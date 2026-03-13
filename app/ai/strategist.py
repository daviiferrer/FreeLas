import logging
import json
from app.ai.openai_client import call_llm
from app.ai.prompts import STRATEGIST_SYSTEM_PROMPT
from app.config import settings, event_bus
from app.services.memory import memory_service

logger = logging.getLogger("freelaas.strategist")


async def run_strategist(project: dict, analyst_data: dict = None, scanner_data: dict = None) -> dict | None:
    """Agent 3 — Proposal Strategist: Generate personalized high-conversion proposal."""
    
    # --- Load Memory (Few-Shot Examples) ---
    category = project.get('category', 'Default')
    memory = await memory_service.get_few_shot_examples(category)
    
    won_context = ""
    if memory["won"]:
        won_context = "\n[EXEMPLOS DE PROPOSTAS VENCEDORAS - USE ESTE TOM E ESTRUTURA!]\n"
        for i, ex in enumerate(memory["won"], 1):
            won_context += f"Exemplo {i}:\nTexto: {ex['proposal_text']}\nPreço: {ex.get('price', 'N/A')}\nPrazo: {ex.get('delivery_days', 'N/A')}\n---\n"
            
    lost_context = ""
    if memory["lost"]:
        lost_context = "\n[EXEMPLOS DE PROPOSTAS PERDEDORAS - CUIDADO, EVITE ESTES PADRÕES!]\n"
        for i, ex in enumerate(memory["lost"], 1):
            lost_context += f"Exemplo {i}:\nTexto: {ex['proposal_text']}\nErro/Lição: {ex.get('lessons_learned', 'Desconhecida')}\n---\n"

    # --- Scanner/Analyst Contexts ---
    scanner_context = ""
    if scanner_data:
        scanner_context = f"""
RESULTADOS DO SCANNER (FASE 1):
- Score Triagem: {scanner_data.get('score', 'N/A')}/10
- Motivo: {scanner_data.get('reason', 'N/A')}
- Decisão: {scanner_data.get('decision', 'N/A')}
"""

    analyst_context = ""
    if analyst_data:
        analyst_context = f"""
RESULTADOS DO ANALYST (FASE 2):
- Score HACRB: {analyst_data.get('score', 'N/A')}
- Detalhes: {analyst_data.get('criteria', analyst_data.get('hacrb_details', {}))}
- Arquétipo do Cliente: {analyst_data.get('client_archetype', 'N/A')}
- Problema Identificado: {analyst_data.get('problem_identified', 'N/A')}
- Decisão do Analyst: {analyst_data.get('decision', 'N/A')}
"""

    user_message = f"""PROJETO PARA ANÁLISE DO STRATEGIST:

Título: {project.get('title', '')}
Descrição: {project.get('description', '')[:1000]}
Cliente: {project.get('client_name', 'N/A')}
Categoria: {project.get('category', 'N/A')}
Nota do Cliente: {project.get('client_rating', 'N/A')}
Propostas: {project.get('proposals_count', 'N/A')}

{scanner_context}
{analyst_context}
{won_context}
{lost_context}

Analise as informações acima. IMPORTANTE: Se o Analyst deu um score baixo ou decidiu "reject", você deve ser MUITO cauteloso na justificativa (hunting_justification), destacando os riscos para o Davi em vez de apenas chamar de "ouro".
Gere o JSON correspondente conforme sua instrução.
"""

    await event_bus.publish("agent_start", {
        "agent": "Strategist",
        "phase": 3,
        "project_id": project.get("project_id", ""),
        "title": project.get("title", ""),
        "message": f"✍️ Strategist gerando proposta para: {project.get('title', '')[:60]}"
    })

    result = await call_llm(
        model=settings.MODEL_STRATEGIST,
        system_prompt=STRATEGIST_SYSTEM_PROMPT,
        user_message=user_message,
        agent_name="Strategist",
        project_id=project.get("project_id", ""),
    )

    if not result:
        return None

    action = result.get("action", "SEND_PROPOSAL")
    
    if action == "ASK_QUESTION":
        await event_bus.publish("strategist_question_generated", {
            "agent": "Strategist",
            "phase": 3,
            "project_id": project.get("project_id", ""),
            "title": project.get("title", ""),
            "question_preview": result.get("question_text", "")[:200],
            "message": f"❓ Strategist elaborou uma pergunta para o cliente."
        })
    else:
        log_msg = f"🎯 Strategist gerou proposta! Estratégia: {result.get('strategy', 'N/A')[:100]}..."
        logger.info(log_msg)
        await event_bus.publish("proposal_generated", {
            "agent": "Strategist",
            "phase": 3,
            "project_id": project.get("project_id", ""),
            "title": project.get("title", ""),
            "proposal_preview": result.get("proposal_text", "")[:200],
            "strategy": result.get("strategy", ""),
            "recommended_price": result.get("recommended_price", ""),
            "recommended_delivery_time": result.get("recommended_delivery_time", ""),
            "message": log_msg
        })

    return result
