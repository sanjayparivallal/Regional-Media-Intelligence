import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import async_session
from models.document import Document, Article
from models.intelligence import Mention
from sqlalchemy import select, func

async def check():
    async with async_session() as s:
        c1 = (await s.execute(select(func.count(Document.id)))).scalar()
        c2 = (await s.execute(select(func.count(Article.id)))).scalar()
        c3 = (await s.execute(select(func.count(Mention.id)))).scalar()
        print(f"Docs: {c1}, Articles: {c2}, Mentions: {c3}")

asyncio.run(check())
