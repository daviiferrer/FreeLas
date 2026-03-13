import asyncio
import logging
import sys
import os

from app.database import async_session
from app.models.proposal_memory import ProposalMemory, ProposalOutcome

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

# Historical proposals provided by Davi that successfully closed
SEED_DATA = [
    {
        "category": "Deploy/VPS",
        "proposal_text": "Consigo subir o teu aplicativo na vps ainda hoje e ainda deixo uma maneira facil de atualizar o codigo na vps apenas apertando um botão. Faço por R$150,00.\n\nPode ver meu perfil, já tenho historico de projetos que eu já subi pra vps e registrei o dominio.",
        "price": "300.00",
        "delivery_days": "1",
        "outcome": ProposalOutcome.won,
        "lessons_learned": "Oferta direta, promessa de entrega no mesmo dia ('ainda hoje'), agregou valor com pipeline CI/CD simples ('atualizar o codigo apenas apertando um botão'), e usou prova social do perfil."
    },
    {
        "category": "Deploy/Web",
        "proposal_text": "Vou colocar teu projeto no ar ainda hoje.",
        "price": "117.65",
        "delivery_days": "1",
        "outcome": ProposalOutcome.won,
        "lessons_learned": "Extremamente conciso. Promessa de entrega muito rápida e preço agressivo para projetos muito simples."
    },
    {
        "category": "Deploy/Web",
        "proposal_text": "Entrega ainda hoje.",
        "price": "117.65",
        "delivery_days": "1",
        "outcome": ProposalOutcome.won,
        "lessons_learned": "Conciso. Demonstra agilidade máxima."
    },
    {
        "category": "Automação/SaaS",
        "proposal_text": "Estava vendo seu projeto de automação no n8n e se encaixa perfeitamente no meu perfil, deixa eu entender melhor: você quer transformar um preenchimento de formulário em uma experiência de compra fluida e profissional, certo?",
        "price": "350.00",
        "delivery_days": "2",
        "outcome": ProposalOutcome.won,
        "lessons_learned": "Abordagem consultiva para projetos complexos. Inicia validando o entendimento do problema ('...você quer transformar X em Y, certo?'). Gera engajamento imediato no chat antes de precificar."
    }
]

async def seed():
    logger.info("Starting seed process for ProposalMemory...")
    async with async_session() as db:
        count = 0
        for item in SEED_DATA:
            memory = ProposalMemory(
                project_id=f"SEED_historical_{count}",
                category=item["category"],
                proposal_text=item["proposal_text"],
                price=item["price"],
                delivery_days=item["delivery_days"],
                outcome=item["outcome"],
                lessons_learned=item["lessons_learned"]
            )
            db.add(memory)
            count += 1
            
        await db.commit()
        logger.info(f"Successfully seeded {count} historical winning proposals into memory.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed())
