"""
Background Document Processor.

Processes documents through the complete AI pipeline using the unified services layer:
PDF → Preprocessing → OCR → Layout → Article Extraction → Language → 
Translation → Entity → Brand → LFM (Sentiment/Crisis) → Risk → Alert → Evidence

Updates processing job status at each stage for real-time progress tracking.
"""

import logging
import time
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
import json

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session
from config import get_settings
from models.document import Document, Page, Article, ProcessingJob, DocumentStatus
from models.intelligence import Translation, Entity, Mention, Alert, AlertPriority, SentimentLabel
from models.review import Review, AuditLog
from models.brand import Brand

# New unified services
from services.pdf_service import PDFService
from services.ocr_service import OCRService
from services.image_preprocessing import ImagePreprocessingService
from services.language_service import LanguageService
from services.translation_service import TranslationService
from services.entity_protection import EntityProtectionService
from services.lfm_service import LFMService
from services.confidence_service import ConfidenceService
from services.review_service import ReviewService

logger = logging.getLogger(__name__)
settings = get_settings()

_processing_semaphore = asyncio.Semaphore(1)

# Service singletons for the worker
_pdf_service = PDFService()
_ocr_service = OCRService()
_preprocessing_service = ImagePreprocessingService()
_language_service = LanguageService()
_translation_service = TranslationService()
_entity_protection_service = EntityProtectionService()
_lfm_service = LFMService()
_confidence_service = ConfidenceService()
_review_service = ReviewService()


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

            # ===== STAGE 1 & 2: PDF Classification & Rendering =====
            await _update_stage(db, job, "pdf_classification", "running", 5)
            
            page_dir = Path(settings.page_image_path) / str(doc.id)
            pdf_result = await asyncio.to_thread(
                _pdf_service.process_pdf,
                doc.file_path,
                str(page_dir),
                300
            )
            
            doc.document_type = pdf_result.document_type
            doc.page_count = pdf_result.page_count
            
            await _log_audit(db, doc.id, None, None, "pdf_classified", "pdf_classification",
                             details={"type": pdf_result.document_type, "pages": pdf_result.page_count})
            await _update_stage(db, job, "pdf_classification", "completed", 10)
            await _update_stage(db, job, "page_rendering", "running", 12)

            # Save pages
            db_pages = []
            for rp in pdf_result.pages:
                page = Page(
                    document_id=doc.id,
                    page_number=rp.page_number,
                    image_path=rp.image_path,
                    thumbnail_path=rp.image_path, # Simplify for now
                    width=rp.width,
                    height=rp.height,
                    dpi=300,
                    has_text_layer=rp.has_text_layer,
                )
                db.add(page)
                db_pages.append((page, rp))

            await db.flush()
            await _update_stage(db, job, "page_rendering", "completed", 18)

            # Load brands for matching
            brand_result = await db.execute(
                select(Brand).options(selectinload(Brand.aliases)).where(Brand.active == True)
            )
            brands = brand_result.scalars().all()
            brand_dicts = []
            monitored_brand_names = []
            for b in brands:
                monitored_brand_names.append(b.name)
                brand_dicts.append({
                    "id": str(b.id),
                    "name": b.name,
                    "aliases": [{"alias": a.alias} for a in (b.aliases or [])],
                    "keywords": b.keywords or [],
                    "fuzzy_threshold": b.fuzzy_threshold,
                    "active": b.active,
                })

            # Process each page
            total_pages = len(db_pages)
            for page_idx, (page, render_info) in enumerate(db_pages):
                progress_base = 20 + (page_idx / max(total_pages, 1)) * 60

                # ===== STAGE 3: OCR / Preprocessing =====
                await _update_stage(db, job, "ocr", "running", progress_base)
                
                # Check if we have native text layer first
                if render_info.has_text_layer and render_info.extracted_text and len(render_info.extracted_text.strip()) > 20:
                    page.ocr_raw_text = render_info.extracted_text
                    page.ocr_confidence = 100.0
                    page.ocr_word_count = len(render_info.extracted_text.split())
                    page.ocr_engine_used = "native_pdf"
                    page.ocr_language = "en"  # Will be detected properly later
                    
                    # Create dummy box for native text
                    page.ocr_bounding_boxes = [{
                        "points": [[0,0], [page.width, 0], [page.width, page.height], [0, page.height]],
                        "text": render_info.extracted_text,
                        "confidence": 100.0
                    }]
                else:
                    # Adaptive preprocessing
                    prep_image_path = await asyncio.to_thread(_preprocessing_service.preprocess, page.image_path)
                    
                    # Run OCR (auto-detect language or default to en for layout)
                    ocr_result = await asyncio.to_thread(_ocr_service.process_page, prep_image_path, None)
                    
                    if ocr_result.status == "success":
                        page.ocr_raw_text = ocr_result.text
                        page.ocr_confidence = ocr_result.confidence or 0.0
                        page.ocr_word_count = len(ocr_result.text.split()) if ocr_result.text else 0
                        page.ocr_engine_used = ocr_result.engine
                        page.ocr_language = ocr_result.language_hint
                        page.ocr_bounding_boxes = ocr_result.bounding_boxes
                    else:
                        page.ocr_raw_text = ""
                        page.ocr_confidence = 0.0
                        page.ocr_word_count = 0
                        page.ocr_engine_used = "failed"
                        page.ocr_language = "unknown"
                        page.ocr_bounding_boxes = []

                await _log_audit(db, doc.id, None, None, "ocr_completed", "ocr",
                    details={"engine": page.ocr_engine_used, "confidence": page.ocr_confidence,
                             "words": page.ocr_word_count})

                # ===== STAGE 4: Layout Analysis =====
                await _update_stage(db, job, "layout_analysis", "running", progress_base + 5)
                await asyncio.sleep(0.01)
                from pipeline.layout.analyzer import analyze_layout
                from pipeline.layout.analyzer import ExtractedArticle

                ocr_box_dicts = page.ocr_bounding_boxes or []
                extracted_articles = await asyncio.to_thread(analyze_layout, ocr_box_dicts, page.width or 2480, page.height or 3508)
                
                # Fallback if layout analysis fails
                if not extracted_articles and page.ocr_raw_text:
                    clean_txt = page.ocr_raw_text.strip()
                    txt_words = clean_txt.split()
                    if len(txt_words) >= 5:
                        headline_str = " ".join(txt_words[:12]) if len(txt_words) >= 12 else clean_txt
                        extracted_articles = [
                            ExtractedArticle(
                                headline=headline_str,
                                body_text=clean_txt,
                                full_text=clean_txt,
                                word_count=len(txt_words),
                                strategy="fallback_raw_text",
                                confidence=60.0,
                            )
                        ]
                
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
                    lang_result = await asyncio.to_thread(_language_service.detect_multi, ext_article.full_text)
                    article.detected_language = lang_result.primary.language
                    article.language_confidence = lang_result.primary.confidence
                    article.detected_script = lang_result.primary.script

                    db.add(article)
                    await db.flush()

                    # ===== STAGE 7: Translation & Entity Protection =====
                    translated_text = ext_article.full_text
                    translation_confidence = None
                    translation_source = "not_available"

                    if article.detected_language != "en" and article.language_confidence > 50:
                        trans_result = await asyncio.to_thread(
                            _translation_service.translate,
                            ext_article.full_text,
                            article.detected_language,
                            "en",
                            monitored_brand_names
                        )
                        translated_text = trans_result.translated_text
                        translation_confidence = trans_result.confidence
                        translation_source = trans_result.confidence_source

                        translation_record = Translation(
                            article_id=article.id,
                            source_language=article.detected_language,
                            source_text=ext_article.full_text,
                            translated_text=translated_text,
                            confidence=trans_result.confidence,
                            model_used=trans_result.model_used,
                            entities_protected=trans_result.entities_protected,
                            needs_review=trans_result.review_required,
                        )
                        db.add(translation_record)

                    # ===== STAGE 8: Entity Detection (Hybrid) =====
                    # Use standard entity extractor for baseline
                    from pipeline.nlp.entity.extractor import EntityExtractor
                    entity_extractor = EntityExtractor()
                    detected_entities = await asyncio.to_thread(entity_extractor.extract, translated_text, "en")
                    entity_texts = [e.text for e in detected_entities]

                    # ===== STAGE 9: Brand Matching =====
                    from pipeline.nlp.entity.brand_matcher import BrandMatcher
                    brand_matcher = BrandMatcher()
                    brand_matcher.load_brands(brand_dicts)
                    brand_matches = brand_matcher.match(translated_text, entity_texts)

                    # ===== STAGE 10: LFM Analysis (Sentiment/Crisis/Summary) =====
                    if brand_matches:
                        # Only run LFM if we found brands
                        primary_brand = brand_matches[0].brand_name
                        lfm_result = await asyncio.to_thread(
                            _lfm_service.analyze,
                            translated_text,
                            entity_texts,
                            primary_brand
                        )
                        
                        lfm_status = lfm_result.status
                        lfm_sentiment = lfm_result.sentiment.get("sentiment", "neutral")
                        lfm_sent_conf = lfm_result.sentiment.get("confidence", 0.5) * 100
                        lfm_crisis = lfm_result.crisis.get("crisis", False)
                        lfm_crisis_topic = lfm_result.crisis.get("category", "general")
                        lfm_crisis_severity = lfm_result.crisis.get("severity", 0.0)
                        lfm_summary = lfm_result.summary

                        # Add LFM verified entities
                        if lfm_result.status == "success" and lfm_result.entities.get("entities"):
                            for ent in lfm_result.entities["entities"]:
                                if ent.get("verified") and ent.get("text") not in entity_texts:
                                    detected_entities.append(
                                        type('obj', (object,), {'text': ent["text"], 'entity_type': ent.get("type", "UNKNOWN"), 'confidence': 0.9, 'start': 0, 'end': 0, 'source': 'lfm', 'normalized': None})()
                                    )
                    else:
                        lfm_status = "skipped"
                        lfm_sentiment = "neutral"
                        lfm_sent_conf = 0.0
                        lfm_crisis = False
                        lfm_crisis_topic = None
                        lfm_crisis_severity = 0.0
                        lfm_summary = ""

                    for ent in detected_entities:
                        entity_record = Entity(
                            article_id=article.id,
                            text=ent.text,
                            entity_type=ent.entity_type,
                            confidence=ent.confidence,
                            start_offset=ent.start,
                            end_offset=ent.end,
                            detected_in="translated" if article.detected_language != "en" else "original",
                            model_used=ent.source,
                            normalized_text=ent.normalized,
                        )
                        db.add(entity_record)

                    # Calculate Risk & Create Mentions/Alerts
                    for brand_match in brand_matches:
                        from pipeline.nlp.crisis.risk_scorer import calculate_risk_score
                        
                        # Use aggregated confidence
                        agg_conf = _confidence_service.aggregate(
                            ocr_confidence=page.ocr_confidence,
                            ocr_source="model" if page.ocr_engine_used != "native_pdf" else "native",
                            language_confidence=article.language_confidence,
                            language_source="model",
                            translation_confidence=translation_confidence,
                            translation_source=translation_source
                        )

                        avg_ai_conf = (
                            ((agg_conf.ocr_confidence or 100) + 
                             (agg_conf.translation_confidence or 100)) / 2
                        ) / 100.0

                        risk = calculate_risk_score(
                            sentiment_label=lfm_sentiment,
                            sentiment_confidence=lfm_sent_conf,
                            brand_match_confidence=brand_match.confidence,
                            crisis_severity=lfm_crisis_severity if lfm_crisis else 0.0,
                            crisis_confidence=85.0 if lfm_crisis else 0.0,
                            publication_reach=0.7, 
                            overall_ai_confidence=avg_ai_conf * 100,
                        )

                        mention = Mention(
                            article_id=article.id,
                            brand_id=uuid.UUID(brand_match.brand_id),
                            matched_text=brand_match.matched_text,
                            match_type=brand_match.match_type,
                            match_confidence=brand_match.confidence,
                            context_snippet=brand_match.context_snippet,
                            sentiment=SentimentLabel(lfm_sentiment),
                            sentiment_confidence=lfm_sent_conf,
                            sentiment_model_used="lfm2.5-2.6b",
                            crisis_topic=lfm_crisis_topic if lfm_crisis else None,
                            crisis_confidence=85.0 if lfm_crisis else None,
                            risk_score=risk.total,
                            risk_breakdown=risk.to_dict(),
                            risk_priority=AlertPriority(risk.priority),
                        )
                        db.add(mention)

                        # Generate alert
                        if risk.total >= 30:
                            from pipeline.alerting.generator import generate_alert
                            alert_data = generate_alert(
                                article_id=str(article.id),
                                brand_id=brand_match.brand_id,
                                brand_name=brand_match.brand_name,
                                headline=ext_article.headline,
                                crisis_topic=lfm_crisis_topic if lfm_crisis else "general",
                                risk_score=risk.total,
                                risk_breakdown=risk.to_dict(),
                                sentiment=lfm_sentiment,
                                sentiment_confidence=lfm_sent_conf,
                                publication_name="",
                                page_number=page.page_number,
                                language=article.detected_language,
                                crisis_keywords=[],
                            )
                            # Use LFM summary if available, else standard
                            if lfm_summary:
                                alert_data.summary = lfm_summary

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

                    # Human Review checking
                    review_item = _review_service.should_review(
                        ocr_confidence=page.ocr_confidence,
                        translation_confidence=translation_confidence,
                        segmentation_confidence=article.segmentation_confidence,
                        lfm_status=lfm_status,
                    )

                    if review_item:
                        article.needs_review = True
                        article.review_reason = review_item.reason
                        
                        review = Review(
                            article_id=article.id,
                            review_type=review_item.review_type,
                            reason=review_item.reason,
                            confidence=review_item.confidence,
                            ai_output=review_item.ai_output,
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
