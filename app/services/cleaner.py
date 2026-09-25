import re
from urllib.parse import urljoin, urlparse


def clean_text(value):
    if not value:
        return ""

    return re.sub(r"\s+", " ", value).strip()


def normalize_url(base, href):
    if not href:
        return None

    url = urljoin(base, href.strip())
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return None

    return url.split("#", 1)[0]


def same_domain(a, b):
    try:
        domain_a = urlparse(a).netloc.lower().removeprefix("www.")
        domain_b = urlparse(b).netloc.lower().removeprefix("www.")

        return domain_a == domain_b

    except Exception:
        return False


def unique_by_url(items):
    seen = set()
    result = []

    for item in items:
        url = item.get("source_url")

        if not url or url in seen:
            continue

        seen.add(url)
        result.append(item)

    return result