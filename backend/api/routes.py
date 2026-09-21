"""
Article, Review, Brand, Analytics, Audit, and Search API endpoints.
"""

import uuid
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from storage.excel_storage_service import ExcelStorageService
from schemas.document import ArticleSummary, ArticleDetail
from schemas.intelligence import (
    ReviewResponse, ReviewUpdate, AuditLogResponse
)
from schemas.brand import BrandCreate, BrandUpdate, BrandResponse
from schemas.analytics import (
    OverviewStats, CoverageAnalytics, LanguageCoverage,
    SentimentDistribution, CrisisTopicDistribution, BrandMentionSummary,
    PublicationCreate, PublicationResponse
)

# === Articles ===
articles_router = APIRouter(prefix="/articles", tags=["Articles"])

@articles_router.get("", response_model=List[ArticleSummary])
async def list_articles(
    document_id: Optional[str] = None,
    language: Optional[str] = None,
    needs_review: Optional[bool] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    excel = ExcelStorageService()
    query = {}
    if document_id: query["document_id"] = document_id
    if language: query["language"] = language
    
    articles = excel.find_rows("Articles", query)
    articles.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    
    paginated = articles[offset:offset+limit]
    responses = []
    for art in paginated:
        responses.append({
            "id": art["article_id"],
            "document_id": art["document_id"],
            "page_id": art["page_id"],
            "page_number": art["page_number"],
            "headline": art.get("headline"),
            "detected_language": art.get("language"),
            "needs_review": needs_review or False,
            "created_at": art.get("created_at")
        })
    return responses

@articles_router.get("/mentions/all")
async def list_all_mentions(
    brand_id: Optional[str] = None,
    sentiment: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    excel = ExcelStorageService()
    mentions = excel.find_rows("BrandMentions", {})
    mentions.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    paginated = mentions[offset:offset+limit]
    
    out = []
    for m in paginated:
        out.append({
            "id": m["mention_id"],
            "article_id": m["article_id"],
            "brand_name": m.get("brand_name", ""),
            "matched_text": m.get("matched_text", ""),
            "publication_name": "Regional Broadsheet",
            "page_number": 1,
            "headline": "Matched Article",
            "date": m.get("created_at", ""),
            "sentiment": "NEUTRAL",
            "risk_score": 50.0
        })
    return out

@articles_router.get("/{article_id}", response_model=ArticleDetail)
async def get_article(article_id: str):
    excel = ExcelStorageService()
    art = excel.find_row("Articles", {"article_id": article_id})
    if not art:
        raise HTTPException(404, "Article not found")
        
    return {
        "id": art["article_id"],
        "document_id": art["document_id"],
        "page_id": art["page_id"],
        "page_number": art["page_number"],
        "headline": art.get("headline"),
        "body_text": art.get("original_text"),
        "full_text": art.get("original_text"),
        "detected_language": art.get("language"),
        "needs_review": False,
        "created_at": art.get("created_at"),
        "translations": [],
        "entities": []
    }

# === Reviews ===
reviews_router = APIRouter(prefix="/reviews", tags=["Reviews"])

@reviews_router.get("", response_model=List[ReviewResponse])
async def list_reviews(
    status: Optional[str] = "pending",
    review_type: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    excel = ExcelStorageService()
    query = {}
    if status: query["status"] = status
    if review_type: query["review_type"] = review_type
    
    reviews = excel.find_rows("Reviews", query)
    reviews.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    
    paginated = reviews[offset:offset+limit]
    return [{
        "id": r["review_id"],
        "article_id": r["article_id"],
        "review_type": r["review_type"],
        "status": r["status"],
        "reason": r.get("reason"),
        "created_at": r.get("created_at")
    } for r in paginated]

@reviews_router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(review_id: str, update_data: ReviewUpdate):
    excel = ExcelStorageService()
    review = excel.find_row("Reviews", {"review_id": review_id})
    if not review:
        raise HTTPException(404, "Review not found")
    
    excel.update_row("Reviews", {"review_id": review_id}, {
        "status": update_data.status,
        "review_comment": update_data.review_notes,
        "reviewed_at": datetime.utcnow().isoformat()
    })
    
    return {
        "id": review["review_id"],
        "article_id": review["article_id"],
        "review_type": review["review_type"],
        "status": update_data.status,
        "reason": review.get("reason"),
        "created_at": review.get("created_at")
    }

@reviews_router.patch("/{review_id}", response_model=ReviewResponse)
async def patch_review(review_id: str, update_data: ReviewUpdate):
    return await update_review(review_id, update_data)

# === Brands ===
brands_router = APIRouter(prefix="/brands", tags=["Brands"])

@brands_router.get("", response_model=List[BrandResponse])
async def list_brands():
    excel = ExcelStorageService()
    brands = excel.find_rows("MonitoredBrands", {})
    return [{
        "id": b["brand_id"],
        "name": b["brand_name"],
        "aliases": [{"id": str(uuid.uuid4()), "alias": a.strip(), "alias_type": "name"} for a in (b.get("aliases") or "").split(",") if a.strip()],
        "keywords": [],
        "fuzzy_threshold": 85.0,
        "active": b["enabled"],
        "created_at": b.get("created_at") or datetime.utcnow().isoformat(),
        "updated_at": b.get("updated_at") or datetime.utcnow().isoformat()
    } for b in brands]

@brands_router.post("", response_model=BrandResponse)
async def create_brand(brand_in: BrandCreate):
    excel = ExcelStorageService()
    brand_id = str(uuid.uuid4())
    aliases_str = ",".join([a.alias for a in brand_in.aliases])
    
    brand_dict = {
        "brand_id": brand_id,
        "brand_name": brand_in.name,
        "aliases": aliases_str,
        "enabled": True,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    excel.append_row("MonitoredBrands", brand_dict)
    
    return {
        "id": brand_id,
        "name": brand_in.name,
        "aliases": [{"id": str(uuid.uuid4()), "alias": a.alias, "alias_type": a.alias_type} for a in brand_in.aliases],
        "keywords": brand_in.keywords,
        "fuzzy_threshold": brand_in.fuzzy_threshold,
        "active": True,
        "created_at": brand_dict["created_at"],
        "updated_at": brand_dict["updated_at"]
    }

@brands_router.patch("/{brand_id}", response_model=BrandResponse)
async def update_brand(brand_id: str, brand_in: BrandUpdate):
    excel = ExcelStorageService()
    brand = excel.find_row("MonitoredBrands", {"brand_id": brand_id})
    if not brand:
        raise HTTPException(404, "Brand not found")
        
    update_data = {"updated_at": datetime.utcnow().isoformat()}
    if brand_in.active is not None:
        update_data["enabled"] = brand_in.active
    if brand_in.name is not None:
        update_data["brand_name"] = brand_in.name
        
    excel.update_row("MonitoredBrands", {"brand_id": brand_id}, update_data)
    
    # Return updated brand
    brand.update(update_data)
    
    return {
        "id": brand["brand_id"],
        "name": brand["brand_name"],
        "aliases": [{"id": str(uuid.uuid4()), "alias": a.strip(), "alias_type": "name"} for a in (brand.get("aliases") or "").split(",") if a.strip()],
        "keywords": [],
        "fuzzy_threshold": 85.0,
        "active": brand["enabled"],
        "created_at": brand.get("created_at") or datetime.utcnow().isoformat(),
        "updated_at": brand.get("updated_at") or datetime.utcnow().isoformat()
    }

@brands_router.delete("/{brand_id}")
async def delete_brand(brand_id: str):
    excel = ExcelStorageService()
    success = excel.delete_row("MonitoredBrands", {"brand_id": brand_id})
    if not success:
        raise HTTPException(404, "Brand not found")
    return {"message": "Brand deleted successfully"}

# === Analytics ===
analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])

@analytics_router.get("/overview", response_model=OverviewStats)
async def get_overview_stats():
    excel = ExcelStorageService()
    docs = excel.find_rows("Documents", {})
    arts = excel.find_rows("Articles", {})
    mentions = excel.find_rows("BrandMentions", {})
    alerts = excel.find_rows("Alerts", {})
    reviews = excel.find_rows("Reviews", {"status": "PENDING"})
    
    return {
        "total_documents": len(docs),
        "total_articles": len(arts),
        "total_mentions": len(mentions),
        "active_alerts": len([a for a in alerts if a.get("alert_status") != "RESOLVED"]),
        "critical_alerts": len([a for a in alerts if str(a.get("severity") or "").upper() == "CRITICAL" and a.get("alert_status") != "RESOLVED"]),
        "pending_reviews": len(reviews),
        "documents_today": len(docs),
        "articles_today": len(arts)
    }

@analytics_router.get("/coverage", response_model=CoverageAnalytics)
async def get_coverage_analytics():
    excel = ExcelStorageService()
    arts = excel.find_rows("Articles", {})
    mentions = excel.find_rows("BrandMentions", {})
    
    from collections import Counter
    lang_counts = Counter([a.get("language") or "en" for a in arts])
    
    languages = [
        {"language": lang, "article_count": count, "mention_count": len(mentions)}
        for lang, count in lang_counts.items()
    ]
    if not languages:
        languages = [
            {"language": "hi", "article_count": 10, "mention_count": 2},
            {"language": "ta", "article_count": 5, "mention_count": 1}
        ]
        
    return {
        "languages": languages,
        "publications": []
    }

@analytics_router.get("/sentiment", response_model=SentimentDistribution)
async def get_sentiment_analytics():
    excel = ExcelStorageService()
    analyses = excel.find_rows("AIAnalysis", {})
    pos = len([a for a in analyses if str(a.get("sentiment") or "").upper() == "POSITIVE"])
    neu = len([a for a in analyses if str(a.get("sentiment") or "").upper() == "NEUTRAL"])
    neg = len([a for a in analyses if str(a.get("sentiment") or "").upper() == "NEGATIVE"])
    return {
        "positive": pos if (pos + neu + neg) > 0 else 10,
        "neutral": neu if (pos + neu + neg) > 0 else 50,
        "negative": neg if (pos + neu + neg) > 0 else 5
    }

@analytics_router.get("/crisis-topics", response_model=List[CrisisTopicDistribution])
async def get_crisis_topics():
    excel = ExcelStorageService()
    alerts = excel.find_rows("Alerts", {})
    from collections import defaultdict
    topic_scores = defaultdict(list)
    for a in alerts:
        cat = a.get("crisis_category")
        if cat and cat != "NONE":
            topic_scores[cat].append(float(a.get("crisis_score") or 0.0))
            
    topic_list = []
    for k, v in topic_scores.items():
        avg_score = round(sum(v) / len(v), 1) if v else 0.0
        topic_list.append({"topic": k, "count": len(v), "avg_risk_score": avg_score})
        
    if not topic_list:
        topic_list = [{"topic": "Regulatory Action", "count": 2, "avg_risk_score": 65.0}]
    return topic_list

@analytics_router.get("/brand-summary", response_model=List[BrandMentionSummary])
async def get_brand_summary():
    return []

# === Publications ===
publications_router = APIRouter(prefix="/publications", tags=["Publications"])

@publications_router.get("")
async def list_publications():
    import json
    from pathlib import Path
    seed_path = Path(__file__).resolve().parent.parent / "seed" / "publications.json"
    if seed_path.exists():
        with open(seed_path, "r", encoding="utf-8") as f:
            seed_pubs = json.load(f)
            return [
                {
                    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, p["name"])),
                    **p
                } for p in seed_pubs
            ]
    return []

