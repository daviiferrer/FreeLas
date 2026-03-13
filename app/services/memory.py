import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.proposal_memory import ProposalMemory, ProposalOutcome

logger = logging.getLogger("freelaas.memory")

class MemoryService:
    async def add_proposal(self, project_id: str, category: str, text: str, price: str, delivery_days: str):
        """Save a sent proposal to memory."""
        async with async_session() as db:
            memory = ProposalMemory(
                project_id=project_id,
                category=category,
                proposal_text=text,
                price=price,
                delivery_days=delivery_days,
                outcome=ProposalOutcome.pending
            )
            db.add(memory)
            await db.commit()
            logger.info(f"💾 Proposal saved to memory for project {project_id}")

    async def get_few_shot_examples(self, category: str, limit_won: int = 3, limit_lost: int = 2) -> dict:
        """Fetch past proposals to use as few-shot examples for the LLM prompt."""
        async with async_session() as db:
            # 1. Try to get winning examples for the SAME category
            won_query = select(ProposalMemory).where(
                ProposalMemory.outcome == ProposalOutcome.won,
                ProposalMemory.category == category
            ).order_by(ProposalMemory.created_at.desc()).limit(limit_won)
            
            won_result = await db.execute(won_query)
            won_examples = won_result.scalars().all()
            
            # If we don't have enough in this category, backfill with ANY winning category
            if len(won_examples) < limit_won:
                needed = limit_won - len(won_examples)
                existing_ids = [e.id for e in won_examples]
                fallback_query = select(ProposalMemory).where(
                    ProposalMemory.outcome == ProposalOutcome.won,
                    ProposalMemory.id.not_in(existing_ids) if existing_ids else True
                ).order_by(ProposalMemory.created_at.desc()).limit(needed)
                
                fallback_result = await db.execute(fallback_query)
                won_examples.extend(fallback_result.scalars().all())

            # 2. Get losing examples (any category, to learn from mistakes)
            lost_query = select(ProposalMemory).where(
                ProposalMemory.outcome == ProposalOutcome.lost
            ).order_by(ProposalMemory.created_at.desc()).limit(limit_lost)
            
            lost_result = await db.execute(lost_query)
            lost_examples = lost_result.scalars().all()

            logger.info(f"🧠 Memory loaded: {len(won_examples)} won, {len(lost_examples)} lost examples")
            
            return {
                "won": [e.to_dict() for e in won_examples],
                "lost": [e.to_dict() for e in lost_examples]
            }

memory_service = MemoryService()
