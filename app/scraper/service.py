import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings, event_bus
from app.models.project import Project, ProjectStatus
from app.scraper.client import fetch_page
from app.scraper.parser import parse_projects

logger = logging.getLogger("freelaas.scraper")


class ScraperService:
    async def run_cycle_stream(self, db: AsyncSession):
        """Run scraping cycle as a stream, yielding only new projects."""
        await event_bus.publish("scraper_start", {"message": "🔍 Iniciando varredura no 99Freelas..."})

        for page in range(1, settings.SCRAPE_MAX_PAGES + 1):
            await event_bus.publish("scraper_page", {"page": page, "total": settings.SCRAPE_MAX_PAGES})
            logger.info(f"Fetching page {page}/{settings.SCRAPE_MAX_PAGES}")

            html = await fetch_page(page)
            if not html:
                await event_bus.publish("scraper_error", {
                    "page": page,
                    "message": f"⚠️ Falha ao buscar página {page}"
                })
                continue

            parsed = parse_projects(html)
            
            # Apply time filter
            now = datetime.now()
            cutoff = now - timedelta(minutes=settings.TIME_FILTER_MINUTES)
            
            page_new_projects = []
            for p in parsed:
                try:
                    p_time = datetime.fromisoformat(p["published_time"])
                    if p_time.tzinfo is None:
                        p_time = p_time.replace(tzinfo=timezone.utc)
                    if p_time < cutoff:
                        continue
                except (ValueError, TypeError):
                    pass # Keep if time parsing fails
                
                # Check if exists in DB
                result = await db.execute(
                    select(Project.project_id).where(Project.project_id == p["project_id"])
                )
                if not result.scalar():
                    page_new_projects.append(p)

            for p_data in page_new_projects:
                # Force naive UTC for scraped_at to avoid asyncpg error
                scraped_at_naive = datetime.now()
                
                project = Project(
                    project_id=p_data["project_id"],
                    title=p_data["title"],
                    description=p_data["description"],
                    category=p_data["category"],
                    experience_level=p_data["experience_level"],
                    client_name=p_data["client_name"],
                    client_rating=p_data["client_rating"],
                    proposals_count=p_data["proposals_count"],
                    interested_count=p_data["interested_count"],
                    published_time=p_data["published_time"],
                    url=p_data["url"],
                    scraped_at=scraped_at_naive,
                    status=ProjectStatus.new,
                )
                db.add(project)
                await db.commit() # Commit immediately so AI can see it if needed
                
                yield project

                await event_bus.publish("project_found", {
                    "project_id": p_data["project_id"],
                    "title": p_data["title"],
                    "category": p_data["category"],
                    "client_name": p_data["client_name"],
                    "message": f"🆕 Novo projeto: {p_data['title'][:80]}"
                })

            await event_bus.publish("scraper_parsed", {
                "page": page,
                "count": len(parsed),
                "new": len(page_new_projects),
                "message": f"📄 Página {page}: {len(parsed)} projetos ({len(page_new_projects)} novos)"
            })

            if page < settings.SCRAPE_MAX_PAGES:
                delay = random.uniform(settings.SCRAPE_DELAY_MIN, settings.SCRAPE_DELAY_MAX)
                await event_bus.publish("scraper_delay", {
                    "seconds": round(delay, 1),
                    "message": f"⏳ Aguardando {round(delay, 1)}s..."
                })
                await asyncio.sleep(delay)

        await event_bus.publish("scraper_complete", {"message": "✅ Varredura concluída"})
