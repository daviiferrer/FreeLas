import logging

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models.project import Project, ProjectStatus
from app.scraper.automator import automator
from app.services.waha import waha_client

logger = logging.getLogger("freelaas.webhook")

router = APIRouter(prefix="/api")

# Approval keywords (case-insensitive)
APPROVE_KEYWORDS = {"sim", "s", "ok", "aprova", "aprovado", "manda", "envia", "vai", "pode", "✅", "👍"}
REJECT_KEYWORDS = {"não", "nao", "n", "rejeita", "rejeitado", "cancela", "❌", "👎"}


@router.post("/webhook/waha")
async def waha_webhook(request: Request):
    """
    Receives incoming WhatsApp messages from WAHA.
    Matches replies to pending projects and processes approval/rejection.
    """
    try:
        payload = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON"}

    # WAHA sends different event types
    event = payload.get("event", "")
    if event != "message":
        return {"status": "ignored", "reason": f"Event type: {event}"}

    # Extract message data
    message_data = payload.get("payload", payload)
    
    # Get the text content
    body = (message_data.get("body") or "").strip().lower()
    if not body:
        return {"status": "ignored", "reason": "Empty message body"}

    # Check if this is from the Davi's number
    from_number = message_data.get("from", "")
    if settings.WAHA_PHONE_NUMBER and settings.WAHA_PHONE_NUMBER not in from_number:
        return {"status": "ignored", "reason": "Not from authorized number"}

    # Check if it's a reply to a WAHA message (quoted message)
    quoted_msg_id = None
    if "quotedMsg" in message_data:
        quoted_msg_id = message_data["quotedMsg"].get("id")
    elif "quoted_message_id" in message_data:
        quoted_msg_id = message_data["quoted_message_id"]
    elif "_data" in message_data and "quotedMsg" in message_data["_data"]:
        quoted_msg_id = message_data["_data"]["quotedMsg"].get("id")

    # Find the project by quoted message ID or by most recent pending
    async with async_session() as db:
        project = None
        
        if quoted_msg_id:
            # Match by WAHA message ID (quoted reply)
            result = await db.execute(
                select(Project).where(
                    Project.waha_message_id == quoted_msg_id,
                    Project.status == ProjectStatus.pending_approval
                )
            )
            project = result.scalar_one_or_none()
        
        if not project:
            # Fallback: match most recent pending_approval project
            result = await db.execute(
                select(Project)
                .where(Project.status == ProjectStatus.pending_approval)
                .order_by(Project.scraped_at.desc())
                .limit(1)
            )
            project = result.scalar_one_or_none()

        if not project:
            logger.warning(f"⚠️ Webhook: No pending project found for message: '{body[:50]}'")
            return {"status": "no_match", "message": "No pending project found"}

        # Process the response
        if body in APPROVE_KEYWORDS or any(kw in body for kw in APPROVE_KEYWORDS):
            logger.info(f"✅ Project {project.project_id} APPROVED by Davi!")
            project.status = ProjectStatus.approved
            await db.commit()

            # Execute action if kill switch is on
            if settings.AUTO_ACTION_ENABLED:
                success = await _execute_action(project)
                if success:
                    project.status = ProjectStatus.sent
                    await db.commit()
                    
                    # Save context to Memory Bank for Strategist
                    from app.services.memory import memory_service
                    await memory_service.add_proposal(
                        project_id=project.project_id,
                        category=project.category,
                        text=project.proposal_text or project.ai_question or "",
                        price=project.recommended_price,
                        delivery_days=project.recommended_delivery_time
                    )
                    
                    # Send confirmation
                    await waha_client.send_message(
                        settings.WAHA_PHONE_NUMBER,
                        f"✅ *{project.ai_action}* enviada com sucesso para: {project.title}\n🔗 {project.url}"
                    )
                    return {"status": "sent", "project_id": project.project_id}
                else:
                    await waha_client.send_message(
                        settings.WAHA_PHONE_NUMBER,
                        f"❌ Falha ao enviar para: {project.title}\nVerifique se a sessão do 99Freelas está ativa."
                    )
                    return {"status": "action_failed", "project_id": project.project_id}
            else:
                await waha_client.send_message(
                    settings.WAHA_PHONE_NUMBER,
                    f"👍 Aprovado! Mas AUTO_ACTION está desligado.\nProjeto: {project.title}"
                )
                return {"status": "approved_no_action", "project_id": project.project_id}

        elif body in REJECT_KEYWORDS or any(kw in body for kw in REJECT_KEYWORDS):
            logger.info(f"❌ Project {project.project_id} REJECTED by Davi.")
            project.status = ProjectStatus.rejected
            await db.commit()
            return {"status": "rejected", "project_id": project.project_id}

        else:
            # Treat as edited proposal text
            logger.info(f"✏️ Project {project.project_id} proposal EDITED by Davi: '{body[:100]}'")
            if project.ai_action == "SEND_PROPOSAL":
                project.proposal_text = body  # Use original case
                raw_payload = await request.body()
                # Re-extract original case body
                try:
                    import json
                    raw = json.loads(raw_payload)
                    original_body = (raw.get("payload", raw).get("body") or "").strip()
                    if original_body:
                        project.proposal_text = original_body
                except Exception:
                    pass
            else:
                project.ai_question = body
            await db.commit()

            await waha_client.send_message(
                settings.WAHA_PHONE_NUMBER,
                f"✏️ Texto atualizado! Responda *SIM* para enviar ou *NÃO* para cancelar."
            )
            return {"status": "edited", "project_id": project.project_id}


async def _execute_action(project: Project) -> bool:
    """Execute the approved action via Playwright."""
    try:
        if project.ai_action == "SEND_PROPOSAL":
            return await automator.send_proposal(
                project_url=project.url,
                text=project.proposal_text or "",
                price=project.recommended_price or "0",
                delivery_days=project.recommended_delivery_time or "7"
            )
        elif project.ai_action == "ASK_QUESTION":
            return await automator.send_question(
                project_url=project.url,
                question=project.ai_question or ""
            )
        else:
            logger.warning(f"Unknown action type: {project.ai_action}")
            return False
    except Exception as e:
        logger.error(f"❌ Action execution failed: {e}", exc_info=True)
        return False
