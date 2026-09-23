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
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
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
from pipeline.nlp.entity.brand_matcher import BrandMatch

logger = logging.getLogger(__name__)

# Keywords signaling negative news and crises for company-specific intelligence
_NEGATIVE_KEYWORDS = {
    "REGULATORY": [
        "sebi", "rbi", "ed", "cbi", "sec", "probe", "investigation", "inquiry",
        "penalty", "fine", "penalized", "raid", "raided", "notice", "summons",
        "ban", "banned", "sanction", "sanctions", "enforcement", "violation",
        "violations", "chargesheet", "compliance failure", "irregularities",
        "scrutiny", "show-cause", "licence cancelled", "license cancelled"
    ],
    "LEGAL": [
        "lawsuit", "court", "petition", "fir", "arrest", "arrested", "guilty",
        "scam", "fraud", "bribe", "bribery", "corruption", "hindenburg",
        "charges", "convicted", "dispute", "litigation", "allegations",
        "settled allegations", "disclosure-violation", "disclosure violation"
    ],
    "FINANCIAL": [
        "quarterly loss", "net loss", "loss of", "losses", "fell sharply",
        "fell as much as", "stocks fell", "shares fell", "shares dropped",
        "plunged", "plunge", "slump", "slumped", "deficit", "default",
        "debt default", "bankruptcy", "insolvent", "insolvency", "downgrade",
        "downgraded", "crash", "crashed", "erosion", "under debt"
    ],
    "SAFETY_OPERATIONAL": [
        "strike", "protests", "protest", "fire", "accident", "explosion",
        "boycott", "data breach", "leak", "shutdown", "layoffs", "laid off",
        "scandal", "fatal", "casualties"
    ]
}


def _get_company_context(text: str, target: str, window: int = 300) -> str:
    """Extract context snippet around target in text."""
    idx = text.lower().find(target.lower())
    if idx == -1:
        return text[:window]
    start = max(0, idx - 150)
    end = min(len(text), idx + len(target) + 150)
    return text[start:end].strip()


def _extract_company_negative_info(
    full_text: str,
    company_name: str,
    aliases: List[str],
    fallback_snippet: str = ""
) -> Tuple[str, str, bool, str, str]:
    """
    Scans full_text specifically for mentions of company_name and its aliases.
    Extracts:
    1. company_context: sentences mentioning the company and adjacent context
    2. neg_info: specific extracted sentences containing negative news about this company
    3. is_negative: bool flag indicating whether negative news was identified
    4. category: crisis/negative category (e.g. REGULATORY, LEGAL, FINANCIAL, etc.)
    5. reason: short explanation of negative information
    """
    if not full_text:
        return "", "", False, "NONE", ""

    sentences = [s.strip() for s in re.split(r'(?<=[.!?\n])\s+', full_text) if s.strip()]
    if not sentences:
        sentences = [full_text]

    names_to_match = [company_name.lower()] + [a.lower() for a in aliases if a]

    matched_indices = []
    for i, s in enumerate(sentences):
        s_lower = s.lower()
        if any(nm in s_lower for nm in names_to_match):
            matched_indices.append(i)

    if not matched_indices:
        ctx = fallback_snippet or _get_company_context(full_text, company_name)
        comp_sentences = [ctx]
    else:
        expanded_indices = set()
        for idx in matched_indices:
            for offset in (-1, 0, 1):
                cur = idx + offset
                if 0 <= cur < len(sentences):
                    expanded_indices.add(cur)
        comp_sentences = [sentences[i] for i in sorted(expanded_indices)]

    company_context = " ".join(comp_sentences)
    detected_neg_sentences = []
    detected_category = "NONE"
    detected_reason = ""
    is_negative = False

    for s in comp_sentences:
        s_lower = s.lower()
        # Only consider sentences that explicitly mention THIS target company or its aliases
        if not any(nm in s_lower for nm in names_to_match):
            continue

        found_cats = []
        for cat, kw_list in _NEGATIVE_KEYWORDS.items():
            for kw in kw_list:
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, s_lower):
                    found_cats.append((cat, kw))
        if found_cats:
            detected_neg_sentences.append(s)
            is_negative = True
            if detected_category == "NONE":
                detected_category = found_cats[0][0]
                detected_reason = f"Identified in relation to {found_cats[0][1]}"

    neg_info = " ".join(detected_neg_sentences) if (is_negative and detected_neg_sentences) else ""
    return company_context, neg_info, is_negative, detected_category, detected_reason
