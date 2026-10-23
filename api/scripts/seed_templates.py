"""Seed the two default templates into the templates table.

Idempotent: un template déjà présent (même nom) n'est pas dupliqué.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models import Template


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        for name, kind in (("Offre emploi", "emploi"), ("Offre stage", "stage")):
            existing = await db.execute(
                select(Template).where(Template.name == name)
            )
            if existing.scalar_one_or_none() is not None:
                continue
            db.add(
                Template(
                    name=name,
                    kind=kind,
                    html="<div>{{ title }}</div>",
                    markup="{{ title }}",
                    format="jinja2",
                    version=1,
                    active=True,
                )
            )
        await db.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
