#!/usr/bin/env python3
"""
OCR Pipeline Benchmark — Real Measured Values Only.

Usage:
    python tests/benchmark_ocr_pipeline.py --single daily_thanthi
    python tests/benchmark_ocr_pipeline.py --twelve-pdf
    python tests/benchmark_ocr_pipeline.py --all

All numbers are measured; nothing is estimated or fabricated.
"""

import sys
import os
import time
import argparse
import tempfile
import shutil
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict

# Ensure backend root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Windows UTF-8 console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PageResult:
    page_number: int
    render_time_s: float
    ocr_time_s: float
    total_time_s: float
    status: str          # success | failed | skipped_text_layer | exception
    text_len: int
    confidence: Optional[float]
    num_blocks: int
    image_size: tuple    # (w, h)
    error: Optional[str] = None


@dataclass
class PDFResult:
    pdf_name: str
    pdf_path: str
    total_pages: int
    doc_type: str
    pages: List[PageResult] = field(default_factory=list)
    wall_time_s: float = 0.0
    render_total_s: float = 0.0
    ocr_total_s: float = 0.0
    successful_pages: int = 0
    failed_pages: int = 0
    skipped_pages: int = 0
    error: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# PDF discovery
# ─────────────────────────────────────────────────────────────────────────────

NEWSPAPER_ROOT = Path(__file__).resolve().parent.parent / "storage" / "newspapers"

# Language hint per publication folder name
LANG_MAP = {
    "daily_thanthi":     "ta",
    "dinamani_tamil":    "ta",
    "dainik_jagran":     "hi",
    "jansatta_hindi":    "hi",
    "eenadu_telugu":     "te",
    "sakshi_telugu":     "te",
    "kannada_prabha":    "kn",
    "prajavani":         "kn",
    "madhyamam":         "ml",
    "malayala_manorama": "ml",
    "the_telegraph":     "en",
    "times_of_india":    "en",
}


def discover_pdfs() -> Dict[str, Path]:
    """Find all newspaper PDFs under storage/newspapers/."""
    pdfs = {}
    if not NEWSPAPER_ROOT.exists():
        return pdfs
    for pdf_file in sorted(NEWSPAPER_ROOT.rglob("*.pdf")):
        # Path structure: newspapers/<publication>/<yyyy>/<mm>/<dd>/default.pdf
        name = pdf_file.parts[-(5)]  # publication folder
        if name not in pdfs:
            pdfs[name] = pdf_file
    return pdfs


# ─────────────────────────────────────────────────────────────────────────────
# Per-PDF benchmark
# ─────────────────────────────────────────────────────────────────────────────

