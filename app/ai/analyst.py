import logging
from app.ai.openai_client import call_llm
from app.ai.prompts import ANALYST_SYSTEM_PROMPT
from app.config import settings, event_bus

logger = logging.getLogger("freelaas.analyst")


async def run_analyst(project: dict) -> dict | None:
    """Agent 2 — Analyst: Deep qualification. Score >= 7 passes to Phase 3."""
    user_message = f"""PROJETO PARA ANÁLISE PROFUNDA:

Título: {project.get('title', '')}
Descrição: {project.get('description', '')[:800]}
Categoria: {project.get('category', '')}
Nível de Experiência: {project.get('experience_level', 'N/A')}
Cliente: {project.get('client_name', 'N/A')}
Avaliação do Cliente: {project.get('client_rating', 'N/A')}
Propostas Enviadas: {project.get('proposals_count', 'N/A')}
Interessados: {project.get('interested_count', 'N/A')}
Score da Fase 1: {project.get('ai_score_phase1', 'N/A')}
"""

    await event_bus.publish("agent_start", {
        "agent": "Analyst",
        "phase": 2,
        "project_id": project.get("project_id", ""),
        "title": project.get("title", ""),
        "message": f"🔬 Analyst analisando profundamente: {project.get('title', '')[:60]}"
    })

    result = await call_llm(
        model=settings.MODEL_ANALYST,
        system_prompt=ANALYST_SYSTEM_PROMPT,
        user_message=user_message,
        agent_name="Analyst",
        project_id=project.get("project_id", ""),
    )

    if not result:
        return {"score": 0, "decision": "reject", "problem_identified": "", "client_archetype": "", "complexity": ""}

    # New scale 0-10, cutoff 7
    score = result.get("score", 0)
    decision = "phase3" if score >= 7 else "reject"
    result["decision"] = decision

    emoji = "✅" if decision == "phase3" else "❌"
    log_msg = f"{emoji} Analyst: {score}/10 — Arquétipo: {result.get('client_archetype', 'N/A')} — Complexidade: {result.get('complexity', 'N/A')}"
    logger.info(log_msg)

    await event_bus.publish("agent_result", {
        "agent": "Analyst",
        "phase": 2,
        "project_id": project.get("project_id", ""),
        "score": score,
        "decision": decision,
        "complexity": result.get("complexity", ""),
        "message": log_msg
    })

    return result
