import logging
import httpx
from app.config import settings

logger = logging.getLogger("freelaas.waha")

class WahaClient:
    def __init__(self):
        self.base_url = settings.WAHA_API_URL
        self.api_key = settings.WAHA_API_KEY
        self.session = settings.WAHA_SESSION
        self.phone = settings.WAHA_PHONE_NUMBER

    async def send_message(self, chat_id: str, text: str) -> str | None:
        """Sends a text message to a WhatsApp number."""
        url = f"{self.base_url}/api/sendText"
        
        # Ensure chat_id has the @c.us suffix if it's a phone number
        if "@" not in chat_id:
            chat_id = f"{chat_id}@c.us"

        payload = {
            "chatId": chat_id,
            "text": text,
            "session": self.session
        }

        headers = {}
        if self.api_key:
            headers["X-Api-Key"] = self.api_key

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                if response.is_error:
                    logger.error(f"❌ WAHA Error {response.status_code}: {response.text}")
                response.raise_for_status()
                result = response.json()
                # Status code 201 or 200 depending on version
                return result.get("id")
        except Exception as e:
            logger.error(f"❌ Error sending message via WAHA: {e}")
            return None

    async def send_approval_request(self, project: dict) -> str | None:
        """Formatted request for human approval via WhatsApp."""
        action = project.get("ai_action", "SEND_PROPOSAL")
        
        # Emoji and Title based on Action
        title_emoji = "🚀" if action == "SEND_PROPOSAL" else "❓"
        title_text = "PROPOSTA" if action == "SEND_PROPOSAL" else "PERGUNTA"
        
        # Metadata
        cat = project.get('category', 'N/A')
        exp = project.get('experience_level', 'N/A')
        rating = project.get('client_rating', 'N/A')
        status_emoji = "🚀" if action == "SEND_PROPOSAL" else "❓"
        action_label = "PROPOSTA" if action == "SEND_PROPOSAL" else "PERGUNTA"
        
        # Scorecard logic
        s1 = project.get('ai_score_phase1', 0)
        s2 = project.get('ai_score_phase2', 0)
        complex = project.get('ai_complexity', 'N/A').upper()
        # Métricas de Poder (Social Proof & Authority)
        try:
            propostas = int(project.get('proposals_count', 0))
        except (ValueError, TypeError):
            propostas = 0
            
        try:
            nota = float(project.get('client_rating', 0.0))
        except (ValueError, TypeError):
            nota = 0.0
        social_proof = "💎 Sniper (<5)" if propostas < 5 else "📩 Comparação" if propostas <= 15 else "🔥 Saturado"
        authority = "⭐ Autoridade (5.0)" if nota >= 4.9 else f"⭐ Nota: {nota}" if nota > 0 else "👤 Iniciante (0.0)"

        strategy = project.get('strategy', 'Estratégia baseada em PSC.')
        proposal = project.get('proposal_text') if action == "SEND_PROPOSAL" else project.get('ai_question')

        text = (
            f"{status_emoji} *{action_label} PROJECT: {project.get('title')}*\n"
            f"🔗 {project.get('url')}\n\n"
            f"📌 *O QUE O CLIENTE QUER:*\n"
            f"{project.get('ai_summary', 'Sem resumo.')}\n\n"
            f"🎯 *HUNTING JUSTIFICATION:*\n"
            f"{project.get('ai_reason', 'Sem justificativa.')}\n\n"
            f"📊 *MÉTRICAS DO MERCADO:*\n"
            f"📩 Propostas: {propostas} ({social_proof})\n"
            f"{authority}\n"
            f"🏆 Nível: {project.get('experience_level', 'N/A')} | 📂 {project.get('category', 'N/A')}\n\n"
            f"🛠️ *ESTRATÉGIA:* {strategy}\n\n"
            f"✍️ *{action_label}:*\n"
            f"{proposal}\n\n"
            f"💰 *VALOR:* R$ {project.get('recommended_price', '---')}\n"
            f"⏱️ *PRAZO:* {project.get('recommended_delivery_time', '---')} dias"
        )
        return await self.send_message(self.phone, text)

waha_client = WahaClient()
