"""
Master Data Seeder.

Seeds the database with brands and publications master data on first run.
No demo documents, articles, or alerts are created — all data comes from
real uploaded newspapers processed through the AI pipeline.
"""

import json
import logging
from pathlib import Path

from sqlalchemy import select
from database import async_session
from models.brand import Brand, BrandAlias
from models.publication import Publication

logger = logging.getLogger(__name__)

SEED_DIR = Path(__file__).parent


async def seed_demo_data():
    """Seed database with master brand and publication data if empty."""
    async with async_session() as db:
        # Only seed if no brands exist yet
        existing = (await db.execute(select(Brand))).scalars().first()
        if existing:
            logger.info("Master data already seeded, skipping")
            return

        logger.info("Seeding master brand and publication data...")

        # Seed brands
        brands_file = SEED_DIR / "brands.json"
        if brands_file.exists():
            brands_data = json.loads(brands_file.read_text())
            for bd in brands_data:
                brand = Brand(
                    name=bd["name"],
                    display_name=bd["display_name"],
                    industry=bd.get("industry"),
                    keywords=bd.get("keywords", []),
                )
                db.add(brand)
                await db.flush()

                for alias_text in bd.get("aliases", []):
                    alias = BrandAlias(brand_id=brand.id, alias=alias_text)
                    db.add(alias)

        # Seed publications
        pubs_file = SEED_DIR / "publications.json"
        if pubs_file.exists():
            pubs_data = json.loads(pubs_file.read_text())
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

        await db.commit()
        logger.info("Master data seeded successfully")
