"""
Background Document Processor — 3-Phase Batch Pipeline.

Newspaper PDF is processed in three explicit, sequential phases:

  PHASE 1  — OCR ALL PAGES (IndicOCR)
             Render PDF → preprocess images → OCR every page → store raw text.

  PHASE 2  — TRANSLATE ALL EXTRACTED TEXT (IndicTrans2)
             Language detection → translate every article → store translations.

  PHASE 3  — SENTIMENT ANALYSIS (LFM2.5)
             Entity extraction → brand matching → LFM/fallback sentiment →
             risk scoring → alert generation.

This separation ensures:
- One failed page does NOT abort the whole run.
- The frontend can display a clear 3-stage progress bar.
- OCR is always complete before translation starts.
- Translation is always complete before sentiment starts.
"""

import logging
import time
import uuid
import asyncio
from collections import Counter
from datetime import datetime
from pathlib import Path
import json

from config import get_settings
from storage.excel_storage_service import ExcelStorageService

from services.pdf_service import PDFService
from services.ocr_service import OCRService
from services.image_preprocessing import ImagePreprocessingService
from services.language_service import LanguageService
from services.translation_service import TranslationService
from services.entity_protection import EntityProtectionService
from services.lfm_service import LFMService
from services.confidence_service import ConfidenceService
from services.review_service import ReviewService
from pipeline.nlp.sentiment.analyzer import SentimentAnalyzer

logger = logging.getLogger(__name__)
settings = get_settings()

_processing_semaphore = asyncio.Semaphore(1)

# Service singletons
_pdf_service = PDFService()
_ocr_service = OCRService()
_preprocessing_service = ImagePreprocessingService()
_language_service = LanguageService()
_translation_service = TranslationService()
_entity_protection_service = EntityProtectionService()
_lfm_service = LFMService()
_sentiment_analyzer = SentimentAnalyzer()
_confidence_service = ConfidenceService()
_review_service = ReviewService()