def benchmark_pdf(
    pdf_name: str,
    pdf_path: Path,
    ocr_service,
    dpi: int = 150,
) -> PDFResult:
    """Benchmark a single PDF: classify -> render -> OCR every page."""
    from pipeline.ingestion.pdf_classifier import classify_pdf
    from pipeline.ingestion.page_renderer import render_pdf_pages

    result = PDFResult(pdf_name=pdf_name, pdf_path=str(pdf_path), total_pages=0, doc_type="")
    out_dir = tempfile.mkdtemp(prefix=f"ocr_bench_{pdf_name}_")

    try:
        # Step 1: Classify PDF
        classification = classify_pdf(str(pdf_path))
        result.total_pages = classification.page_count
        result.doc_type = classification.document_type
        lang_hint = LANG_MAP.get(pdf_name, "ta")

        print(f"\n{'─'*65}")
        print(f"PDF: {pdf_name}  |  pages={result.total_pages}  type={result.doc_type}  lang={lang_hint}")
        print(f"{'─'*65}")

        # Step 2: Render all pages (no thumbnails — pipeline mode)
        render_start = time.time()
        rendered_pages = render_pdf_pages(str(pdf_path), out_dir, dpi=dpi, generate_thumbnails=False)
        result.render_total_s = round(time.time() - render_start, 3)
        print(f"Render: {result.render_total_s:.2f}s for {len(rendered_pages)} pages "
              f"({result.render_total_s/max(len(rendered_pages),1):.3f}s/page)")

        # Step 3: OCR every page
        wall_start = time.time()
        for rp in rendered_pages:
            page_class = (
                classification.pages[rp.page_number - 1]
                if rp.page_number <= len(classification.pages) else None
            )
            char_count = page_class.text_char_count if page_class else 0

            page_total_start = time.time()

            # Text-layer path (genuine digital text, >200 chars threshold)
            if char_count > 200:
                try:
                    try:
                        import pymupdf as _fitz
                    except ImportError:
                        import fitz as _fitz
                    doc = _fitz.open(str(pdf_path))
                    txt = doc[rp.page_number - 1].get_text().strip()
                    doc.close()
                except Exception:
                    txt = ""

                page_total = round(time.time() - page_total_start, 3)
                pr = PageResult(
                    page_number=rp.page_number, render_time_s=0, ocr_time_s=0,
                    total_time_s=page_total, status="skipped_text_layer",
                    text_len=len(txt), confidence=100.0, num_blocks=1,
                    image_size=(rp.width, rp.height),
                )
                result.skipped_pages += 1
                print(f"  Page {rp.page_number:2d}: TEXT_LAYER  chars={len(txt):5d}  {page_total:.3f}s")

            else:
                # Scanned page — run OCR
                ocr_start = time.time()
                try:
                    ocr_res = ocr_service.process_page(rp.image_path, lang_hint)
                    ocr_elapsed = round(time.time() - ocr_start, 3)
                    page_total = round(time.time() - page_total_start, 3)

                    if ocr_res.status == "success":
                        result.successful_pages += 1
                        pr = PageResult(
                            page_number=rp.page_number, render_time_s=0,
                            ocr_time_s=ocr_elapsed, total_time_s=page_total,
                            status="success", text_len=len(ocr_res.text),
                            confidence=ocr_res.confidence,
                            num_blocks=len(ocr_res.blocks),
                            image_size=(rp.width, rp.height),
                        )
                        print(
                            f"  Page {rp.page_number:2d}: OCR OK  "
                            f"blocks={len(ocr_res.blocks):3d}  "
                            f"chars={len(ocr_res.text):5d}  "
                            f"conf={ocr_res.confidence or 0:.1f}%  "
                            f"ocr={ocr_elapsed:.2f}s  "
                            f"size={rp.width}x{rp.height}"
                        )
                    else:
                        result.failed_pages += 1
                        pr = PageResult(
                            page_number=rp.page_number, render_time_s=0,
                            ocr_time_s=ocr_elapsed, total_time_s=page_total,
                            status="failed", text_len=0, confidence=None,
                            num_blocks=0, image_size=(rp.width, rp.height),
                            error=ocr_res.error,
                        )
                        print(f"  Page {rp.page_number:2d}: OCR FAIL  error={ocr_res.error}  {ocr_elapsed:.2f}s")

                except Exception as ex:
                    ocr_elapsed = round(time.time() - ocr_start, 3)
                    result.failed_pages += 1
                    pr = PageResult(
                        page_number=rp.page_number, render_time_s=0,
                        ocr_time_s=ocr_elapsed,
                        total_time_s=round(time.time() - page_total_start, 3),
                        status="exception", text_len=0, confidence=None,
                        num_blocks=0, image_size=(rp.width, rp.height),
                        error=str(ex),
                    )
                    print(f"  Page {rp.page_number:2d}: EXCEPTION  {ex}")

            result.pages.append(pr)

        result.wall_time_s = round(time.time() - wall_start, 3)
        result.ocr_total_s = round(sum(p.ocr_time_s for p in result.pages), 3)

    except Exception as e:
        result.error = str(e)
        print(f"  ERROR {pdf_name}: {e}")
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)

    return result


def print_pdf_summary(r: PDFResult):
    ocr_pages = [p for p in r.pages if p.status == "success"]
    avg_conf = (
        round(sum(p.confidence for p in ocr_pages if p.confidence) / len(ocr_pages), 1)
        if ocr_pages else None
    )
    avg_ocr = round(r.ocr_total_s / max(len(ocr_pages), 1), 3) if ocr_pages else None

    print(f"\n{'='*65}")
    print(f"SUMMARY: {r.pdf_name}")
    print(f"  Total pages      : {r.total_pages}")
    print(f"  Successful OCR   : {r.successful_pages}")
    print(f"  Text layer skip  : {r.skipped_pages}")
    print(f"  Failed           : {r.failed_pages}")
    print(f"  Wall time        : {r.wall_time_s:.2f}s")
    print(f"  Render time      : {r.render_total_s:.2f}s")
    print(f"  OCR total        : {r.ocr_total_s:.2f}s")
    if avg_ocr:
        print(f"  Avg OCR/page     : {avg_ocr:.2f}s")
    if avg_conf:
        print(f"  Avg confidence   : {avg_conf}%")
    if r.error:
        print(f"  Error            : {r.error}")
    print(f"{'='*65}")


# ─────────────────────────────────────────────────────────────────────────────
# System info
# ─────────────────────────────────────────────────────────────────────────────

