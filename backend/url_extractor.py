"""
URL Article Extractor.
Scrapes and parses headline, metadata, and body text from news URLs.
Extracts clean plain text suitable for verification.
"""

import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def extract_from_url(url: str) -> dict:
    """
    Extracts article title, body text, and meta description from a target URL.
    Returns:
    - title: Headline of the article
    - text: Extracted article text body
    - meta_description: Summary snippet if found
    - source_domain: Domain name
    """
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP status code {resp.status_code} returned by target server."
            }

        soup = BeautifulSoup(resp.text, "html.parser")

        # 1. Extract Title
        title = ""
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()
        elif soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Clean title
        title = re.sub(r"\s+", " ", title)

        # 2. Extract Meta description
        meta_desc = ""
        og_desc = soup.find("meta", property="og:description")
        meta_d = soup.find("meta", attrs={"name": "description"})
        if og_desc and og_desc.get("content"):
            meta_desc = og_desc["content"].strip()
        elif meta_d and meta_d.get("content"):
            meta_desc = meta_d["content"].strip()

        # 3. Extract main article paragraphs
        article_elem = soup.find("article") or soup.find("main") or soup.body
        paragraphs = []
        if article_elem:
            for p in article_elem.find_all("p"):
                p_text = p.get_text(separator=" ", strip=True)
                if len(p_text.split()) > 7:
                    paragraphs.append(p_text)

        full_body = "\n\n".join(paragraphs[:8])  # First 8 substantive paragraphs

        # If paragraphs are sparse, fall back to meta_desc or title
        if not full_body:
            full_body = meta_desc or title

        # Extract domain
        domain = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]

        return {
            "success": True,
            "url": url,
            "domain": domain,
            "title": title,
            "meta_description": meta_desc,
            "body_text": full_body,
            "combined_content": f"{title}\n\n{full_body}".strip()
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to retrieve URL content: {str(e)}"
        }