async def process_document_task(document_id: str, job_id: str):
    """Main background task — runs 3-phase batch pipeline on a document."""
    async with _processing_semaphore:
        logger.info(f"Starting 3-phase processing for document {document_id}")
        start_time = time.time()
        excel = ExcelStorageService()

        try:
            doc = excel.find_row("Documents", {"document_id": document_id})
            if not doc:
                logger.error(f"Document not found: {document_id}")
                return

            # Mark as started
            excel.update_row("Documents", {"document_id": document_id}, {
                "processing_status": "PROCESSING",
                "current_stage": "Phase 1: OCR Scan",
                "progress_percent": 0.0,
                "processing_started_at": datetime.utcnow().isoformat()
            })

            # Clear previous run data (idempotent)
            for sheet in ("Pages", "Articles", "Translations", "Alerts", "AuditLogs"):
                excel.delete_rows(sheet, {"document_id": document_id})

            # =====================================================================
            # PRE-PHASE — PDF Rendering
            # =====================================================================
            page_dir = Path(settings.page_image_path) / document_id
            upload_dir = Path(settings.upload_path)
            matching_files = list(upload_dir.glob(f"{document_id}.*"))
            if matching_files:
                file_path = str(matching_files[0])
            else:
                ext = Path(doc.get("file_name", "")).suffix or ".pdf"
                file_path = str(upload_dir / f"{document_id}{ext}")

            pdf_result = await asyncio.to_thread(
                _pdf_service.process_pdf,
                file_path,
                str(page_dir),
                300
            )

            if pdf_result.status == "error" or not pdf_result.pages:
                raise RuntimeError(pdf_result.error or f"Failed to render pages from: {file_path}")

            total_pages = pdf_result.page_count
            excel.update_row("Documents", {"document_id": document_id}, {
                "source_type": pdf_result.document_type,
                "total_pages": total_pages
            })
            await _log_audit(excel, document_id, None, "pdf_classified", "pdf_classification",
                             details={"type": pdf_result.document_type, "pages": total_pages})

            # =====================================================================
            # PHASE 1 — OCR ALL PAGES (IndicOCR)
            # Progress band: 0% → 30%
            # =====================================================================
            logger.info(f"[Phase 1] OCR scanning {total_pages} pages with IndicOCR")
            excel.update_row("Documents", {"document_id": document_id}, {
                "current_stage": "Phase 1: OCR Scan (IndicOCR)",
                "progress_percent": 2.0
            })

            pages_to_process = []  # list of (page_dict, render_page, ocr_bounding_boxes)

            for page_idx, rp in enumerate(pdf_result.pages):
                page_id = str(uuid.uuid4())
                page_dict = {
                    "page_id": page_id,
                    "document_id": document_id,
                    "page_number": rp.page_number,
                    "image_path": rp.image_path,
                    "is_scanned": not rp.has_text_layer,
                    "has_extractable_text": rp.has_text_layer,
                    "page_width": rp.width,
                    "page_height": rp.height,
                    "created_at": datetime.utcnow().isoformat()
                }

                # Update progress within Phase 1
                p1_progress = 2.0 + (page_idx / total_pages) * 28.0
                excel.update_row("Documents", {"document_id": document_id}, {
                    "current_stage": f"Phase 1: OCR Scan — page {rp.page_number}/{total_pages} (IndicOCR)",
                    "progress_percent": round(p1_progress, 1)
                })

                # Native text layer (digital PDF page)
                if rp.has_text_layer and rp.extracted_text and len(rp.extracted_text.strip()) > 20:
                    page_dict["ocr_text"] = rp.extracted_text
                    page_dict["ocr_confidence"] = 100.0
                    page_dict["ocr_status"] = "success"
                    page_dict["language"] = "en"
                    ocr_boxes = [{
                        "points": [[0, 0], [rp.width, 0], [rp.width, rp.height], [0, rp.height]],
                        "text": rp.extracted_text,
                        "confidence": 100.0
                    }]
                else:
                    # Scanned page — run IndicOCR
                    try:
                        prep_path = await asyncio.to_thread(
                            _preprocessing_service.preprocess, rp.image_path
                        )
                    except Exception as e:
                        logger.warning(f"Page {rp.page_number} preprocessing failed, using raw: {e}")
                        prep_path = rp.image_path

                    doc_lang_hint = doc.get("language")
                    ocr_result = await asyncio.to_thread(
                        _ocr_service.process_page, prep_path, doc_lang_hint
                    )

                    if ocr_result.status == "success" and ocr_result.text:
                        page_dict["ocr_text"] = ocr_result.text
                        page_dict["ocr_confidence"] = ocr_result.confidence or 75.0
                        page_dict["ocr_status"] = "success"
                        page_dict["language"] = ocr_result.language_hint or "en"
                        ocr_boxes = ocr_result.bounding_boxes or []
                    else:
                        logger.warning(f"OCR failed/empty on page {rp.page_number} — continuing")
                        page_dict["ocr_text"] = ocr_result.text or ""
                        page_dict["ocr_confidence"] = ocr_result.confidence or 0.0
                        page_dict["ocr_status"] = ocr_result.status or "failed"
                        page_dict["language"] = ocr_result.language_hint or "unknown"
                        ocr_boxes = []

                excel.append_row("Pages", page_dict)
                await _log_audit(excel, document_id, None, "ocr_completed", "ocr",
                                 details={"page": rp.page_number, "confidence": page_dict["ocr_confidence"]})

                pages_to_process.append((page_dict, rp, ocr_boxes))

            logger.info(f"[Phase 1] Complete — {total_pages} pages OCR'd")

            # =====================================================================
            # PHASE 2 — ARTICLE EXTRACTION + TRANSLATION (IndicTrans2)
            # Progress band: 30% → 65%
            # =====================================================================
            logger.info(f"[Phase 2] Extracting articles and translating with IndicTrans2")
            excel.update_row("Documents", {"document_id": document_id}, {
                "current_stage": "Phase 2: Translation (IndicTrans2)",
                "progress_percent": 30.0
            })

            from pipeline.layout.analyzer import analyze_layout, ExtractedArticle

            # article_buffer: list of dicts ready for Phase 3
            article_buffer = []
            total_articles_extracted = 0

            for page_idx, (page, rp, ocr_boxes) in enumerate(pages_to_process):
                p2_progress = 30.0 + (page_idx / total_pages) * 35.0

                # Layout analysis / article segmentation
                extracted_articles = await asyncio.to_thread(
                    analyze_layout, ocr_boxes,
                    page["page_width"] or 2480, page["page_height"] or 3508
                )

                # Fallback — treat whole page text as one article
                if not extracted_articles and page.get("ocr_text"):
                    clean_txt = page["ocr_text"].strip()
                    words = clean_txt.split()
                    if words:
                        headline_str = " ".join(words[:12]) if len(words) >= 12 else clean_txt
                        extracted_articles = [
                            ExtractedArticle(
                                headline=headline_str,
                                body_text=clean_txt,
                                full_text=clean_txt,
                                word_count=len(words),
                                strategy="fallback_raw_text",
                                confidence=65.0,
                                bbox_x=0,
                                bbox_y=0,
                                bbox_width=page["page_width"] or 2480,
                                bbox_height=page["page_height"] or 3508,
                            )
                        ]

                for art_idx, ext_article in enumerate(extracted_articles):
                    if ext_article.word_count < 2:
                        continue

                    total_articles_extracted += 1
                    article_id = str(uuid.uuid4())

                    # Language detection
                    lang_result = await asyncio.to_thread(
                        _language_service.detect_multi, ext_article.full_text
                    )
                    detected_lang = (
                        lang_result.primary.language
                        if lang_result and lang_result.primary else "en"
                    )
                    lang_confidence = (
                        lang_result.primary.confidence
                        if lang_result and lang_result.primary else 0.0
                    )

                    # Save article record
                    article_dict = {
                        "article_id": article_id,
                        "document_id": document_id,
                        "page_id": page["page_id"],
                        "page_number": page["page_number"],
                        "headline": ext_article.headline,
                        "original_text": ext_article.full_text,
                        "language": detected_lang,
                        "article_type": ext_article.article_type,
                        "x1": ext_article.bbox_x,
                        "y1": ext_article.bbox_y,
                        "x2": (ext_article.bbox_x or 0) + (ext_article.bbox_width or 0),
                        "y2": (ext_article.bbox_y or 0) + (ext_article.bbox_height or 0),
                        "ocr_confidence": page["ocr_confidence"],
                        "article_confidence": ext_article.confidence,
                        "created_at": datetime.utcnow().isoformat()
                    }
                    excel.append_row("Articles", article_dict)

                    # Update progress within Phase 2
                    excel.update_row("Documents", {"document_id": document_id}, {
                        "current_stage": f"Phase 2: Translating — page {page['page_number']}/{total_pages} (IndicTrans2)",
                        "progress_percent": round(p2_progress + (art_idx / max(len(extracted_articles), 1)) * (35.0 / total_pages), 1)
                    })

                    # Translation (only for non-English text with sufficient confidence)
                    translated_text = ext_article.full_text
                    translation_confidence = None

                    if detected_lang != "en" and lang_confidence > 40:
                        try:
                            trans_result = await asyncio.to_thread(
                                _translation_service.translate,
                                ext_article.full_text,
                                detected_lang,
                                "en",
                                []  # brand names added in phase 3
                            )
                            if trans_result.status == "success" and trans_result.translated_text:
                                translated_text = trans_result.translated_text
                                translation_confidence = trans_result.confidence
                            else:
                                translation_confidence = 50.0

                            trans_dict = {
                                "translation_id": str(uuid.uuid4()),
                                "article_id": article_id,
                                "source_language": detected_lang,
                                "target_language": "en",
                                "original_text": ext_article.full_text,
                                "translated_text": translated_text,
                                "translation_confidence": translation_confidence,
                                "entity_protected": getattr(trans_result, "entities_protected", []),
                                "review_required": getattr(trans_result, "review_required", False),
                                "translation_model": getattr(trans_result, "model_used", "none"),
                                "created_at": datetime.utcnow().isoformat()
                            }
                            excel.append_row("Translations", trans_dict)
                        except Exception as e:
                            logger.warning(f"Translation failed for article {article_id}: {e}")

                    # Buffer for Phase 3
                    article_buffer.append({
                        "article_id": article_id,
                        "page": page,
                        "ext_article": ext_article,
                        "detected_lang": detected_lang,
                        "translated_text": translated_text,
                        "translation_confidence": translation_confidence,
                    })

            logger.info(f"[Phase 2] Complete — {total_articles_extracted} articles extracted and translated")

            # =====================================================================
            # PHASE 3 — SENTIMENT ANALYSIS (LFM2.5 / fallback)
            # Progress band: 65% → 95%
            # =====================================================================
            logger.info(f"[Phase 3] Running sentiment analysis on {len(article_buffer)} articles")
            excel.update_row("Documents", {"document_id": document_id}, {
                "current_stage": "Phase 3: Sentiment Analysis (LFM2.5)",
                "progress_percent": 65.0
            })

            # Load brands once for Phase 3
            brands = excel.find_rows("MonitoredBrands", {"enabled": True})
            if not brands:
                excel.seed_defaults_if_empty()
                brands = excel.find_rows("MonitoredBrands", {"enabled": True})

            monitored_brand_names = [b["brand_name"] for b in brands]
            brand_dicts = []
            for b in brands:
                aliases_str = b.get("aliases") or ""
                aliases_list = [a.strip() for a in aliases_str.split(",") if a.strip()]
                brand_dicts.append({
                    "id": b["brand_id"],
                    "name": b["brand_name"],
                    "aliases": [{"alias": a} for a in aliases_list],
                    "keywords": [],
                    "fuzzy_threshold": 85.0,
                    "active": True,
                })

            doc_sentiments = []
            doc_risk_scores = []
            total_art = max(len(article_buffer), 1)

            for art_idx, buf in enumerate(article_buffer):
                article_id = buf["article_id"]
                page = buf["page"]
                ext_article = buf["ext_article"]
                detected_lang = buf["detected_lang"]
                translated_text = buf["translated_text"]
                translation_confidence = buf["translation_confidence"]

                p3_progress = 65.0 + (art_idx / total_art) * 30.0
                excel.update_row("Documents", {"document_id": document_id}, {
                    "current_stage": f"Phase 3: Sentiment — article {art_idx + 1}/{total_art} (LFM2.5)",
                    "progress_percent": round(p3_progress, 1)
                })

                # Entity detection
                from pipeline.nlp.entity.extractor import EntityExtractor
                entity_extractor = EntityExtractor()
                detected_entities = await asyncio.to_thread(
                    entity_extractor.extract, translated_text, "en"
                )
                entity_texts = [e.text for e in detected_entities]

                # Brand matching
                from pipeline.nlp.entity.brand_matcher import BrandMatcher
                brand_matcher = BrandMatcher()
                brand_matcher.load_brands(brand_dicts)
                brand_matches = brand_matcher.match(translated_text, entity_texts)

                # LFM sentiment + crisis analysis
                lfm_status = "skipped"
                lfm_sentiment = "NEUTRAL"
                lfm_sent_conf = 50.0
                lfm_crisis = False
                lfm_crisis_topic = "GENERAL"
                lfm_crisis_severity = 0.0
                lfm_summary = ext_article.headline or ""
                primary_brand = brand_matches[0].brand_name if brand_matches else None

                if brand_matches and _lfm_service.is_available():
                    try:
                        lfm_result = await asyncio.to_thread(
                            _lfm_service.analyze,
                            translated_text,
                            entity_texts,
                            primary_brand
                        )
                        if lfm_result and lfm_result.status == "success":
                            lfm_status = "success"
                            lfm_sentiment = str(lfm_result.sentiment.get("sentiment", "NEUTRAL")).upper()
                            lfm_sent_conf = float(lfm_result.sentiment.get("confidence", 0.5) * 100)
                            lfm_crisis = bool(lfm_result.crisis.get("crisis", False))
                            lfm_crisis_topic = str(lfm_result.crisis.get("category", "GENERAL"))
                            lfm_crisis_severity = float(lfm_result.crisis.get("severity", 0.0))
                            lfm_summary = lfm_result.summary or ext_article.headline
                    except Exception as e:
                        logger.warning(f"LFM analysis failed: {e}")

                # Fallback to local SentimentAnalyzer
                if lfm_status != "success":
                    try:
                        sent_res = await asyncio.to_thread(
                            _sentiment_analyzer.analyze,
                            ext_article.full_text,
                            translated_text,
                            detected_lang
                        )
                        lfm_sentiment = str(sent_res.label).upper()
                        lfm_sent_conf = float(sent_res.confidence)
                        lfm_status = "success"
                        lfm_summary = ext_article.headline
                    except Exception as e:
                        logger.warning(f"Sentiment fallback failed: {e}")

                # Save AI Analysis
                excel.append_row("AIAnalysis", {
                    "analysis_id": str(uuid.uuid4()),
                    "article_id": article_id,
                    "brand_name": primary_brand or "General",
                    "summary": lfm_summary or ext_article.headline,
                    "sentiment": lfm_sentiment,
                    "sentiment_confidence": lfm_sent_conf,
                    "crisis_category": lfm_crisis_topic if lfm_crisis else "NONE",
                    "crisis_reason": "Automated AI Analysis",
                    "ai_confidence": lfm_sent_conf,
                    "model_name": "lfm-sentiment-pipeline",
                    "created_at": datetime.utcnow().isoformat()
                })
                doc_sentiments.append(lfm_sentiment)

                # Save entities
                for ent in detected_entities:
                    excel.append_row("Entities", {
                        "entity_id": str(uuid.uuid4()),
                        "article_id": article_id,
                        "entity_text": ent.text,
                        "entity_type": ent.entity_type,
                        "normalized_name": ent.normalized,
                        "start_position": ent.start,
                        "end_position": ent.end,
                        "confidence": ent.confidence,
                        "is_monitored_brand": ent.text in monitored_brand_names,
                        "verification_status": "verified" if lfm_status == "success" else "unverified",
                        "created_at": datetime.utcnow().isoformat()
                    })

                # Risk scoring + alerts per brand mention
                for brand_match in brand_matches:
                    sentiment_severity = 100 if lfm_sentiment == "NEGATIVE" else (50 if lfm_sentiment == "NEUTRAL" else 0)
                    brand_relevance = 80
                    crisis_severity = lfm_crisis_severity if lfm_crisis else 0.0
                    publication_reach = 50
                    avg_ai_conf = ((page.get("ocr_confidence") or 100) + (translation_confidence or 100)) / 2

                    final_crisis_score = (
                        (sentiment_severity * 0.30) +
                        (brand_relevance * 0.25) +
                        (crisis_severity * 0.20) +
                        (publication_reach * 0.15) +
                        (avg_ai_conf * 0.10)
                    )

                    severity_label = "LOW"
                    if final_crisis_score >= 81: severity_label = "CRITICAL"
                    elif final_crisis_score >= 61: severity_label = "HIGH"
                    elif final_crisis_score >= 31: severity_label = "MEDIUM"

                    doc_risk_scores.append(final_crisis_score)

                    excel.append_row("CrisisScores", {
                        "score_id": str(uuid.uuid4()),
                        "article_id": article_id,
                        "brand_name": brand_match.brand_name,
                        "sentiment_score": sentiment_severity,
                        "brand_relevance_score": brand_relevance,
                        "crisis_severity_score": crisis_severity,
                        "publication_reach_score": publication_reach,
                        "ai_confidence_score": avg_ai_conf,
                        "final_crisis_score": final_crisis_score,
                        "severity": severity_label,
                        "created_at": datetime.utcnow().isoformat()
                    })

                    excel.append_row("BrandMentions", {
                        "mention_id": str(uuid.uuid4()),
                        "article_id": article_id,
                        "brand_name": brand_match.brand_name,
                        "matched_text": brand_match.matched_text,
                        "match_type": brand_match.match_type,
                        "match_confidence": brand_match.confidence,
                        "context": brand_match.context_snippet,
                        "verified_by_lfm": lfm_status == "success",
                        "created_at": datetime.utcnow().isoformat()
                    })

                    if final_crisis_score >= 50 or lfm_crisis or (lfm_sentiment == "NEGATIVE" and final_crisis_score >= 25):
                        excel.append_row("Alerts", {
                            "alert_id": str(uuid.uuid4()),
                            "article_id": article_id,
                            "document_id": document_id,
                            "publication": doc.get("publication", "Regional Broadsheet"),
                            "page_number": page["page_number"],
                            "brand_name": brand_match.brand_name,
                            "language": detected_lang,
                            "headline": ext_article.headline,
                            "sentiment": lfm_sentiment,
                            "crisis_category": lfm_crisis_topic if lfm_crisis else "NONE",
                            "crisis_score": final_crisis_score,
                            "severity": severity_label,
                            "summary": lfm_summary or ext_article.headline,
                            "reason": f"AI identified this article with {severity_label} severity.",
                            "evidence_page_path": page["image_path"],
                            "evidence_article_coordinates": f"{ext_article.bbox_x},{ext_article.bbox_y},{ext_article.bbox_width},{ext_article.bbox_height}",
                            "alert_status": "NEW",
                            "created_at": datetime.utcnow().isoformat()
                        })
                        await _log_audit(excel, document_id, article_id, "alert_generated", "alert_generation",
                                         details={"brand": brand_match.brand_name, "risk_score": final_crisis_score})

                # Human review flag
                review_item = _review_service.should_review(
                    ocr_confidence=page.get("ocr_confidence"),
                    translation_confidence=translation_confidence,
                    segmentation_confidence=ext_article.confidence,
                    lfm_status=lfm_status,
                )
                if review_item:
                    excel.append_row("Reviews", {
                        "review_id": str(uuid.uuid4()),
                        "article_id": article_id,
                        "review_type": review_item.review_type,
                        "reason": review_item.reason,
                        "original_value": "",
                        "corrected_value": "",
                        "reviewer": "",
                        "status": "PENDING",
                        "review_comment": "",
                        "reviewed_at": ""
                    })

            logger.info(f"[Phase 3] Complete — {len(article_buffer)} articles analysed")

            # =====================================================================
            # FINALISE — aggregate collective sentiment & risk
            # =====================================================================
            overall_sentiment = "NEUTRAL"
            overall_risk_score = 0.0

            if doc_risk_scores:
                overall_risk_score = round(sum(doc_risk_scores) / len(doc_risk_scores), 2)
            if doc_sentiments:
                overall_sentiment = Counter(doc_sentiments).most_common(1)[0][0]

            duration_ms = int((time.time() - start_time) * 1000)
            excel.update_row("Documents", {"document_id": document_id}, {
                "processing_status": "COMPLETED",
                "current_stage": "completed",
                "progress_percent": 100.0,
                "overall_sentiment": overall_sentiment,
                "overall_risk_score": overall_risk_score,
                "processing_completed_at": datetime.utcnow().isoformat()
            })
            logger.info(
                f"Document {document_id} complete in {duration_ms}ms — "
                f"pages={total_pages}, articles={len(article_buffer)}, "
                f"sentiment={overall_sentiment}, risk={overall_risk_score}"
            )

        except Exception as e:
            logger.error(f"Processing failed for {document_id}: {e}", exc_info=True)
            excel.update_row("Documents", {"document_id": document_id}, {
                "processing_status": "FAILED",
                "current_stage": "failed",
                "processing_error": str(e),
                "processing_completed_at": datetime.utcnow().isoformat()
            })


async def _log_audit(excel: ExcelStorageService, doc_id: str, article_id: str,
                     action: str, stage: str, details: dict = None):
    """Log an audit entry."""
    msg = f"{action} - {json.dumps(details)}" if details else action
    excel.append_row("AuditLogs", {
        "log_id": str(uuid.uuid4()),
        "document_id": doc_id,
        "article_id": article_id,
        "stage": stage,
        "status": "SUCCESS",
        "message": msg,
        "model": "",
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": datetime.utcnow().isoformat(),
        "error": "",
        "created_at": datetime.utcnow().isoformat()
    })