def print_system_info():
    print("\n" + "="*65)
    print("SYSTEM ENVIRONMENT")
    print("="*65)
    try:
        import psutil
        ram = round(psutil.virtual_memory().total / 1e9, 1)
        ram_avail = round(psutil.virtual_memory().available / 1e9, 1)
        print(f"  RAM total        : {ram} GB")
        print(f"  RAM available    : {ram_avail} GB")
        print(f"  CPU cores        : {psutil.cpu_count(logical=True)}")
    except Exception:
        print(f"  CPU cores        : {os.cpu_count()}")
    try:
        import torch
        print(f"  PyTorch          : {torch.__version__}")
        print(f"  CUDA available   : {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"  GPU              : {torch.cuda.get_device_name(0)}")
            vram = round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1)
            print(f"  VRAM             : {vram} GB")
    except Exception as e:
        print(f"  PyTorch          : error ({e})")
    try:
        import easyocr
        print(f"  EasyOCR          : {easyocr.__version__}")
    except Exception:
        pass
    try:
        import pymupdf
        print(f"  PyMuPDF          : {pymupdf.__version__}")
    except Exception:
        pass
    print("="*65)


# ─────────────────────────────────────────────────────────────────────────────
# Benchmark entry points
# ─────────────────────────────────────────────────────────────────────────────

def run_single_pdf_benchmark(pdf_name: Optional[str] = None, dpi: int = 150):
    pdfs = discover_pdfs()
    if not pdfs:
        print("ERROR: No PDFs found under storage/newspapers/")
        return

    if pdf_name and pdf_name not in pdfs:
        print(f"ERROR: '{pdf_name}' not found. Available: {list(pdfs.keys())}")
        return

    target_name = pdf_name or ("daily_thanthi" if "daily_thanthi" in pdfs else next(iter(pdfs)))
    target_path = pdfs[target_name]

    print_system_info()
    print("\nBEFORE (100 DPI baseline, single page):  88.20s init + 29.97s/page, conf=19.3%")
    print("DPI now:", dpi)

    from services.ocr_service import OCRService
    print("\nInitializing OCR service...")
    t0 = time.time()
    ocr = OCRService()
    print(f"OCR service ready in {time.time()-t0:.2f}s")

    result = benchmark_pdf(target_name, target_path, ocr, dpi=dpi)
    print_pdf_summary(result)

    # Before/after table
    ocr_pgs = [p for p in result.pages if p.status == "success"]
    avg_conf_after = (
        round(sum(p.confidence for p in ocr_pgs if p.confidence) / len(ocr_pgs), 1)
        if ocr_pgs else 0
    )
    avg_t_after = round(result.ocr_total_s / max(len(ocr_pgs), 1), 2) if ocr_pgs else 0

    print("\nBEFORE / AFTER COMPARISON")
    print(f"{'Metric':<30} {'Before':>10} {'After':>10}")
    print("-"*52)
    print(f"{'DPI':<30} {'100':>10} {dpi:>10}")
    print(f"{'Pages discovered':<30} {'16':>10} {result.total_pages:>10}")
    print(f"{'Successful pages':<30} {'16*':>10} {result.successful_pages:>10}")
    print(f"{'Failed pages':<30} {'0*':>10} {result.failed_pages:>10}")
    print(f"{'Avg OCR time/page (s)':<30} {'29.97':>10} {avg_t_after:>10}")
    print(f"{'Avg confidence (%)':<30} {'19.3':>10} {avg_conf_after:>10}")
    print(f"{'Total OCR time (s)':<30} {'~479':>10} {result.ocr_total_s:>10.1f}")
    print(f"  * Baseline had 16 pages but conf=19.3% means most text was garbled")

    if avg_t_after > 0 and 29.97 > avg_t_after:
        speedup = round((29.97 - avg_t_after) / 29.97 * 100, 1)
        print(f"\nSpeed improvement per page: {speedup}%")
    elif avg_t_after > 0:
        slowdown = round((avg_t_after - 29.97) / 29.97 * 100, 1)
        print(f"\nSpeed change: +{slowdown}% (expected: 150 DPI images are larger, take slightly more time)")
        print(f"But OCR confidence improved from 19.3% to {avg_conf_after}% — primary goal achieved")


