import logging
import asyncio
import cloudscraper

logger = logging.getLogger("freelaas.scraper")

BASE_URL = "https://www.99freelas.com.br/projects"

async def fetch_page(page: int = 1) -> str | None:
    url = f"{BASE_URL}?order=mais-recentes&categoria=web-mobile-e-software&page={page}"
    
    def _fetch():
        # cloudscraper simulates a real browser environment specifically for Cloudflare
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        logger.info(f"🌐 [Scraper] Buscando página {page} usando Cloudscraper (Lightweight)...")
        response = scraper.get(url, timeout=30)
        
        if response.status_code == 403:
            logger.error(f"❌ [Scraper] Acesso Negado (403). Cloudflare bloqueou o Cloudscraper.")
            return None
            
        response.raise_for_status()
        return response.text

    try:
        # Run the synchronous cloudscraper in a background thread to not block async loop
        content = await asyncio.to_thread(_fetch)
        return content
    except Exception as e:
        logger.error(f"❌ [Scraper] Erro crítica ao buscar página {page}: {e}")
        return None
