import logging
from bs4 import BeautifulSoup

logger = logging.getLogger("freelaas.parser")


def parse_projects(html: str) -> list[dict]:
    """Parse project listings from 99Freelas HTML."""
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    projects = []

    items = soup.select("li.result-item[data-id]")
    if not items:
        items = soup.select("[data-id]")

    for item in items:
        project_id = item.get("data-id")
        if not project_id:
            continue

        title_el = item.select_one(".title a") or item.select_one("h1.title a")
        description_el = item.select_one(".description")
        client_el = item.select_one(".client a")
        
        # Parse client rating
        rating_star = item.select_one(".avaliacoes-star")
        rating_val = rating_star.get("data-score") if rating_star else ""
        rating_text_el = item.select_one(".avaliacoes-text")
        rating_txt = rating_text_el.get_text(strip=True) if rating_text_el else ""
        client_rating = f"{rating_val} {rating_txt}".strip()

        # Parse information paragraph (Category, Experience, Time, Proposals, Interested)
        info_el = item.select_one("p.information")
        category = ""
        experience_level = ""
        proposals_count = ""
        interested_count = ""
        published_time = ""

        if info_el:
            info_raw = info_el.get_text(separator=" ", strip=False)
            parts = [p.strip() for p in info_raw.split('|') if p.strip()]
            
            if len(parts) > 0:
                category = parts[0]
            if len(parts) > 1:
                experience_level = parts[1]
                
            for part in parts:
                if "Propostas:" in part:
                    proposals_count = part.replace("Propostas:", "").strip()
                elif "Interessados:" in part:
                    interested_count = part.replace("Interessados:", "").strip()
                    
            datetime_el = info_el.select_one(".datetime")
            if datetime_el:
                if datetime_el.get("cp-datetime"):
                    try:
                        import datetime
                        ts_ms = int(datetime_el["cp-datetime"])
                        published_time = datetime.datetime.fromtimestamp(ts_ms / 1000.0).isoformat()
                    except (ValueError, TypeError):
                        published_time = datetime_el.get_text(strip=True)
                else:
                    published_time = datetime_el.get_text(strip=True)

        url = ""
        if title_el and title_el.get("href"):
            href = title_el["href"]
            url = href if href.startswith("http") else f"https://www.99freelas.com.br{href}"

        project = {
            "project_id": str(project_id).strip(),
            "title": title_el.get_text(strip=True) if title_el else "",
            "description": description_el.get_text(strip=True) if description_el else "",
            "category": category,
            "experience_level": experience_level,
            "client_name": client_el.get_text(strip=True) if client_el else "",
            "client_rating": client_rating,
            "proposals_count": proposals_count,
            "interested_count": interested_count,
            "published_time": published_time,
            "url": url,
        }

        if project["title"]:
            projects.append(project)

    logger.info(f"Parsed {len(projects)} projects from HTML")
    return projects