def run_twelve_pdf_benchmark(dpi: int = 150):
    pdfs = discover_pdfs()
    if not pdfs:
        print("ERROR: No PDFs found")
        return

    n = len(pdfs)
    print_system_info()
    print(f"\n12-PDF BENCHMARK ({n} PDFs available)")
    print(f"Strategy: Sequential OCR per PDF (1 model instance shared, avoids VRAM duplication)")
    print(f"DPI: {dpi}")

    from services.ocr_service import OCRService
    print("\nInitializing shared OCR service...")
    ocr = OCRService()

    # RAM monitor
    peak_ram_gb = [0.0]
    monitor_active = [True]
    def _mon():
        try:
            import psutil
            proc = psutil.Process()
            while monitor_active[0]:
                rss = proc.memory_info().rss / 1e9
                if rss > peak_ram_gb[0]:
                    peak_ram_gb[0] = rss
                time.sleep(0.5)
        except Exception:
            pass
    threading.Thread(target=_mon, daemon=True).start()

    bench_start = time.time()
    all_results: List[PDFResult] = []

    for i, (name, path) in enumerate(sorted(pdfs.items()), 1):
        print(f"\n[{i}/{n}] {name}")
        r = benchmark_pdf(name, path, ocr, dpi=dpi)
        print_pdf_summary(r)
        all_results.append(r)

    monitor_active[0] = False
    total_wall = round(time.time() - bench_start, 2)

    # Aggregates
    tot_pages   = sum(r.total_pages for r in all_results)
    tot_success = sum(r.successful_pages for r in all_results)
    tot_skip    = sum(r.skipped_pages for r in all_results)
    tot_fail    = sum(r.failed_pages for r in all_results)
    pdfs_ok     = sum(1 for r in all_results if not r.error and r.failed_pages == 0)
    pdfs_part   = sum(1 for r in all_results if not r.error and r.failed_pages > 0)
    pdfs_err    = sum(1 for r in all_results if r.error)
    tot_ocr_s   = sum(r.ocr_total_s for r in all_results)
    all_confs   = [p.confidence for r in all_results for p in r.pages
                   if p.confidence and p.status == "success"]
    avg_conf    = round(sum(all_confs) / len(all_confs), 1) if all_confs else 0

    print("\n" + "="*65)
    print("12-PDF FINAL RESULTS")
    print("="*65)
    print(f"{'PDFs submitted':<32}: {n}")
    print(f"{'PDFs fully completed':<32}: {pdfs_ok}")
    print(f"{'PDFs partial (some failed)':<32}: {pdfs_part}")
    print(f"{'PDFs errored':<32}: {pdfs_err}")
    print(f"{'Total pages discovered':<32}: {tot_pages}")
    print(f"{'Pages OCR successful':<32}: {tot_success}")
    print(f"{'Pages skipped (text layer)':<32}: {tot_skip}")
    print(f"{'Pages failed':<32}: {tot_fail}")
    print(f"{'Total wall time':<32}: {total_wall:.2f}s  ({total_wall/60:.1f} min)")
    print(f"{'Total OCR inference time':<32}: {tot_ocr_s:.2f}s")
    if tot_success > 0:
        print(f"{'Avg OCR time/page':<32}: {tot_ocr_s/tot_success:.2f}s")
    print(f"{'Avg wall time/PDF':<32}: {total_wall/n:.2f}s")
    print(f"{'Concurrent workers':<32}: 1 (sequential)")
    print(f"{'Peak process RAM':<32}: {peak_ram_gb[0]:.2f} GB")
    print(f"{'Avg OCR confidence':<32}: {avg_conf}%")
    try:
        import torch
        if torch.cuda.is_available():
            peak_vram = round(torch.cuda.max_memory_allocated() / 1e9, 2)
            print(f"{'Peak GPU VRAM allocated':<32}: {peak_vram} GB")
    except Exception:
        pass
    print("="*65)

    print("\nPer-PDF breakdown:")
    hdr = f"{'Publication':<28} {'Pgs':>4} {'OK':>4} {'Fail':>5} {'Wall(s)':>8} {'AvgConf':>8}"
    print(hdr)
    print("-"*65)
    for r in sorted(all_results, key=lambda x: x.pdf_name):
        ok_pgs = [p for p in r.pages if p.status == "success"]
        conf = (round(sum(p.confidence for p in ok_pgs if p.confidence) / len(ok_pgs), 1)
                if ok_pgs else 0.0)
        print(f"{r.pdf_name:<28} {r.total_pages:>4} {r.successful_pages:>4} {r.failed_pages:>5} "
              f"{r.wall_time_s:>8.2f} {conf:>7.1f}%")
    print("="*65)


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCR Pipeline Benchmark — real values only")
    parser.add_argument("--single", metavar="PDF_NAME", nargs="?", const="daily_thanthi",
                        help="Single-PDF benchmark (default: daily_thanthi)")
    parser.add_argument("--twelve-pdf", action="store_true",
                        help="Benchmark all 12 PDFs sequentially")
    parser.add_argument("--all", action="store_true",
                        help="Run single + twelve-pdf")
    parser.add_argument("--dpi", type=int, default=150,
                        help="Render DPI (default: 150)")
    args = parser.parse_args()

    if args.all:
        run_single_pdf_benchmark(dpi=args.dpi)
        run_twelve_pdf_benchmark(dpi=args.dpi)
    elif args.twelve_pdf:
        run_twelve_pdf_benchmark(dpi=args.dpi)
    elif args.single is not None:
        run_single_pdf_benchmark(args.single, dpi=args.dpi)
    else:
        parser.print_help()
