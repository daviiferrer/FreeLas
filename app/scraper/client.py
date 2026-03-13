import logging
import asyncio
import random
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

logger = logging.getLogger("freelaas.scraper")

BASE_URL = "https://www.99freelas.com.br/projects"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]


async def fetch_page(page: int = 1) -> str | None:
    url = f"{BASE_URL}?order=mais-recentes&categoria=web-mobile-e-software&page={page}"
    
    async with async_playwright() as p:
        browser = None
        try:
            # Launch browser with essential bypass args
            browser = await p.chromium.launch(
                headless=True, 
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"]
            )
            
            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={'width': 1280, 'height': 720}
            )
            
            page_obj = await context.new_page()
            await stealth_async(page_obj)
            
            logger.info(f"🌐 [Scraper] Buscando página {page} usando Playwright...")
            
            # Go to the URL
            response = await page_obj.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            if not response or response.status == 403:
                logger.error(f"❌ [Scraper] Bloqueio detectado (Status {response.status if response else 'None'})")
                return None
            
            # Small random wait to simulate human reading or JS execution
            await asyncio.sleep(random.uniform(2, 5))
            
            content = await page_obj.content()
            
            # Final check if Cloudflare challenge is stuck
            if "challenge-running" in content or "ray_id" in content and "Forbidden" in content:
                logger.error(f"❌ [Scraper] Cloudflare capturou o Playwright na página {page}")
                return None
            
            return content
            
        except Exception as e:
            logger.error(f"❌ [Scraper] Erro crítica ao buscar página {page}: {e}")
            return None
        finally:
            if browser:
                await browser.close()
