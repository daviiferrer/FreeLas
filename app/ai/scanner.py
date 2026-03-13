import logging
from app.ai.openai_client import call_llm
from app.ai.prompts import SCANNER_SYSTEM_PROMPT
from app.config import settings, event_bus

logger = logging.getLogger("freelaas.scanner")


async def run_scanner(project: dict) -> dict | None:
    """Agent 1 — Scanner: Quick relevance filter. Score >= 6 passes to Phase 2."""
    user_message = f"""PROJETO PARA ANÁLISE RÁPIDA:

Título: {project.get('title', '')}
Descrição: {project.get('description', '')[:500]}
Categoria: {project.get('category', '')}
"""

    await event_bus.publish("agent_start", {
        "agent": "Scanner",
        "phase": 1,
        "project_id": project.get("project_id", ""),
        "title": project.get("title", ""),
        "message": f"🔍 Scanner analisando: {project.get('title', '')[:60]}"
    })

    result = await call_llm(
        model=settings.MODEL_SCANNER,
        system_prompt=SCANNER_SYSTEM_PROMPT,
        user_message=user_message,
        agent_name="Scanner",
        project_id=project.get("project_id", ""),
    )

    if not result:
        return {"score": 0, "reason": "Erro na análise", "decision": "reject"}

    # New scale 0-10, cutoff 6
    score = result.get("score", 0)
    decision = "phase2" if score >= 6 else "reject"
    result["decision"] = decision

    emoji = "✅" if decision == "phase2" else "❌"
    log_msg = f"{emoji} Scanner: {score}/10 — {result.get('reason', '')}"
    logger.info(log_msg)
    
    await event_bus.publish("agent_result", {
        "agent": "Scanner",
        "phase": 1,
        "project_id": project.get("project_id", ""),
        "score": score,
        "decision": decision,
        "reason": result.get("reason", ""),
        "message": log_msg
    })

    return result
