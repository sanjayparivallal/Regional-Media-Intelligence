"""
Article, Review, Brand, Analytics, Audit, and Search API endpoints.
"""

import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, update
from sqlalchemy.orm import selectinload

from database import get_db
from models.document import Document, Page, Article, DocumentStatus
from models.intelligence import Alert, Mention, Translation, Entity, Incident, AlertPriority, SentimentLabel
from models.brand import Brand, BrandAlias
from models.review import Review, AuditLog
from models.publication import Publication
from schemas.document import ArticleSummary, ArticleDetail
from schemas.intelligence import (
    AlertResponse, ReviewResponse, ReviewUpdate, IncidentResponse, AuditLogResponse
)
from schemas.brand import BrandCreate, BrandUpdate, BrandResponse
from schemas.analytics import (
    OverviewStats, CoverageAnalytics, LanguageCoverage,
    SentimentDistribution, CrisisTopicDistribution, BrandMentionSummary,
    PublicationCreate, PublicationResponse
)

# === Articles ===
articles_router = APIRouter(prefix="/articles", tags=["Articles"])


@articles_router.get("", response_model=list[ArticleSummary])
async def list_articles(
    document_id: Optional[uuid.UUID] = None,
    language: Optional[str] = None,
    needs_review: Optional[bool] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Article).order_by(desc(Article.created_at))
    if document_id:
        query = query.where(Article.document_id == document_id)
    if language:
        query = query.where(Article.detected_language == language)
    if needs_review is not None:
        query = query.where(Article.needs_review == needs_review)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    articles = result.scalars().all()
    responses = []
    for art in articles:
        resp = ArticleSummary.model_validate(art)
        # Get page number
        page_result = await db.execute(select(Page.page_number).where(Page.id == art.page_id))
        pn = page_result.scalar_one_or_none()
        resp.page_number = pn or 0
        responses.append(resp)
    return responses


@articles_router.get("/{article_id}", response_model=ArticleDetail)
async def get_article(article_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Article)
        .options(
            selectinload(Article.translations),
            selectinload(Article.entities),
            selectinload(Article.mentions),
        )
        .where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article not found")
    return article


# === Reviews ===
reviews_router = APIRouter(prefix="/reviews", tags=["Reviews"])


