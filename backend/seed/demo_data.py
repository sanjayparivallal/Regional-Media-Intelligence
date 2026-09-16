"""
Demo Data Seeder.

Seeds the database with brands, publications, and sample demo data
for a fully functional demo experience without real newspaper uploads.
"""

import json
import logging
import uuid
from pathlib import Path
from datetime import datetime, timedelta

from sqlalchemy import select
from database import async_session
from models.brand import Brand, BrandAlias
from models.publication import Publication
from models.document import Document, Page, Article, ProcessingJob, DocumentStatus, DocumentType
from models.intelligence import Alert, Mention, Translation, Entity, AlertPriority, SentimentLabel
from models.review import AuditLog

logger = logging.getLogger(__name__)

SEED_DIR = Path(__file__).parent


async def seed_demo_data():
    """Seed database with demo data."""
    async with async_session() as db:
        # Check if already seeded
        existing = (await db.execute(select(Brand))).scalars().first()
        if existing:
            logger.info("Database already seeded, skipping")
            return

        logger.info("Seeding demo data...")

        # Seed brands
        brands_data = json.loads((SEED_DIR / "brands.json").read_text())
        brand_map = {}
        for bd in brands_data:
            brand = Brand(
                name=bd["name"],
                display_name=bd["display_name"],
                industry=bd.get("industry"),
                keywords=bd.get("keywords", []),
            )
            db.add(brand)
            await db.flush()
            brand_map[bd["name"]] = brand

            for alias_text in bd.get("aliases", []):
                alias = BrandAlias(brand_id=brand.id, alias=alias_text)
                db.add(alias)

        # Seed publications
        pubs_data = json.loads((SEED_DIR / "publications.json").read_text())
        pub_map = {}
        for pd in pubs_data:
            pub = Publication(
                name=pd["name"],
                display_name=pd["display_name"],
                language=pd.get("language"),
                region=pd.get("region"),
                state=pd.get("state"),
                reach_tier=pd.get("reach_tier", 2),
                estimated_circulation=pd.get("estimated_circulation"),
                default_ocr_language=pd.get("default_ocr_language"),
                reach_score=1.0 / pd.get("reach_tier", 2),
            )
            db.add(pub)
            await db.flush()
            pub_map[pd["name"]] = pub

        # Create demo document
        pub = pub_map.get("Dainik Jagran")
        doc = Document(
            filename="demo_dainik_jagran.pdf",
            original_filename="Dainik_Jagran_2024_Sep_10.pdf",
            file_path="demo",
            file_size=2500000,
            mime_type="application/pdf",
            document_type=DocumentType.PDF_SCANNED,
            page_count=1,
            status=DocumentStatus.COMPLETED,
            publication_id=pub.id if pub else None,
            publication_date=datetime.utcnow() - timedelta(hours=2),
            source_region="North India",
            processing_started_at=datetime.utcnow() - timedelta(minutes=5),
            processing_completed_at=datetime.utcnow() - timedelta(minutes=3),
            processing_duration_ms=120000,
            is_demo=True,
        )
        db.add(doc)
        await db.flush()

        # Create demo page
        page = Page(
            document_id=doc.id,
            page_number=1,
            image_path="demo",
            thumbnail_path="demo",
            width=2480,
            height=3508,
            dpi=300,
            ocr_engine_used="demo",
            ocr_language="hi",
            ocr_confidence=92.5,
            ocr_word_count=156,
            detected_columns=3,
        )
        db.add(page)
        await db.flush()

        # Create demo article
        article = Article(
            page_id=page.id,
            document_id=doc.id,
            headline="PayU पर RBI की कार्रवाई: डिजिटल भुगतान कंपनी पर लगा प्रतिबंध",
            body_text="भारतीय रिजर्व बैंक ने PayU फाइनेंस पर नए ग्राहकों को जोड़ने पर रोक लगा दी है। RBI ने कहा कि कंपनी ने KYC नियमों का उल्लंघन किया है। PayU ने कहा कि वह RBI के निर्देशों का पालन करेगी।",
            full_text="PayU पर RBI की कार्रवाई: डिजिटल भुगतान कंपनी पर लगा प्रतिबंध भारतीय रिजर्व बैंक ने PayU फाइनेंस पर नए ग्राहकों को जोड़ने पर रोक लगा दी है।",
            word_count=42,
            bbox_x=50, bbox_y=80, bbox_width=900, bbox_height=280,
            detected_language="hi",
            language_confidence=98.5,
            detected_script="devanagari",
            ocr_confidence=92.5,
            segmentation_confidence=87.0,
            segmentation_strategy="column_first",
        )
        db.add(article)
        await db.flush()

        # Translation
        trans = Translation(
            article_id=article.id,
            source_language="hi",
            source_text=article.full_text,
            translated_text="RBI takes action against PayU: Ban imposed on digital payment company. The Reserve Bank of India has banned PayU Finance from onboarding new customers. RBI stated that the company violated KYC regulations. PayU said it will comply with RBI directives.",
            confidence=91.0,
            model_used="demo",
            entities_protected=["PayU", "RBI", "KYC"],
        )
        db.add(trans)

        # Entities
        for ent_data in [
            ("PayU", "ORGANIZATION", 0.95), ("RBI", "REGULATOR", 0.98),
            ("Reserve Bank of India", "REGULATOR", 0.97),
        ]:
            db.add(Entity(
                article_id=article.id, text=ent_data[0],
                entity_type=ent_data[1], confidence=ent_data[2],
                detected_in="translated", model_used="demo",
            ))

        # Brand mention + alert
        payu_brand = brand_map.get("PayU")
        if payu_brand:
            mention = Mention(
                article_id=article.id,
                brand_id=payu_brand.id,
                matched_text="PayU",
                match_type="exact",
                match_confidence=0.98,
                context_snippet="RBI takes action against PayU: Ban imposed on digital payment company",
                sentiment=SentimentLabel.NEGATIVE,
                sentiment_confidence=91.0,
                crisis_topic="regulatory_action",
                crisis_confidence=88.0,
                risk_score=91.0,
                risk_breakdown={
                    "sentiment": {"score": 28, "max": 30},
                    "brand": {"score": 24, "max": 25},
                    "topic": {"score": 18, "max": 20},
                    "reach": {"score": 13, "max": 15},
                    "confidence": {"score": 8, "max": 10},
                    "total": 91, "priority": "critical",
                },
                risk_priority=AlertPriority.CRITICAL,
            )
            db.add(mention)
            await db.flush()

            alert = Alert(
                article_id=article.id,
                mention_id=mention.id,
                brand_id=payu_brand.id,
                title="Regulatory Action: RBI takes action against PayU",
                summary="Critical regulatory action detected. RBI has banned PayU Finance from onboarding new customers due to KYC violations. Negative sentiment (91% confidence). Source: Dainik Jagran, page 1.",
                priority=AlertPriority.CRITICAL,
                risk_score=91.0,
                risk_breakdown=mention.risk_breakdown,
                publication_name="Dainik Jagran",
                page_number=1,
                language="hi",
                region="North India",
                sentiment=SentimentLabel.NEGATIVE,
                sentiment_confidence=91.0,
                crisis_topic="regulatory_action",
                crisis_keywords=["regulatory", "RBI", "ban", "KYC", "violation"],
                is_demo=True,
            )
            db.add(alert)

        # Audit trail
        for action_data in [
            ("document_uploaded", "upload", 0),
            ("pdf_classified", "pdf_classification", 1200),
            ("pages_rendered", "page_rendering", 3500),
            ("ocr_completed", "ocr", 15000),
            ("layout_analyzed", "layout_analysis", 2800),
            ("articles_extracted", "article_extraction", 1500),
            ("language_detected", "language_detection", 200),
            ("translation_completed", "translation", 8500),
            ("entities_extracted", "entity_detection", 1200),
            ("brands_matched", "brand_matching", 300),
            ("sentiment_analyzed", "sentiment_analysis", 2100),
            ("crisis_classified", "crisis_analysis", 800),
            ("risk_score_calculated", "risk_scoring", 100),
            ("alert_generated", "alert_generation", 50),
        ]:
            db.add(AuditLog(
                document_id=doc.id,
                article_id=article.id if action_data[1] != "upload" else None,
                action=action_data[0],
                stage=action_data[1],
                processing_time_ms=action_data[2],
                success=True,
                model_used="demo",
            ))

        await db.commit()
        logger.info("Demo data seeded successfully")