settings = get_settings()

_processing_semaphore = asyncio.Semaphore(getattr(settings, "processing_workers", 1) or 1)
_active_tasks: Dict[str, asyncio.Task] = {}


def register_task(document_id: str, task: asyncio.Task) -> None:
    """Register an active processing task for cancellation tracking."""
    _active_tasks[document_id] = task


def unregister_task(document_id: str) -> None:
    """Unregister completed or cancelled task."""
    _active_tasks.pop(document_id, None)


def cancel_task(document_id: str) -> bool:
    """Cancel active processing task if running."""
    task = _active_tasks.pop(document_id, None)
    if task and not task.done():
        task.cancel()
        logger.info(f"Background task for document {document_id} was successfully cancelled")
        return True
    return False


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


def warmup_models() -> None:
    """
    Pre-warm OCR and translation models onto GPU at server startup.
    This avoids first-request cold-start latency (which can add 30-90 s).
    Only runs if settings.warmup_models is True.
    """
    if not getattr(settings, "warmup_models", True):
        return

    import numpy as np
    try:
        logger.info("[Warmup] Pre-loading OCR model onto GPU…")
        dummy_img = np.zeros((64, 256, 3), dtype=np.uint8)
        # Touch the reader so it allocates GPU memory now, not on first paper
        reader = _ocr_service._get_easyocr_reader("en")
        if reader is not None:
            reader.readtext(dummy_img, batch_size=1)
        logger.info("[Warmup] OCR model ready")
    except Exception as e:
        logger.warning(f"[Warmup] OCR warmup skipped: {e}")

    try:
        logger.info("[Warmup] Pre-loading translation model onto GPU…")
        _translation_service._load_model()
        logger.info("[Warmup] Translation model ready")
    except Exception as e:
        logger.warning(f"[Warmup] Translation warmup skipped: {e}")