@reviews_router.get("", response_model=list[ReviewResponse])
async def list_reviews(
    status: Optional[str] = None,
    review_type: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Review).order_by(desc(Review.created_at))
    if status:
        query = query.where(Review.status == status)
    if review_type:
        query = query.where(Review.review_type == review_type)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@reviews_router.patch("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: uuid.UUID,
    data: ReviewUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(404, "Review not found")

    review.status = data.status
    review.reviewer = data.reviewer or "analyst"
    review.correction = data.correction
    review.review_notes = data.review_notes
    review.reviewed_at = datetime.utcnow()

    # Log the review action
    audit = AuditLog(
        article_id=review.article_id,
        alert_id=review.alert_id,
        action=f"review_{data.status}",
        stage="human_review",
        actor=review.reviewer,
        details={"review_id": str(review_id), "notes": data.review_notes},
    )
    db.add(audit)
    await db.flush()
    await db.refresh(review)
    await db.commit()
    return review


# === Brands ===
brands_router = APIRouter(prefix="/brands", tags=["Brands"])


@brands_router.get("", response_model=list[BrandResponse])
async def list_brands(
    active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Brand).options(selectinload(Brand.aliases)).order_by(Brand.name)
    if active is not None:
        query = query.where(Brand.active == active)
    result = await db.execute(query)
    return result.scalars().all()


@brands_router.post("", response_model=BrandResponse)
async def create_brand(data: BrandCreate, db: AsyncSession = Depends(get_db)):
    brand = Brand(
        name=data.name,
        display_name=data.display_name or data.name,
        industry=data.industry,
        description=data.description,
        keywords=data.keywords,
        fuzzy_threshold=data.fuzzy_threshold,
    )
    db.add(brand)
    await db.flush()

    for alias_data in data.aliases:
        alias = BrandAlias(brand_id=brand.id, alias=alias_data.alias, alias_type=alias_data.alias_type)
        db.add(alias)

    await db.flush()
    await db.refresh(brand)
    await db.commit()

    # Reload with aliases
    result = await db.execute(
        select(Brand).options(selectinload(Brand.aliases)).where(Brand.id == brand.id)
    )
    return result.scalar_one()


@brands_router.patch("/{brand_id}", response_model=BrandResponse)
async def update_brand(brand_id: uuid.UUID, data: BrandUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(404, "Brand not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(brand, field, value)

    await db.flush()
    await db.refresh(brand)
    await db.commit()
    return brand


@brands_router.delete("/{brand_id}")
async def delete_brand(brand_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(404, "Brand not found")
    await db.delete(brand)
    await db.commit()
    return {"status": "deleted"}


# === Analytics ===
analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])


@analytics_router.get("/overview", response_model=OverviewStats)
async def get_overview(db: AsyncSession = Depends(get_db)):
    docs = (await db.execute(select(func.count()).select_from(Document).where(Document.status == DocumentStatus.COMPLETED))).scalar() or 0
    pages = (await db.execute(select(func.count()).select_from(Page))).scalar() or 0
    articles = (await db.execute(select(func.count()).select_from(Article))).scalar() or 0
    mentions_count = (await db.execute(select(func.count()).select_from(Mention))).scalar() or 0
    critical = (await db.execute(select(func.count()).select_from(Alert).where(Alert.priority == AlertPriority.CRITICAL))).scalar() or 0
    high = (await db.execute(select(func.count()).select_from(Alert).where(Alert.priority == AlertPriority.HIGH))).scalar() or 0
    pending = (await db.execute(select(func.count()).select_from(Review).where(Review.status == "pending"))).scalar() or 0
    brands_active = (await db.execute(select(func.count()).select_from(Brand).where(Brand.active == True))).scalar() or 0

    return OverviewStats(
        documents_processed=docs,
        pages_processed=pages,
        articles_detected=articles,
        brand_mentions=mentions_count,
        critical_alerts=critical,
        high_alerts=high,
        pending_reviews=pending,
        active_brands=brands_active,
    )


@analytics_router.get("/coverage", response_model=CoverageAnalytics)
async def get_coverage(db: AsyncSession = Depends(get_db)):
    # Language coverage
    lang_result = await db.execute(
        select(Article.detected_language, func.count().label("cnt"))
        .where(Article.detected_language.isnot(None))
        .group_by(Article.detected_language)
    )
    total_articles = (await db.execute(select(func.count()).select_from(Article))).scalar() or 1
    lang_coverage = [
        LanguageCoverage(
            language=row[0] or "unknown",
            count=row[1],
            percentage=round(row[1] / total_articles * 100, 1),
        )
        for row in lang_result.all()
    ]

    # Sentiment distribution
    pos = (await db.execute(select(func.count()).select_from(Mention).where(Mention.sentiment == SentimentLabel.POSITIVE))).scalar() or 0
    neu = (await db.execute(select(func.count()).select_from(Mention).where(Mention.sentiment == SentimentLabel.NEUTRAL))).scalar() or 0
    neg = (await db.execute(select(func.count()).select_from(Mention).where(Mention.sentiment == SentimentLabel.NEGATIVE))).scalar() or 0

    return CoverageAnalytics(
        language_coverage=lang_coverage,
        sentiment_distribution=SentimentDistribution(positive=pos, neutral=neu, negative=neg),
    )


# === Audit ===
audit_router = APIRouter(prefix="/audit", tags=["Audit"])


@audit_router.get("/{document_id}", response_model=list[AuditLogResponse])
async def get_audit_trail(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.document_id == document_id)
        .order_by(AuditLog.created_at)
    )
    return result.scalars().all()


# === Search ===
search_router = APIRouter(prefix="/search", tags=["Search"])


@search_router.get("")
async def global_search(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_db),
):
    results = {"articles": [], "alerts": [], "brands": [], "documents": []}

    # Search articles
    art_result = await db.execute(
        select(Article)
        .where(
            Article.headline.ilike(f"%{q}%") |
            Article.body_text.ilike(f"%{q}%")
        )
        .limit(10)
    )
    results["articles"] = [
        {"id": str(a.id), "headline": a.headline, "type": "article"}
        for a in art_result.scalars().all()
    ]

    # Search brands
    brand_result = await db.execute(
        select(Brand).where(Brand.name.ilike(f"%{q}%")).limit(10)
    )
    results["brands"] = [
        {"id": str(b.id), "name": b.name, "type": "brand"}
        for b in brand_result.scalars().all()
    ]

    # Search alerts
    alert_result = await db.execute(
        select(Alert).where(Alert.title.ilike(f"%{q}%")).limit(10)
    )
    results["alerts"] = [
        {"id": str(a.id), "title": a.title, "type": "alert", "priority": a.priority.value if a.priority else None}
        for a in alert_result.scalars().all()
    ]

    return results


# === Publications ===
publications_router = APIRouter(prefix="/publications", tags=["Publications"])


@publications_router.get("", response_model=list[PublicationResponse])
async def list_publications(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Publication).order_by(Publication.name))
    return result.scalars().all()


@publications_router.post("", response_model=PublicationResponse)
async def create_publication(data: PublicationCreate, db: AsyncSession = Depends(get_db)):
    pub = Publication(
        name=data.name,
        display_name=data.display_name or data.name,
        language=data.language,
        region=data.region,
        state=data.state,
        reach_tier=data.reach_tier,
        estimated_circulation=data.estimated_circulation,
        default_ocr_language=data.default_ocr_language,
    )
    db.add(pub)
    await db.flush()
    await db.refresh(pub)
    await db.commit()
    return pub
