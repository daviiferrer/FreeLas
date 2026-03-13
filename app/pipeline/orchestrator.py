import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import event_bus
from app.database import async_session
from app.models.project import Project, ProjectStatus
from app.scraper.service import ScraperService
from app.ai.scanner import run_scanner
from app.ai.analyst import run_analyst
from app.ai.strategist import run_strategist
from app.services.waha import waha_client

logger = logging.getLogger("freelaas.pipeline")


class PipelineOrchestrator:
    def __init__(self):
        self.scraper = ScraperService()
        self._running = False

    async def run_full_cycle(self):
        """Execute complete pipeline project-by-project for maximum responsiveness."""
        if self._running:
            logger.warning("Pipeline already running, skipping cycle")
            return

        self._running = True
        try:
            await event_bus.publish("pipeline_start", {
                "message": "🚀 Pipeline iniciado — varredura em tempo real"
            })

            async with async_session() as db:
                # Use the new streaming scraper
                async for project in self.scraper.run_cycle_stream(db):
                    logger.info(f"Processing new project through AI: {project.project_id}")
                    await self._process_single_project(db, project)

                # Get final stats
                stats = await self._get_stats(db)
                await event_bus.publish("pipeline_complete", {
                    "stats": stats,
                    "message": f"🏁 Ciclo completo! {stats.get('total', 0)} projetos totais"
                })

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            await event_bus.publish("pipeline_error", {
                "message": f"❌ Erro no pipeline: {str(e)[:200]}"
            })
        finally:
            self._running = False

    async def _process_single_project(self, db: AsyncSession, project: Project):
        """Run all AI phases for a single project and send notification if passed."""
        try:
            # Phase 1: Scanner
            scanner_result = await run_scanner(project.to_dict())
            if not scanner_result:
                return

            project.ai_score_phase1 = scanner_result.get("score", 0)
            project.ai_reason_phase1 = scanner_result.get("reason", "")

            if scanner_result.get("decision") != "phase2":
                logger.info(f"🚫 Project {project.project_id} REJECTED by Scanner. Reason: {scanner_result.get('reason', 'N/A')}")
                project.status = ProjectStatus.rejected
                await db.commit()
                return

            project.status = ProjectStatus.phase1_pass
            await db.commit()

            # Phase 2: Analyst
            analyst_result = await run_analyst(project.to_dict())
            if not analyst_result:
                return

            project.ai_score_phase2 = analyst_result.get("score", 0)
            # Combine problem identification and archetype for a full analysis view
            project.ai_analysis = f"Problema: {analyst_result.get('problem_identified', 'N/A')} | Arquétipo: {analyst_result.get('client_archetype', 'N/A')}"
            project.ai_complexity = analyst_result.get("complexity", "")
            # Clear effort as it's not in the new prompt
            project.ai_estimated_effort = ""

            if analyst_result.get("decision") != "phase3":
                logger.info(f"🚫 Project {project.project_id} REJECTED by Analyst. Archetype: {analyst_result.get('client_archetype', 'N/A')}")
                project.status = ProjectStatus.rejected
                await db.commit()
                return

            project.status = ProjectStatus.phase2_pass
            await db.commit()

            # PHASE 3: STRATEGIST
            project_data = project.to_dict()
            
            strategist_result = await run_strategist(
                project=project_data,
                analyst_data=analyst_result,
                scanner_data=scanner_result
            )
            
            if not strategist_result:
                return
            
            # Map strategist fields to DB project
            project.ai_action = strategist_result.get("action", "SEND_PROPOSAL")
            project.ai_summary = strategist_result.get("summary_for_davi", "")
            project.ai_analysis = (
                f"Problema: {analyst_result.get('problem_identified', 'N/A')} | "
                f"Arquétipo: {analyst_result.get('client_archetype', 'N/A')} | "
                f"Justificativa: {strategist_result.get('hunting_justification', 'N/A')}"
            )
            project.proposal_text = strategist_result.get("proposal_text", "")
            project.ai_question = strategist_result.get("question_text", "")
            project.recommended_price = str(strategist_result.get("recommended_price", ""))
            project.recommended_delivery_time = str(strategist_result.get("recommended_delivery_time", ""))
            
            project.status = ProjectStatus.pending_approval
            
            db.add(project)
            await db.commit()
            
            # Prepare data for WAHA notification
            # Keys must match what waha.py reads
            project_dict = {
                "title": project.title,
                "url": project.url,
                "category": project.category,
                "experience_level": project.experience_level,
                "client_rating": project.client_rating,
                "proposals_count": project.proposals_count,
                "ai_score_phase1": project.ai_score_phase1,
                "ai_score_phase2": project.ai_score_phase2,
                "ai_complexity": project.ai_complexity,
                "ai_action": project.ai_action,
                "ai_reason": strategist_result.get("hunting_justification", ""),
                "ai_summary": project.ai_summary,
                "strategy": strategist_result.get("strategy", ""),
                "proposal_text": project.proposal_text,
                "ai_question": project.ai_question,
                "recommended_price": project.recommended_price,
                "recommended_delivery_time": project.recommended_delivery_time,
            }

            # Trigger WAHA notification using the prepared dict
            msg_id = await waha_client.send_approval_request(project_dict)
            if msg_id:
                project.waha_message_id = msg_id
                await db.commit()
                logger.info(f"Notification sent for project {project.project_id}")

        except Exception as e:
            logger.error(f"Error processing project {project.project_id}: {e}")
            project.status = ProjectStatus.rejected # Fail closed
            await db.commit()

    async def _get_stats(self, db: AsyncSession) -> dict:
        stats = {}
        for status in ProjectStatus:
            result = await db.execute(
                select(func.count(Project.project_id)).where(Project.status == status)
            )
            stats[status.value] = result.scalar() or 0

        total = await db.execute(select(func.count(Project.project_id)))
        stats["total"] = total.scalar() or 0
        return stats