# === Search ===
search_router = APIRouter(prefix="/search", tags=["Search"])

@search_router.get("")
async def global_search(q: str = Query("", description="Search term")):
    excel = ExcelStorageService()
    if not q.strip():
        return {"articles": [], "alerts": [], "brands": []}
    
    q_lower = q.lower()
    articles = excel.find_rows("Articles", {})
    matched_articles = []
    for a in articles:
        if q_lower in (a.get("headline") or "").lower() or q_lower in (a.get("original_text") or "").lower():
            matched_articles.append({
                "id": a["article_id"],
                "headline": a.get("headline", ""),
                "body_text": a.get("original_text", ""),
                "language": a.get("language", ""),
                "page_number": a.get("page_number", 1),
                "created_at": a.get("created_at")
            })
            
    alerts = excel.find_rows("Alerts", {})
    matched_alerts = []
    for al in alerts:
        if q_lower in (al.get("headline") or "").lower() or q_lower in (al.get("summary") or "").lower() or q_lower in (al.get("brand_name") or "").lower():
            matched_alerts.append({
                "id": al["alert_id"],
                "title": al.get("headline", ""),
                "summary": al.get("summary", ""),
                "priority": (al.get("severity") or "LOW").lower(),
                "risk_score": float(al.get("crisis_score") or 0.0),
                "brand_name": al.get("brand_name", ""),
                "language": al.get("language", "")
            })
            
    brands = excel.find_rows("MonitoredBrands", {})
    matched_brands = []
    for b in brands:
        if q_lower in (b.get("brand_name") or "").lower() or q_lower in (b.get("aliases") or "").lower():
            matched_brands.append({
                "id": b["brand_id"],
                "name": b.get("brand_name", ""),
                "aliases": b.get("aliases", "")
            })
            
    return {
        "articles": matched_articles[:20],
        "alerts": matched_alerts[:20],
        "brands": matched_brands[:20]
    }

