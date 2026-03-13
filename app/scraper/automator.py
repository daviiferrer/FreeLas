import logging
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from app.config import settings

logger = logging.getLogger("freelaas.automator")

AUTH_FILE = "/app/auth.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


class FreelasAutomator:
    def __init__(self):
        self.auth_file = AUTH_FILE

    async def _get_context(self, playwright):
        """Launches browser with persistent or loaded session."""
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        import os
        if os.path.exists(self.auth_file):
            context = await browser.new_context(
                storage_state=self.auth_file,
                user_agent=USER_AGENT,
                viewport={'width': 1280, 'height': 720}
            )
        else:
            logger.error(f"❌ Auth file {self.auth_file} not found. Run login_manual.py first.")
            await browser.close()
            return None, None
        return browser, context

    async def send_proposal(self, project_url: str, text: str, price: str, delivery_days: str) -> bool:
        """Automates the proposal submission on a 99Freelas project page."""
        if not settings.AUTO_ACTION_ENABLED:
            logger.info("⏸️ AUTO_ACTION_ENABLED is off. Skipping proposal submission.")
            return False

        # Convert to bid URL
        if "/project/bid/" not in project_url:
            project_url = project_url.replace("/project/", "/project/bid/")

        async with async_playwright() as p:
            browser, context = await self._get_context(p)
            if not context:
                return False

            page = await context.new_page()
            await stealth_async(page)
            try:
                logger.info(f"🌐 Navegando para formulário de proposta: {project_url}")
                await page.goto(project_url, wait_until="networkidle", timeout=30000)

                # Check if redirected to login
                if "/login" in page.url or "/register" in page.url:
                    logger.error("❌ Sessão expirada ou inválida. Redirecionado para login.")
                    return False

                logger.info("✍️ Preenchendo campos da proposta...")
                await page.fill("input#oferta", str(price))
                await page.fill("input#duracao-estimada", str(delivery_days))
                await page.fill("textarea#proposta", text)

                # Human-like delay
                await asyncio.sleep(2)

                logger.info("🚀 Enviando proposta...")
                await page.click("button#btnConcluirEnvioProposta")
                
                # Wait for confirmation
                await asyncio.sleep(3)
                
                # Screenshot for audit trail
                await page.screenshot(path="/app/last_proposal_sent.png")
                logger.info("✅ Proposta enviada com sucesso!")
                return True

            except Exception as e:
                logger.error(f"❌ Erro ao automatizar proposta: {e}", exc_info=True)
                try:
                    await page.screenshot(path="/app/last_proposal_error.png")
                except Exception:
                    pass
                return False
            finally:
                await browser.close()

    async def send_question(self, project_url: str, question: str) -> bool:
        """Automates sending a question on a project."""
        if not settings.AUTO_ACTION_ENABLED:
            logger.info("⏸️ AUTO_ACTION_ENABLED is off. Skipping question submission.")
            return False

        # Convert to message URL
        msg_url = project_url.replace("/project/bid/", "/project/message/").replace("/project/", "/project/message/")

        async with async_playwright() as p:
            browser, context = await self._get_context(p)
            if not context:
                return False

            page = await context.new_page()
            await stealth_async(page)
            try:
                logger.info(f"🌐 Navegando para envio de pergunta: {msg_url}")
                await page.goto(msg_url, wait_until="networkidle", timeout=30000)

                if "/login" in page.url or "/register" in page.url:
                    logger.error("❌ Sessão expirada ou inválida.")
                    return False

                await page.fill("textarea#mensagem-pergunta", question)
                await asyncio.sleep(1)

                logger.info("🚀 Enviando pergunta...")
                await page.click("button#btnEnviarPergunta")
                
                await asyncio.sleep(2)
                await page.screenshot(path="/app/last_question_sent.png")
                logger.info("✅ Pergunta enviada com sucesso!")
                return True

            except Exception as e:
                logger.error(f"❌ Erro ao automatizar pergunta: {e}", exc_info=True)
                return False
            finally:
                await browser.close()


automator = FreelasAutomator()
