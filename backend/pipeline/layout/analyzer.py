"""
Newspaper Layout Analyzer.

Multi-strategy article segmentation system that:
1. Detects columns using vertical projection profiles
2. Classifies blocks as headlines, body, ads, etc.
3. Groups OCR blocks into coherent articles
4. Tries multiple strategies and selects the best

Core implementation of the trial-and-error segmentation philosophy.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Any

try:
    import numpy as np
except Exception:
    np = None


def _mean(values, default=0.0):
    if not values:
        return default
    return float(sum(values) / len(values))


def _std(values):
    if len(values) <= 1:
        return 0.0
    m = _mean(values)
    variance = sum((x - m) ** 2 for x in values) / len(values)
    return float(variance ** 0.5)


def _histogram_bins(values, num_bins=20, val_range=(0, 1000)):
    min_v, max_v = val_range
    if max_v <= min_v:
        max_v = min_v + 1
    bin_width = (max_v - min_v) / num_bins
    counts = [0] * num_bins
    edges = [min_v + i * bin_width for i in range(num_bins + 1)]
    for v in values:
        if min_v <= v <= max_v:
            idx = min(int((v - min_v) / bin_width), num_bins - 1)
            counts[idx] += 1
    return counts, edges


logger = logging.getLogger(__name__)


@dataclass
class LayoutRegion:
    """A detected region on the newspaper page."""
    x: float
    y: float
    width: float
    height: float
    region_type: str  # headline, body, image, caption, advertisement, sidebar
    confidence: float = 0.0
    text: str = ""
    font_size_estimate: float = 0.0
    column_index: int = -1


@dataclass
class ExtractedArticle:
    """An article extracted from layout analysis."""
    headline: str = ""
    body_text: str = ""
    full_text: str = ""
    bbox_x: float = 0
    bbox_y: float = 0
    bbox_width: float = 0
    bbox_height: float = 0
    bounding_boxes: List[dict] = field(default_factory=list)
    article_type: str = "news"
    is_advertisement: bool = False
    confidence: float = 0.0
    strategy: str = ""
    word_count: int = 0


def analyze_layout(
    ocr_boxes: List[dict],
    page_width: int,
    page_height: int,
    image: Any = None,
) -> List[ExtractedArticle]:
    """
    Main entry point for layout analysis.
    Tries multiple segmentation strategies and picks the best.
    """
    if not ocr_boxes:
        return []

    strategies = [
        ("column_first", _strategy_column_first),
        ("clustering", _strategy_clustering),
        ("text_density", _strategy_text_density),
    ]

    results = []
    for name, strategy_fn in strategies:
        try:
            articles = strategy_fn(ocr_boxes, page_width, page_height)
            score = _evaluate_segmentation(articles, len(ocr_boxes))
            results.append((name, articles, score))
            logger.info(f"Strategy '{name}': {len(articles)} articles, score={score:.1f}")
        except Exception as e:
            logger.warning(f"Strategy '{name}' failed: {e}")

    if not results:
        # Fallback: treat everything as one article
        return [_create_single_article(ocr_boxes)]

    # Select best strategy
    results.sort(key=lambda x: x[2], reverse=True)
    best_name, best_articles, best_score = results[0]

    # Tag with strategy
    for article in best_articles:
        article.strategy = best_name

    logger.info(f"Selected strategy: {best_name} ({len(best_articles)} articles, score={best_score:.1f})")
    return best_articles


def _strategy_column_first(
    ocr_boxes: List[dict], page_width: int, page_height: int
) -> List[ExtractedArticle]:
    """
    Strategy A: Detect columns first, then segment articles within each column.
    Works well for standard multi-column newspaper layouts.
    """
    # Detect columns using x-position gaps
    columns = _detect_columns(ocr_boxes, page_width)

    articles = []
    for col_idx, col_boxes in enumerate(columns):
        if not col_boxes:
            continue

        # Sort by y position within column
        col_boxes.sort(key=lambda b: b.get("y", 0))

        # Find headline candidates (larger font = larger height)
        avg_height = _mean([b.get("height", 10) for b in col_boxes])
        headline_threshold = avg_height * 1.4

        current_article = None

        for box in col_boxes:
            box_height = box.get("height", 0)
            text = box.get("text", "").strip()

            if not text:
                continue

            # New headline detected
            if box_height > headline_threshold and len(text) > 3:
                if current_article:
                    current_article.word_count = len(current_article.full_text.split())
                    articles.append(current_article)

                current_article = ExtractedArticle(
                    headline=text,
                    bbox_x=box.get("x", 0),
                    bbox_y=box.get("y", 0),
                    bbox_width=box.get("width", 0),
                    bbox_height=box.get("height", 0),
                    bounding_boxes=[box],
                )
            elif current_article:
                # Add to current article body
                current_article.body_text += " " + text
                current_article.bounding_boxes.append(box)
                # Expand bounding box
                _expand_bbox(current_article, box)
            else:
                # No headline yet, create article without headline
                current_article = ExtractedArticle(
                    body_text=text,
                    bbox_x=box.get("x", 0),
                    bbox_y=box.get("y", 0),
                    bbox_width=box.get("width", 0),
                    bbox_height=box.get("height", 0),
                    bounding_boxes=[box],
                )

        if current_article:
            current_article.full_text = (
                (current_article.headline + " " if current_article.headline else "") +
                current_article.body_text
            ).strip()
            current_article.word_count = len(current_article.full_text.split())
            articles.append(current_article)

    return articles


def _strategy_clustering(
    ocr_boxes: List[dict], page_width: int, page_height: int
) -> List[ExtractedArticle]:
    """
    Strategy B: Spatial clustering of OCR boxes using proximity.
    Groups nearby boxes into articles based on distance.
    """
    if not ocr_boxes:
        return []

    # Sort by position
    sorted_boxes = sorted(ocr_boxes, key=lambda b: (b.get("y", 0), b.get("x", 0)))

    # Group by proximity
    groups = []
    current_group = [sorted_boxes[0]]

    for i in range(1, len(sorted_boxes)):
        prev = sorted_boxes[i - 1]
        curr = sorted_boxes[i]

        # Calculate vertical gap
        prev_bottom = prev.get("y", 0) + prev.get("height", 0)
        curr_top = curr.get("y", 0)
        gap = curr_top - prev_bottom

        # Large gap = new article
        avg_height = _mean([b.get("height", 10) for b in current_group])
        threshold = avg_height * 3

        if gap > threshold:
            groups.append(current_group)
            current_group = [curr]
        else:
            current_group.append(curr)

    if current_group:
        groups.append(current_group)

    # Convert groups to articles
    articles = []
    for group in groups:
        if not group:
            continue

        texts = [b.get("text", "") for b in group]
        full_text = " ".join(t for t in texts if t.strip())

        if len(full_text.strip()) < 10:
            continue

        # Find headline (first large text)
        avg_h = _mean([b.get("height", 10) for b in group])
        headline = ""
        body_parts = []
        for b in group:
            if b.get("height", 0) > avg_h * 1.3 and not headline:
                headline = b.get("text", "")
            else:
                body_parts.append(b.get("text", ""))

        # Calculate bounding box
        min_x = min(b.get("x", 0) for b in group)
        min_y = min(b.get("y", 0) for b in group)
        max_x = max(b.get("x", 0) + b.get("width", 0) for b in group)
        max_y = max(b.get("y", 0) + b.get("height", 0) for b in group)

        articles.append(ExtractedArticle(
            headline=headline,
            body_text=" ".join(body_parts),
            full_text=full_text,
            bbox_x=min_x,
            bbox_y=min_y,
            bbox_width=max_x - min_x,
            bbox_height=max_y - min_y,
            bounding_boxes=group,
            word_count=len(full_text.split()),
            confidence=70.0,
        ))

    return articles


def _strategy_text_density(
    ocr_boxes: List[dict], page_width: int, page_height: int
) -> List[ExtractedArticle]:
    """
    Strategy C: Divide page into grid cells and group by text density.
    Works well for advertisement-heavy pages.
    """
    if not ocr_boxes:
        return []

    # Create grid
    cell_w = page_width / 4
    cell_h = page_height / 8

    grid = {}
    for box in ocr_boxes:
        cx = int(box.get("x", 0) / cell_w)
        cy = int(box.get("y", 0) / cell_h)
        key = (cx, cy)
        if key not in grid:
            grid[key] = []
        grid[key].append(box)

    # Group adjacent non-empty cells
    visited = set()
    groups = []

    for key in grid:
        if key in visited:
            continue
        group = []
        _flood_fill(grid, key, visited, group)
        if group:
            groups.append(group)

    # Convert to articles
    articles = []
    for group_boxes in groups:
        if not group_boxes:
            continue

        texts = [b.get("text", "") for b in group_boxes]
        full_text = " ".join(t for t in texts if t.strip())

        if len(full_text.strip()) < 10:
            continue

        min_x = min(b.get("x", 0) for b in group_boxes)
        min_y = min(b.get("y", 0) for b in group_boxes)
        max_x = max(b.get("x", 0) + b.get("width", 0) for b in group_boxes)
        max_y = max(b.get("y", 0) + b.get("height", 0) for b in group_boxes)

        articles.append(ExtractedArticle(
            body_text=full_text,
            full_text=full_text,
            bbox_x=min_x,
            bbox_y=min_y,
            bbox_width=max_x - min_x,
            bbox_height=max_y - min_y,
            bounding_boxes=group_boxes,
            word_count=len(full_text.split()),
            confidence=60.0,
        ))

    return articles


def _detect_columns(ocr_boxes: List[dict], page_width: int) -> List[List[dict]]:
    """Detect columns using x-position histogram gaps."""
    if not ocr_boxes:
        return [ocr_boxes]

    # Build x-position histogram
    x_centers = [b.get("x", 0) + b.get("width", 0) / 2 for b in ocr_boxes]

    if not x_centers:
        return [ocr_boxes]

    # Try to detect 1-4 columns
    counts, edges = _histogram_bins(x_centers, num_bins=20, val_range=(0, page_width))

    # Find significant gaps (low-density bins)
    threshold = _mean(counts) * 0.3
    gaps = []
    for i in range(len(counts)):
        if counts[i] <= threshold and i > 0 and i < len(counts) - 1:
            gap_center = (edges[i] + edges[i + 1]) / 2
            gaps.append(gap_center)

    if not gaps:
        return [ocr_boxes]

    # Merge nearby gaps
    merged_gaps = [gaps[0]]
    for g in gaps[1:]:
        if g - merged_gaps[-1] > page_width * 0.05:
            merged_gaps.append(g)

    # Split boxes into columns
    boundaries = [0] + merged_gaps + [page_width]
    columns = [[] for _ in range(len(boundaries) - 1)]

    for box in ocr_boxes:
        cx = box.get("x", 0) + box.get("width", 0) / 2
        for i in range(len(boundaries) - 1):
            if boundaries[i] <= cx <= boundaries[i + 1]:
                columns[i].append(box)
                break

    return [col for col in columns if col]


def _expand_bbox(article: ExtractedArticle, box: dict):
    """Expand article bounding box to include a new OCR box."""
    min_x = min(article.bbox_x, box.get("x", article.bbox_x))
    min_y = min(article.bbox_y, box.get("y", article.bbox_y))
    max_x = max(
        article.bbox_x + article.bbox_width,
        box.get("x", 0) + box.get("width", 0),
    )
    max_y = max(
        article.bbox_y + article.bbox_height,
        box.get("y", 0) + box.get("height", 0),
    )
    article.bbox_x = min_x
    article.bbox_y = min_y
    article.bbox_width = max_x - min_x
    article.bbox_height = max_y - min_y


def _flood_fill(grid: dict, key: tuple, visited: set, result: list):
    """Flood fill to group adjacent grid cells."""
    if key in visited or key not in grid:
        return
    visited.add(key)
    result.extend(grid[key])

    cx, cy = key
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        neighbor = (cx + dx, cy + dy)
        _flood_fill(grid, neighbor, visited, result)


def _evaluate_segmentation(articles: List[ExtractedArticle], total_boxes: int) -> float:
    """Evaluate segmentation quality."""
    if not articles:
        return 0.0

    score = 0.0

    # Reward: reasonable number of articles (2-15)
    n = len(articles)
    if 2 <= n <= 15:
        score += 30
    elif n == 1:
        score += 10
    else:
        score += max(0, 30 - abs(n - 8) * 2)

    # Reward: articles have both headlines and body
    for art in articles:
        if art.headline and art.body_text:
            score += 10 / max(n, 1)

    # Reward: good word distribution
    word_counts = [a.word_count for a in articles]
    if word_counts:
        avg = _mean(word_counts)
        std = _std(word_counts)
        cv = std / max(avg, 1)  # Coefficient of variation
        if cv < 2:
            score += 20
        else:
            score += max(0, 20 - cv * 5)

    # Penalize: very small articles
    tiny = sum(1 for a in articles if a.word_count < 5)
    score -= tiny * 5

    # Coverage: what fraction of boxes are in articles
    used_boxes = sum(len(a.bounding_boxes) for a in articles)
    coverage = used_boxes / max(total_boxes, 1)
    score += coverage * 20

    return max(0, min(100, score))


def _create_single_article(ocr_boxes: List[dict]) -> ExtractedArticle:
    """Fallback: create a single article from all OCR boxes."""
    texts = [b.get("text", "") for b in ocr_boxes]
    full_text = " ".join(t for t in texts if t.strip())

    min_x = min(b.get("x", 0) for b in ocr_boxes) if ocr_boxes else 0
    min_y = min(b.get("y", 0) for b in ocr_boxes) if ocr_boxes else 0
    max_x = max(b.get("x", 0) + b.get("width", 0) for b in ocr_boxes) if ocr_boxes else 0
    max_y = max(b.get("y", 0) + b.get("height", 0) for b in ocr_boxes) if ocr_boxes else 0

    return ExtractedArticle(
        body_text=full_text,
        full_text=full_text,
        bbox_x=min_x,
        bbox_y=min_y,
        bbox_width=max_x - min_x,
        bbox_height=max_y - min_y,
        bounding_boxes=ocr_boxes,
        word_count=len(full_text.split()),
        strategy="fallback_single",
        confidence=30.0,
    )
