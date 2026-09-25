from urllib.parse import urlparse
from bs4 import BeautifulSoup
import re
import requests

CAREERS_WORDS = (
    "career", "careers", "jobs", "job", "join us", "work with us",
    "opportunities", "vacancies", "open positions", "employment"
)

def _domain(value):
    host = urlparse(value).netloc.lower()
    return host.removeprefix("www.")

def _search_official(company_name):
    query = requests.utils.quote(f"{company_name} official website")
    url = f"https://html.duckduckgo.com/html/?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    blocked = {
        "facebook.com", "linkedin.com", "instagram.com", "twitter.com",
        "x.com", "youtube.com", "wikipedia.org", "glassdoor.com",
        "indeed.com", "ambitionbox.com", "naukri.com"
    }

    for a in soup.select("a.result__a"):
        href = a.get("href", "")
        host = _domain(href)
        if host and not any(host.endswith(x) for x in blocked):
            return f"https://{host}"
    return None

def discover_company(company_name, timeout=15):
    company_name = company_name.strip()
    if not company_name:
        raise ValueError("Company name is required.")

    website = _search_official(company_name)

    if not website:
        slug = re.sub(r"[^a-z0-9]+", "", company_name.lower())
        candidates = [
            f"https://{slug}.com",
            f"https://www.{slug}.com",
        ]
        for candidate in candidates:
            try:
                r = requests.get(candidate, headers={"User-Agent": "Mozilla/5.0"},
                                 timeout=timeout, allow_redirects=True)
                if r.ok:
                    website = r.url
                    break
            except requests.RequestException:
                pass

    if not website:
        raise RuntimeError("Could not discover the official website.")

    r = requests.get(
        website,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=timeout,
        allow_redirects=True,
    )
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    candidates = []

    for a in soup.find_all("a", href=True):
        label = " ".join(a.stripped_strings).lower()
        href = a["href"]
        if any(word in label or word in href.lower() for word in CAREERS_WORDS):
            candidates.append(href)

    from app.services.cleaner import normalize_url, same_domain
    careers = []
    for href in candidates:
        normalized = normalize_url(r.url, href)
        if normalized and same_domain(normalized, r.url):
            careers.append(normalized)

    # Prefer URLs containing careers/jobs.
    careers.sort(key=lambda x: (
        0 if any(w in x.lower() for w in ("careers", "jobs")) else 1,
        len(x)
    ))

    return {
        "name": company_name,
        "website_url": r.url,
        "domain": _domain(r.url),
        "careers_url": careers[0] if careers else None,
    }
