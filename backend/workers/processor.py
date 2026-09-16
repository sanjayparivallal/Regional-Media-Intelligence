"""
Background Document Processor.

Processes documents through the complete AI pipeline:
PDF → OCR → Layout → Article Extraction → Language → Translation →
Entity → Brand → Sentiment → Crisis → Risk → Alert → Evidence

Updates processing job status at each stage for real-time progress tracking.
"""

import logging
import time
import uuid
import asyncio
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session
from config import get_settings
from models.document import Document, Page, Article, ProcessingJob, DocumentStatus, DocumentType
from models.intelligence import Translation, Entity, Mention, Alert, AlertPriority, SentimentLabel
from models.review import Review, AuditLog
from models.brand import Brand
from pipeline.orchestrator import ModelOrchestrator

logger = logging.getLogger(__name__)
settings = get_settings()

# Global orchestrator
_orchestrator = None
_processing_semaphore = asyncio.Semaphore(1)

try:
    import torch
    torch.set_num_threads(2)
except Exception:
    pass


def get_orchestrator() -> ModelOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ModelOrchestrator()
    return _orchestrator


async def process_document_task(document_id: str, job_id: str):
    """Main background task to process a document through the AI pipeline."""
    async with _processing_semaphore:
        logger.info(f"Starting processing for document {document_id}")
        start_time = time.time()

    async with async_session() as db:
        try:
            # Load document and job
            doc = (await db.execute(select(Document).where(Document.id == uuid.UUID(document_id)))).scalar_one_or_none()
            job = (await db.execute(select(ProcessingJob).where(ProcessingJob.id == uuid.UUID(job_id)))).scalar_one_or_none()

            if not doc or not job:
                logger.error(f"Document or job not found: {document_id}")
                return

            doc.status = DocumentStatus.PROCESSING
            doc.processing_started_at = datetime.utcnow()
            job.status = "running"
            job.started_at = datetime.utcnow()
            await db.commit()

            orchestrator = get_orchestrator()

            # ===== STAGE 1: PDF Classification =====
            await _update_stage(db, job, "pdf_classification", "running", 5)
            from pipeline.ingestion.pdf_classifier import classify_pdf
            classification = classify_pdf(doc.file_path)
            doc.document_type = classification.document_type
            doc.page_count = classification.page_count
            await _log_audit(db, doc.id, None, None, "pdf_classified", "pdf_classification",
                             details={"type": classification.document_type, "pages": classification.page_count})
            await _update_stage(db, job, "pdf_classification", "completed", 10)

            # ===== STAGE 2: Page Rendering =====
            await _update_stage(db, job, "page_rendering", "running", 12)
            from pipeline.ingestion.page_renderer import render_pdf_pages
            page_dir = Path(settings.page_image_path) / str(doc.id)
            rendered_pages = render_pdf_pages(doc.file_path, str(page_dir))

            for rp in rendered_pages:
                page = Page(
                    document_id=doc.id,
                    page_number=rp.page_number,
                    image_path=rp.image_path,
                    thumbnail_path=rp.thumbnail_path,
                    width=rp.width,
                    height=rp.height,
                    dpi=rp.dpi,
                    has_text_layer=classification.pages[rp.page_number - 1].has_text if rp.page_number <= len(classification.pages) else False,
                )
                db.add(page)

            await db.flush()
            await _update_stage(db, job, "page_rendering", "completed", 18)

            # Load all pages
            pages = (await db.execute(
                select(Page).where(Page.document_id == doc.id).order_by(Page.page_number)
            )).scalars().all()

            # Load brands for matching (eager load aliases to prevent MissingGreenlet lazy-loading error)
            brand_result = await db.execute(
                select(Brand).options(selectinload(Brand.aliases)).where(Brand.active == True)
            )
            brands = brand_result.scalars().all()
            brand_dicts = []
            for b in brands:
                brand_dicts.append({
                    "id": str(b.id),
                    "name": b.name,
                    "aliases": [{"alias": a.alias} for a in (b.aliases or [])],
                    "keywords": b.keywords or [],
                    "fuzzy_threshold": b.fuzzy_threshold,
                    "active": b.active,
                })

            # Process each page
            total_pages = len(pages)
            for page_idx, page in enumerate(pages):
                progress_base = 20 + (page_idx / max(total_pages, 1)) * 60

                # ===== STAGE 3: OCR =====
                await _update_stage(db, job, "ocr", "running", progress_base)
                import cv2
                image = cv2.imread(page.image_path)

                if image is None:
                    logger.warning(f"Could not read page image: {page.image_path}")
                    continue

                # Detect language from any existing text
                from pipeline.ocr.language_router import route_ocr_language
                ocr_languages = route_ocr_language()

                # Try OCR with preprocessing variants in background thread
                from pipeline.ingestion.preprocessor import generate_preprocessing_variants, select_best_variant
                variants = await asyncio.to_thread(generate_preprocessing_variants, image)

                ocr_provider = orchestrator.get_ocr_provider()
                best_result = None

                if ocr_provider:
                    ocr_results = []
                    found_good_ocr = False
                    for variant in variants[:2]:  # Try top 2 variants
                        if found_good_ocr:
                            break
                        for lang in ocr_languages[:2]:  # Try top 2 languages
                            try:
                                result = await asyncio.to_thread(ocr_provider.ocr, variant.image, lang)
                                if result.confidence > 0:
                                    ocr_results.append({
                                        "name": f"{variant.name}_{lang}",
                                        "ocr_confidence": result.confidence,
                                        "word_count": result.word_count,
                                        "text": result.text,
                                        "result": result,
                                        "preprocessing": variant.name,
                                    })
                                    # If confidence and word count are solid, skip trying more variants on CPU
                                    if result.confidence >= 65 and result.word_count >= 10:
                                        found_good_ocr = True
                                        break
                            except Exception as e:
                                logger.warning(f"OCR variant failed: {e}")
                            await asyncio.sleep(0.05)
                        await asyncio.sleep(0.05)

                    if ocr_results:
                        best = select_best_variant(ocr_results)
                        if best:
                            best_result = best.get("result")
                            page.preprocessing_applied = best.get("preprocessing", "")

                # Use demo fallback if OCR failed
                if not best_result or not best_result.text:
                    from pipeline.ocr.base import OCRResult
                    if settings.demo_mode:
                        best_result = _get_demo_ocr_result(page.page_number)
                    else:
                        best_result = OCRResult(text="", confidence=0.0, engine="none")

                # Update page with OCR results
                page.ocr_raw_text = best_result.text
                page.ocr_confidence = best_result.confidence
                page.ocr_word_count = best_result.word_count
                page.ocr_engine_used = best_result.engine
                page.ocr_language = best_result.language
                page.ocr_bounding_boxes = [b.to_dict() for b in best_result.boxes] if best_result.boxes else []

                await _log_audit(db, doc.id, None, None, "ocr_completed", "ocr",
                    details={"engine": best_result.engine, "confidence": best_result.confidence,
                             "words": best_result.word_count, "language": best_result.language})

                # ===== STAGE 4: Layout Analysis =====
                await _update_stage(db, job, "layout_analysis", "running", progress_base + 5)
                await asyncio.sleep(0.01)
                from pipeline.layout.analyzer import analyze_layout

                ocr_box_dicts = page.ocr_bounding_boxes or []
                extracted_articles = await asyncio.to_thread(analyze_layout, ocr_box_dicts, page.width or 2480, page.height or 3508)
                page.detected_columns = len(set(a.bbox_x // ((page.width or 2480) / 3) for a in extracted_articles)) if extracted_articles else 1

                # ===== STAGE 5: Article Extraction =====
                await _update_stage(db, job, "article_extraction", "running", progress_base + 10)
                await asyncio.sleep(0.01)

                for ext_article in extracted_articles:
                    if ext_article.word_count < 5:
                        continue

                    article = Article(
                        page_id=page.id,
                        document_id=doc.id,
                        headline=ext_article.headline,
                        body_text=ext_article.body_text,
                        full_text=ext_article.full_text,
                        word_count=ext_article.word_count,
                        bbox_x=ext_article.bbox_x,
                        bbox_y=ext_article.bbox_y,
                        bbox_width=ext_article.bbox_width,
                        bbox_height=ext_article.bbox_height,
                        bounding_boxes=ext_article.bounding_boxes,
                        article_type=ext_article.article_type,
                        is_advertisement=ext_article.is_advertisement,
                        segmentation_confidence=ext_article.confidence,
                        segmentation_strategy=ext_article.strategy,
                    )

                    # ===== STAGE 6: Language Detection =====
                    from pipeline.nlp.language_detector import detect_language
                    lang_result = detect_language(ext_article.full_text)
                    article.detected_language = lang_result.language
                    article.language_confidence = lang_result.confidence
                    article.detected_script = lang_result.script

                    # ===== STAGE 7: Translation =====
                    translated_text = ext_article.full_text
                    translation_confidence = 100.0

                    if lang_result.language != "en" and lang_result.confidence > 50:
                        translator = orchestrator.get_translation_provider()
                        # Pre-extract entities for protection
                        from pipeline.nlp.translation.entity_protector import extract_potential_entities
                        pre_entities = extract_potential_entities(ext_article.full_text)

                        trans_result = await asyncio.to_thread(
                            translator.translate,
                            ext_article.full_text,
                            lang_result.language,
                            "en",
                            pre_entities,
                        )
                        translated_text = trans_result.translated_text
                        translation_confidence = trans_result.confidence

                        db.add(article)
                        await db.flush()

                        translation_record = Translation(
                            article_id=article.id,
                            source_language=lang_result.language,
                            source_text=ext_article.full_text,
                            translated_text=translated_text,
                            confidence=trans_result.confidence,
                            model_used=trans_result.model_used,
                            entities_protected=trans_result.entities_protected,
                            needs_review=trans_result.confidence < 90,
                        )
                        db.add(translation_record)
                    else:
                        db.add(article)
                        await db.flush()

                    # ===== STAGE 8: Entity Detection =====
                    entity_extractor = orchestrator.get_entity_extractor()
                    detected_entities = await asyncio.to_thread(entity_extractor.extract, translated_text, "en")

                    for ent in detected_entities:
                        entity_record = Entity(
                            article_id=article.id,
                            text=ent.text,
                            entity_type=ent.entity_type,
                            confidence=ent.confidence,
                            start_offset=ent.start,
                            end_offset=ent.end,
                            detected_in="translated" if lang_result.language != "en" else "original",
                            model_used=ent.source,
                            normalized_text=ent.normalized,
                        )
                        db.add(entity_record)

                    # ===== STAGE 9: Brand Matching =====
                    brand_matcher = orchestrator.get_brand_matcher()
                    brand_matcher.load_brands(brand_dicts)
                    entity_texts = [e.text for e in detected_entities]
                    brand_matches = brand_matcher.match(translated_text, entity_texts)

                    # ===== STAGE 10: Sentiment + Crisis + Risk for each brand match =====
                    sentiment_analyzer = orchestrator.get_sentiment_analyzer()
                    crisis_classifier = orchestrator.get_crisis_classifier()

                    sentiment_result = await asyncio.to_thread(
                        sentiment_analyzer.analyze,
                        ext_article.full_text, translated_text, lang_result.language
                    )

                    for brand_match in brand_matches:
                        # Crisis classification
                        crisis_result = await asyncio.to_thread(
                            crisis_classifier.classify,
                            translated_text,
                            entities=entity_texts,
                            sentiment_label=sentiment_result.label,
                            sentiment_confidence=sentiment_result.confidence,
                        )

                        # Risk scoring
                        from pipeline.nlp.crisis.risk_scorer import calculate_risk_score
                        risk = calculate_risk_score(
                            sentiment_label=sentiment_result.label,
                            sentiment_confidence=sentiment_result.confidence,
                            brand_match_confidence=brand_match.confidence,
                            crisis_severity=crisis_result.severity if crisis_result else 0.0,
                            crisis_confidence=crisis_result.confidence if crisis_result else 0.0,
                            publication_reach=0.7,  # TODO: get from publication
                            overall_ai_confidence=min(page.ocr_confidence, translation_confidence) / 100,
                        )

                        # Create mention
                        mention = Mention(
                            article_id=article.id,
                            brand_id=uuid.UUID(brand_match.brand_id),
                            matched_text=brand_match.matched_text,
                            match_type=brand_match.match_type,
                            match_confidence=brand_match.confidence,
                            context_snippet=brand_match.context_snippet,
                            sentiment=SentimentLabel(sentiment_result.label),
                            sentiment_confidence=sentiment_result.confidence,
                            sentiment_model_used=sentiment_result.model_used,
                            crisis_topic=crisis_result.topic if crisis_result else None,
                            crisis_confidence=crisis_result.confidence if crisis_result else None,
                            risk_score=risk.total,
                            risk_breakdown=risk.to_dict(),
                            risk_priority=AlertPriority(risk.priority),
                        )
                        db.add(mention)

                        # Generate alert if risk warrants it
                        if risk.total >= 30:
                            from pipeline.alerting.generator import generate_alert
                            alert_data = generate_alert(
                                article_id=str(article.id),
                                brand_id=brand_match.brand_id,
                                brand_name=brand_match.brand_name,
                                headline=ext_article.headline,
                                crisis_topic=crisis_result.topic if crisis_result else "general",
                                risk_score=risk.total,
                                risk_breakdown=risk.to_dict(),
                                sentiment=sentiment_result.label,
                                sentiment_confidence=sentiment_result.confidence,
                                publication_name="",
                                page_number=page.page_number,
                                language=lang_result.language,
                                crisis_keywords=crisis_result.keywords_matched if crisis_result else [],
                            )

                            alert = Alert(
                                article_id=article.id,
                                brand_id=uuid.UUID(brand_match.brand_id),
                                title=alert_data.title,
                                summary=alert_data.summary,
                                priority=AlertPriority(alert_data.priority),
                                risk_score=alert_data.risk_score,
                                risk_breakdown=alert_data.risk_breakdown,
                                publication_name=alert_data.publication_name,
                                page_number=alert_data.page_number,
                                language=alert_data.language,
                                sentiment=SentimentLabel(alert_data.sentiment),
                                sentiment_confidence=alert_data.sentiment_confidence,
                                crisis_topic=alert_data.crisis_topic,
                                crisis_keywords=alert_data.crisis_keywords,
                                fingerprint=alert_data.fingerprint,
                                is_demo=doc.is_demo,
                            )
                            db.add(alert)

                            await _log_audit(db, doc.id, article.id, None, "alert_generated", "alert_generation",
                                details={"brand": brand_match.brand_name, "risk_score": risk.total, "priority": risk.priority})

                    # Check if article needs review
                    if (page.ocr_confidence < settings.ocr_confidence_threshold or
                        article.segmentation_confidence < 50 or
                        (translation_confidence < 90 and lang_result.language != "en")):
                        article.needs_review = True
                        reasons = []
                        if page.ocr_confidence < settings.ocr_confidence_threshold:
                            reasons.append(f"OCR confidence {page.ocr_confidence:.0f}%")
                        if article.segmentation_confidence < 50:
                            reasons.append(f"segmentation confidence {article.segmentation_confidence:.0f}%")
                        article.review_reason = "; ".join(reasons)

                        review = Review(
                            article_id=article.id,
                            review_type="quality",
                            reason=article.review_reason,
                            confidence=page.ocr_confidence,
                            ai_output={
                                "ocr_confidence": page.ocr_confidence,
                                "segmentation_confidence": article.segmentation_confidence,
                                "language": lang_result.language,
                            },
                        )
                        db.add(review)

                await db.flush()

            # ===== Complete =====
            await _update_stage(db, job, "evidence_indexed", "completed", 100)
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.duration_ms = int((time.time() - start_time) * 1000)
            doc.status = DocumentStatus.COMPLETED
            doc.processing_completed_at = datetime.utcnow()
            doc.processing_duration_ms = job.duration_ms

            await db.commit()
            logger.info(f"Document {document_id} processing completed in {job.duration_ms}ms")

        except Exception as e:
            logger.error(f"Processing failed for {document_id}: {e}", exc_info=True)
            try:
                job.status = "failed"
                job.error_message = str(e)
                doc.status = DocumentStatus.FAILED
                doc.error_message = str(e)
                await db.commit()
            except Exception:
                pass


async def _update_stage(db: AsyncSession, job: ProcessingJob, stage: str, status: str, progress: float):
    """Update processing job stage status."""
    stages = dict(job.stages) if job.stages else {}
    stages[stage] = status
    job.stages = stages
    job.current_stage = stage
    job.progress_percent = progress
    await db.commit()


async def _log_audit(db, doc_id, article_id, alert_id, action, stage, **kwargs):
    """Log an audit entry."""
    audit = AuditLog(
        document_id=doc_id,
        article_id=article_id,
        alert_id=alert_id,
        action=action,
        stage=stage,
        **kwargs,
    )
    db.add(audit)


def _get_demo_ocr_result(page_number: int):
    """Generate demo OCR result for testing without real OCR."""
    from pipeline.ocr.base import OCRResult, OCRBox

    demo_texts = {
        1: {
            "text": "PayU पर RBI की कार्रवाई: डिजिटल भुगतान कंपनी पर लगा प्रतिबंध\n\nभारतीय रिजर्व बैंक ने PayU फाइनेंस पर नए ग्राहकों को जोड़ने पर रोक लगा दी है। RBI ने कहा कि कंपनी ने KYC नियमों का उल्लंघन किया है। PayU ने कहा कि वह RBI के निर्देशों का पालन करेगी और जल्द से जल्द सभी मुद्दों का समाधान करेगी।",
            "boxes": [
                {"x": 50, "y": 80, "width": 900, "height": 60, "text": "PayU पर RBI की कार्रवाई: डिजिटल भुगतान कंपनी पर लगा प्रतिबंध", "confidence": 92, "font_size_estimate": 60},
                {"x": 50, "y": 200, "width": 900, "height": 30, "text": "भारतीय रिजर्व बैंक ने PayU फाइनेंस पर नए ग्राहकों को जोड़ने पर रोक लगा दी है।", "confidence": 89, "font_size_estimate": 30},
                {"x": 50, "y": 250, "width": 900, "height": 30, "text": "RBI ने कहा कि कंपनी ने KYC नियमों का उल्लंघन किया है।", "confidence": 91, "font_size_estimate": 30},
                {"x": 50, "y": 300, "width": 900, "height": 30, "text": "PayU ने कहा कि वह RBI के निर्देशों का पालन करेगी और जल्द से जल्द सभी मुद्दों का समाधान करेगी।", "confidence": 88, "font_size_estimate": 30},
            ],
            "language": "hi",
        },
    }

    demo = demo_texts.get(page_number, demo_texts[1])
    boxes = [OCRBox(**b) for b in demo["boxes"]]

    return OCRResult(
        text=demo["text"],
        boxes=boxes,
        confidence=90.0,
        word_count=len(demo["text"].split()),
        engine="demo",
        language=demo["language"],
    )