async def process_document_task(document_id: str, job_id: str):
    """Main background task — runs 3-phase batch pipeline on a document."""
    async with _processing_semaphore:
        logger.info(f"Starting 3-phase processing for document {document_id}")
        start_time = time.time()
        excel = ExcelStorageService()

        def _is_cancelled() -> bool:
            try:
                row = excel.find_row("Documents", {"document_id": document_id})
                return bool(row and row.get("processing_status") == "CANCELLED")
            except Exception:
                return False

        if _is_cancelled():
            logger.info(f"Document {document_id} was cancelled before start, exiting.")
            return

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
            # PRE-PHASE — PDF Rendering (180 DPI for optimal speed and memory)
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
                150,  # 150 DPI: ~1000px wide A3 page — reliable for Indic script OCR (100 DPI gave 19% confidence)
                generate_thumbnails=False,  # Skip thumbnail I/O during pipeline; thumbnails only needed for UI viewer
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

            if _is_cancelled():
                logger.info(f"Document {document_id} cancelled during rendering, exiting.")
                return

            # =====================================================================
            # PHASE 1 — OCR ALL PAGES (IndicOCR)
            # Progress band: 0% → 30%
            # =====================================================================
            logger.info(f"[Phase 1] OCR scanning {total_pages} pages with IndicOCR")
            excel.update_row("Documents", {"document_id": document_id}, {
                "current_stage": "Phase 1: OCR Scan (IndicOCR)",
                "progress_percent": 2.0
            })

            # Resolve language hint once for the entire document
            doc_lang_hint = doc.get("language") or doc.get("harvest_language_code")
            if not doc_lang_hint:
                from api.documents import infer_document_language
                doc_lang_hint = infer_document_language(doc.get("file_name", ""), doc.get("publication", ""))
            if doc_lang_hint and doc.get("language") != doc_lang_hint:
                excel.update_row("Documents", {"document_id": document_id}, {"language": doc_lang_hint})
            logger.info(f"[Phase 1] Document language hint resolved as: {doc_lang_hint}")

            page_sem = asyncio.Semaphore(getattr(settings, "ocr_page_concurrency", 1) or 1)

            async def _process_single_page(page_idx: int, rp):
                if _is_cancelled():
                    return None
                async with page_sem:
                    if _is_cancelled():
                        return None
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
                        prep_path = rp.image_path
                        try:
                            prep_path = await asyncio.to_thread(
                                _preprocessing_service.preprocess, rp.image_path
                            )
                        except Exception as e:
                            logger.warning(f"Page {rp.page_number} preprocessing failed, using raw: {e}")

                        # --- OOM-safe OCR with automatic CPU fallback ---
                        async def _run_ocr_safe(path, lang_hint):
                            """Run OCR; on CUDA OOM flush VRAM and retry on CPU."""
                            result = await asyncio.to_thread(
                                _ocr_service.process_page, path, lang_hint
                            )
                            if result.status == "error" and (
                                "out of memory" in (result.error or "").lower() or
                                "cudaerror" in (result.error or "").lower()
                            ):
                                # CUDA OOM — flush and retry on CPU
                                logger.warning(
                                    f"Page {rp.page_number}: CUDA OOM detected, "
                                    f"flushing VRAM and retrying on CPU..."
                                )
                                try:
                                    import torch
                                    torch.cuda.empty_cache()
                                except Exception:
                                    pass
                                # Temporarily force CPU for this page
                                orig_gpu = _ocr_service._gpu_available
                                _ocr_service._gpu_available = False
                                try:
                                    result = await asyncio.to_thread(
                                        _ocr_service.process_page, path, lang_hint
                                    )
                                finally:
                                    _ocr_service._gpu_available = orig_gpu
                            return result

                        ocr_result = await _run_ocr_safe(prep_path, doc_lang_hint)
                        # NOTE: torch.cuda.empty_cache() intentionally removed from per-page loop.
                        # It does NOT free VRAM — it releases PyTorch's cache of freed tensors,
                        # forcing CUDA to reallocate on next use, adding ~50-200ms overhead per page.
                        # VRAM accumulation is prevented by the model singleton pattern.

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

                    p1_progress = 2.0 + ((page_idx + 1) / total_pages) * 28.0
                    excel.update_row("Documents", {"document_id": document_id}, {
                        "current_stage": f"Phase 1: OCR Scan — page {rp.page_number}/{total_pages} (IndicOCR)",
                        "progress_percent": round(p1_progress, 1)
                    })
                    return (page_dict, rp, ocr_boxes)

            # NOTE: OCR runs sequentially — GPU (EasyOCR/CUDA) is not thread-safe.
            # Page coroutines are created and awaited one at a time to avoid
            # CUDA memory races and unawaited-coroutine warnings.
            page_results = []
            for idx, rp in enumerate(pdf_result.pages):
                result = await _process_single_page(idx, rp)
                page_results.append(result)

            if _is_cancelled():
                logger.info(f"Document {document_id} was cancelled during OCR, exiting.")
                return

            pages_to_process = [r for r in page_results if r is not None]
            # Ensure in original page order
            pages_to_process.sort(key=lambda x: x[0]["page_number"])

            logger.info(f"[Phase 1] Complete — {len(pages_to_process)} pages OCR'd")

            # =====================================================================
            # PHASE 2 — ARTICLE EXTRACTION + TRANSLATION (IndicTrans2)
            # Progress band: 30% → 65%
            # Translations are gathered concurrently for ALL articles on ALL pages.
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

            # ---- Sub-step 2a: Layout extraction for ALL pages ----
            layout_tasks = [
                asyncio.to_thread(
                    analyze_layout, ocr_boxes,
                    page["page_width"] or 2480, page["page_height"] or 3508
                )
                for (page, rp, ocr_boxes) in pages_to_process
            ]
            layout_results = await asyncio.gather(*layout_tasks)

            # Collect all articles from all pages into one flat list
            all_articles_to_process = []  # list of (page, rp, extracted_articles)
            for (page, rp, ocr_boxes), extracted_articles in zip(pages_to_process, layout_results):
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
                if extracted_articles:
                    all_articles_to_process.append((page, rp, extracted_articles))

            # ---- Sub-step 2b: Language detection — all articles concurrently ----
            async def _detect_language(full_text: str):
                return await asyncio.to_thread(
                    _language_service.detect_multi, full_text
                )

            lang_tasks = [
                _detect_language(ext_art.full_text)
                for (page, rp, articles) in all_articles_to_process
                for ext_art in articles
                if ext_art.word_count >= 2
            ]
            lang_results = await asyncio.gather(*lang_tasks)

            # ---- Sub-step 2c: Translation — all non-English articles concurrently ----
            # Build (article, lang_result) pairs first
            article_lang_pairs = []
            lang_idx = 0
            for (page, rp, articles) in all_articles_to_process:
                for ext_art in articles:
                    if ext_art.word_count < 2:
                        continue
                    lang_res = lang_results[lang_idx]
                    lang_idx += 1
                    detected_lang = (
                        lang_res.primary.language
                        if lang_res and lang_res.primary else "en"
                    )
                    lang_confidence = (
                        lang_res.primary.confidence
                        if lang_res and lang_res.primary else 0.0
                    )
                    article_lang_pairs.append((page, ext_art, detected_lang, lang_confidence))

            # article_lang_pairs is built; count non-English articles that need translation
            articles_to_translate_count = sum(
                1 for (_, _, lang, conf) in article_lang_pairs
                if lang != "en" and conf > 40
            )

            excel.update_row("Documents", {"document_id": document_id}, {
                "current_stage": f"Phase 2: Translating {articles_to_translate_count} articles — GPU batch (IndicTrans2)",
                "progress_percent": 33.0
            })

            # ---- Sub-step 2c (optimised): Group articles by source language and
            # send each language group as a single GPU batch call. This maximises
            # GPU utilisation — one model.generate() per language instead of one per article.
            from collections import defaultdict
            lang_groups: dict = defaultdict(list)  # lang -> [(pair_index, text)]
            passthrough_map: dict = {}  # pair_index -> original text (for English/low-confidence)

            for pair_idx, (page, ext_art, detected_lang, lang_confidence) in enumerate(article_lang_pairs):
                if detected_lang == "en" or lang_confidence <= 40:
                    passthrough_map[pair_idx] = ext_art.full_text
                else:
                    lang_groups[detected_lang].append((pair_idx, ext_art.full_text))

            # Translate each language group as a batch
            batch_translation_map: dict = {}  # pair_index -> TranslationServiceResult
            for lang, items in lang_groups.items():
                pair_indices = [i for i, _ in items]
                texts_to_translate = [t for _, t in items]
                logger.info(f"[Phase 2] Batch translating {len(texts_to_translate)} articles from '{lang}' → GPU batch")
                try:
                    batch_results = await asyncio.to_thread(
                        _translation_service.translate_batch,
                        texts_to_translate,
                        lang,
                        "en",
                    )
                    for pair_idx, trans_result in zip(pair_indices, batch_results):
                        batch_translation_map[pair_idx] = trans_result
                except Exception as e:
                    logger.warning(f"Batch translation failed for lang '{lang}': {e} — falling back to original text")
                    for pair_idx, orig_text in items:
                        batch_translation_map[pair_idx] = None

            # Build translation_results list aligned with article_lang_pairs
            translation_results = []
            for pair_idx, (page, ext_art, detected_lang, lang_confidence) in enumerate(article_lang_pairs):
                if pair_idx in passthrough_map:
                    translation_results.append((passthrough_map[pair_idx], None))
                else:
                    trans_res = batch_translation_map.get(pair_idx)
                    if trans_res and getattr(trans_res, "status", "success") == "success" and trans_res.translated_text:
                        translation_results.append((trans_res.translated_text, trans_res))
                    else:
                        translation_results.append((ext_art.full_text, trans_res))

            # Flush GPU VRAM cache after batch translation to free fragmented memory
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    logger.info("[Phase 2] GPU VRAM cache flushed after batch translation")
            except Exception:
                pass

            # ---- Sub-step 2d: Persist articles + translations to Excel ----
            for art_idx, ((page, ext_art, detected_lang, lang_confidence), (translated_text, trans_result)) in enumerate(
                zip(article_lang_pairs, translation_results)
            ):
                if _is_cancelled():
                    logger.info(f"Document {document_id} cancelled during Phase 2 persist, exiting.")
                    return

                total_articles_extracted += 1
                article_id = str(uuid.uuid4())

                p2_progress = 35.0 + (art_idx / max(len(article_lang_pairs), 1)) * 28.0
                excel.update_row("Documents", {"document_id": document_id}, {
                    "current_stage": f"Phase 2: Saving articles — {art_idx + 1}/{len(article_lang_pairs)}",
                    "progress_percent": round(p2_progress, 1)
                })

                translation_confidence = None
                if trans_result is not None:
                    translation_confidence = getattr(trans_result, "confidence", None)

                # Save article record
                article_dict = {
                    "article_id": article_id,
                    "document_id": document_id,
                    "page_id": page["page_id"],
                    "page_number": page["page_number"],
                    "headline": ext_art.headline,
                    "original_text": ext_art.full_text,
                    "language": detected_lang,
                    "article_type": ext_art.article_type,
                    "x1": ext_art.bbox_x,
                    "y1": ext_art.bbox_y,
                    "x2": (ext_art.bbox_x or 0) + (ext_art.bbox_width or 0),
                    "y2": (ext_art.bbox_y or 0) + (ext_art.bbox_height or 0),
                    "ocr_confidence": page["ocr_confidence"],
                    "article_confidence": ext_art.confidence,
                    "created_at": datetime.utcnow().isoformat()
                }
                excel.append_row("Articles", article_dict)

                if trans_result is not None and getattr(trans_result, "status", None) == "success":
                    trans_dict = {
                        "translation_id": str(uuid.uuid4()),
                        "article_id": article_id,
                        "source_language": detected_lang,
                        "target_language": "en",
                        "original_text": ext_art.full_text,
                        "translated_text": translated_text,
                        "translation_confidence": translation_confidence,
                        "entity_protected": getattr(trans_result, "entities_protected", []),
                        "review_required": getattr(trans_result, "review_required", False),
                        "translation_model": getattr(trans_result, "model_used", "none"),
                        "created_at": datetime.utcnow().isoformat()
                    }
                    excel.append_row("Translations", trans_dict)

                # Buffer for Phase 3
                article_buffer.append({
                    "article_id": article_id,
                    "page": page,
                    "ext_article": ext_art,
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

            # Pre-initialize NLP services once for Phase 3
            from pipeline.nlp.entity.extractor import EntityExtractor
            from pipeline.nlp.entity.brand_matcher import BrandMatcher
            entity_extractor = EntityExtractor()
            brand_matcher = BrandMatcher()
            brand_matcher.load_brands(brand_dicts)

            # Cache LFM availability ONCE before the loop — avoids N HTTP calls to Ollama
            lfm_available = _lfm_service.is_available()
            logger.info(f"[Phase 3] LFM available: {lfm_available}")

            doc_sentiments = []
            doc_risk_scores = []
            total_art = max(len(article_buffer), 1)

            for art_idx, buf in enumerate(article_buffer):
                # Throttle cancel check to every 5 articles (Excel scan is expensive)
                if art_idx % 5 == 0 and _is_cancelled():
                    logger.info(f"Document {document_id} cancelled during Phase 3, exiting.")
                    return

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

                # Entity detection — scan page for all named entities
                detected_entities = await asyncio.to_thread(
                    entity_extractor.extract, translated_text, "en"
                )
                entity_texts = [e.text for e in detected_entities]

                # Save all detected entities to storage
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
                        "verification_status": "verified" if ent.text in monitored_brand_names else "unverified",
                        "created_at": datetime.utcnow().isoformat()
                    })

                # Brand matching — scan for companies and verify against provided list
                brand_matches = brand_matcher.match(translated_text, entity_texts)

                # Group verified company matches by their canonical name in the provided list
                verified_companies: Dict[str, List[BrandMatch]] = {}
                for bm in brand_matches:
                    bname = bm.brand_name
                    if bname not in verified_companies:
                        verified_companies[bname] = []
                    verified_companies[bname].append(bm)

                # Also verify any detected organization/brand entities against the provided list
                for ent in detected_entities:
                    if ent.entity_type in ("ORGANIZATION", "BRAND") or getattr(ent, "is_monitored_brand", False):
                        ent_lower = ent.text.strip().lower()
                        for b in brands:
                            b_name = b["brand_name"]
                            aliases_str = b.get("aliases") or ""
                            b_aliases = [a.strip().lower() for a in aliases_str.split(",") if a.strip()]
                            if ent_lower == b_name.lower() or ent_lower in b_aliases:
                                if b_name not in verified_companies:
                                    bm = BrandMatch(
                                        brand_id=str(b["brand_id"]),
                                        brand_name=b_name,
                                        matched_text=ent.text,
                                        match_type="entity",
                                        confidence=ent.confidence or 0.90,
                                        context_snippet=_get_company_context(translated_text, ent.text),
                                    )
                                    verified_companies[b_name] = [bm]
                                break

                lfm_status = "skipped"

                # For EACH company in the provided list that was verified on this page:
                # Extract relevant negative information and record clearly per company.
                for company_name, matches_list in verified_companies.items():
                    primary_match = matches_list[0]
                    c_brand_obj = next((b for b in brands if b["brand_name"].lower() == company_name.lower()), None)
                    c_aliases = []
                    if c_brand_obj:
                        raw_aliases = c_brand_obj.get("aliases") or ""
                        c_aliases = [a.strip() for a in raw_aliases.split(",") if a.strip()]

                    # Extract context & negative information specifically for this company
                    company_context, neg_info, auto_neg, auto_cat, auto_reason = _extract_company_negative_info(
                        translated_text, company_name, c_aliases, primary_match.context_snippet
                    )

                    comp_status = "skipped"
                    comp_sentiment = "NEUTRAL"
                    comp_sent_conf = 50.0
                    comp_crisis = False
                    comp_crisis_topic = "NONE"
                    comp_crisis_severity = 0.0
                    comp_summary = neg_info or company_context or ext_article.headline
                    comp_reason = auto_reason

                    # Targeted LFM analysis specifically for this company
                    if lfm_available:
                        try:
                            lfm_result = await asyncio.to_thread(
                                _lfm_service.analyze,
                                company_context or translated_text,
                                entity_texts,
                                company_name
                            )
                            if lfm_result and lfm_result.status == "success":
                                comp_status = "success"
                                lfm_status = "success"
                                comp_sentiment = str(lfm_result.sentiment.get("sentiment", "NEUTRAL")).upper()
                                comp_sent_conf = float(lfm_result.sentiment.get("confidence", 0.5) * 100)
                                comp_crisis = bool(lfm_result.crisis.get("crisis", False))
                                comp_crisis_topic = str(lfm_result.crisis.get("category", "GENERAL")).upper()
                                comp_crisis_severity = float(lfm_result.crisis.get("severity", 0.0))
                                if comp_sentiment == "NEGATIVE":
                                    comp_summary = lfm_result.summary or neg_info or ext_article.headline
                                    comp_reason = lfm_result.crisis.get("reason") or auto_reason
                                else:
                                    comp_summary = lfm_result.summary or company_context or ext_article.headline
                        except Exception as e:
                            logger.warning(f"LFM company analysis failed for {company_name}: {e}")

                    # Fallback sentiment analysis focused specifically on this company
                    if comp_status != "success":
                        try:
                            if auto_neg:
                                comp_sentiment = "NEGATIVE"
                                comp_sent_conf = 88.0
                                comp_crisis = True
                                comp_crisis_topic = auto_cat
                                comp_crisis_severity = 0.75
                                comp_summary = neg_info
                                comp_status = "success"
                            else:
                                sent_res = await asyncio.to_thread(
                                    _sentiment_analyzer.analyze,
                                    company_context or ext_article.full_text,
                                    company_context or translated_text,
                                    detected_lang
                                )
                                comp_sentiment = str(sent_res.label).upper()
                                comp_sent_conf = float(sent_res.confidence)
                                comp_status = "success"
                                if comp_sentiment == "NEGATIVE":
                                    comp_crisis = True
                                    comp_crisis_topic = auto_cat
                                    comp_crisis_severity = 0.60
                                    comp_summary = neg_info or company_context or ext_article.headline
                                else:
                                    comp_summary = company_context or ext_article.headline
                        except Exception as e:
                            logger.warning(f"Sentiment fallback failed for {company_name}: {e}")

                    doc_sentiments.append(comp_sentiment)

                    # Calculate crisis & risk scores specifically for this company
                    sentiment_severity = 100 if comp_sentiment == "NEGATIVE" else (50 if comp_sentiment == "NEUTRAL" else 0)
                    brand_relevance = 85
                    crisis_severity = comp_crisis_severity if comp_crisis else 0.0
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

                    # 1. Record AI Analysis specifically for this company
                    excel.append_row("AIAnalysis", {
                        "analysis_id": str(uuid.uuid4()),
                        "article_id": article_id,
                        "brand_name": company_name,
                        "summary": comp_summary or ext_article.headline,
                        "sentiment": comp_sentiment,
                        "sentiment_confidence": comp_sent_conf,
                        "crisis_category": comp_crisis_topic if comp_crisis else "NONE",
                        "crisis_reason": comp_reason or ("Negative news identified" if comp_sentiment == "NEGATIVE" else "Standard coverage"),
                        "ai_confidence": comp_sent_conf,
                        "model_name": "lfm-sentiment-pipeline",
                        "created_at": datetime.utcnow().isoformat()
                    })

                    # 2. Record CrisisScores specifically for this company
                    excel.append_row("CrisisScores", {
                        "score_id": str(uuid.uuid4()),
                        "article_id": article_id,
                        "brand_name": company_name,
                        "sentiment_score": sentiment_severity,
                        "brand_relevance_score": brand_relevance,
                        "crisis_severity_score": crisis_severity,
                        "publication_reach_score": publication_reach,
                        "ai_confidence_score": avg_ai_conf,
                        "final_crisis_score": final_crisis_score,
                        "severity": severity_label,
                        "created_at": datetime.utcnow().isoformat()
                    })

                    # 3. Record BrandMentions specifically for this company
                    excel.append_row("BrandMentions", {
                        "mention_id": str(uuid.uuid4()),
                        "article_id": article_id,
                        "brand_name": company_name,
                        "matched_text": primary_match.matched_text,
                        "match_type": primary_match.match_type,
                        "match_confidence": primary_match.confidence,
                        "context": company_context or primary_match.context_snippet,
                        "verified_by_lfm": comp_status == "success",
                        "created_at": datetime.utcnow().isoformat()
                    })

                    # 4. Record Alerts specifically for this company if negative news / crisis
                    if final_crisis_score >= 50 or comp_crisis or (comp_sentiment == "NEGATIVE" and final_crisis_score >= 25):
                        excel.append_row("Alerts", {
                            "alert_id": str(uuid.uuid4()),
                            "article_id": article_id,
                            "document_id": document_id,
                            "publication": doc.get("publication", "Regional Broadsheet"),
                            "page_number": page["page_number"],
                            "brand_name": company_name,
                            "language": detected_lang,
                            "headline": ext_article.headline,
                            "sentiment": comp_sentiment,
                            "crisis_category": comp_crisis_topic if comp_crisis else "GENERAL",
                            "crisis_score": final_crisis_score,
                            "severity": severity_label,
                            "summary": comp_summary or ext_article.headline,
                            "reason": f"Negative news identified for {company_name}: {comp_reason or comp_summary}",
                            "evidence_page_path": page["image_path"],
                            "evidence_article_coordinates": f"{ext_article.bbox_x},{ext_article.bbox_y},{ext_article.bbox_width},{ext_article.bbox_height}",
                            "alert_status": "NEW",
                            "created_at": datetime.utcnow().isoformat()
                        })
                        await _log_audit(excel, document_id, article_id, "alert_generated", "alert_generation",
                                         details={"brand": company_name, "risk_score": final_crisis_score})

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
            try:
                await _log_audit(excel, document_id, None, "pipeline_failed", "pipeline", details={"error": str(e)})
            except Exception:
                pass
        finally:
            unregister_task(document_id)


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