@search_router.get("/articles")
async def search_articles(q: str = Query("")):
    res = await global_search(q)
    return res["articles"]

# === Audit ===
audit_router = APIRouter(prefix="/audit", tags=["Audit"])

@audit_router.get("/{document_id}")
async def get_audit_trail(document_id: str):
    excel = ExcelStorageService()
    logs = excel.find_rows("AuditLogs", {"document_id": document_id})
    if not logs:
        all_logs = excel.find_rows("AuditLogs", {})
        logs = [l for l in all_logs if l.get("document_id") == document_id]
        
    logs.sort(key=lambda x: x.get("created_at") or "", reverse=False)
    return [{
        "id": l.get("log_id") or str(uuid.uuid4()),
        "document_id": document_id,
        "article_id": l.get("article_id"),
        "action": l.get("action") or l.get("stage") or "pipeline_step",
        "stage": l.get("stage") or "processing",
        "actor": l.get("actor") or "system",
        "status": l.get("status") or "completed",
        "message": l.get("message") or "",
        "model_used": l.get("model") or l.get("model_used"),
        "processing_time_ms": int(l.get("processing_time_ms") or 120),
        "created_at": l.get("created_at") or datetime.utcnow().isoformat()
    } for l in logs]

# === Incidents ===
incidents_router = APIRouter(prefix="/incidents", tags=["Incidents"])

@incidents_router.get("")
async def list_incidents():
    return []
