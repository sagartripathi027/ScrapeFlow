from urllib.parse import urljoin

import requests


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}


ATS_PATTERNS = {
    "greenhouse": (
        "greenhouse.io",
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
    ),
    "lever": (
        "lever.co",
        "jobs.lever.co",
    ),
    "ashby": (
        "ashbyhq.com",
        "jobs.ashbyhq.com",
    ),
    "smartrecruiters": (
        "smartrecruiters.com",
        "careers.smartrecruiters.com",
    ),
    "workday": (
        "myworkdayjobs.com",
        "workday.com",
    ),
    "icims": (
        "icims.com",
    ),
    "jobvite": (
        "jobvite.com",
    ),
}
KNOWN_ATS_BOARDS = {
    "aqr.com": {
        "ats": "greenhouse",
        "url": "https://boards.greenhouse.io/aqr",
    },
}


def detect_ats_from_url(url):
    if not url:
        return None

    url_lower = url.lower()

    for ats_name, patterns in ATS_PATTERNS.items():
        for pattern in patterns:
            if pattern in url_lower:
                return {
                    "ats": ats_name,
                    "url": url,
                }

    return None


def detect_ats_from_page(url):
    if not url:
        return None

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15,
            allow_redirects=True,
        )

        print(
            "ATS PAGE CHECK:",
            response.status_code,
            "->",
            response.url,
        )

        if response.status_code >= 400:
            return None

        soup_text = response.text

        for ats_name, patterns in ATS_PATTERNS.items():

            for pattern in patterns:

                if pattern not in soup_text.lower():
                    continue

                # Try to find an actual ATS URL from links.
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(
                    response.text,
                    "html.parser",
                )

                for link in soup.find_all("a", href=True):

                    href = link.get("href", "").strip()

                    if not href:
                        continue

                    absolute_url = urljoin(
                        response.url,
                        href,
                    )

                    if pattern in absolute_url.lower():

                        return {
                            "ats": ats_name,
                            "url": absolute_url,
                        }

                # ATS signal found but no direct link found.
                return {
                    "ats": ats_name,
                    "url": url,
                }

    except requests.RequestException as exc:
        print(
            "ATS DETECTION ERROR:",
            repr(exc),
        )

    return None


def discover_ats(careers_url):
    """
    Detect ATS and return the actual ATS board URL when possible.
    """

    if not careers_url:
        return None

    # ---------------------------------------------------------
    # 0. Check known ATS board mappings
    # ---------------------------------------------------------

    from urllib.parse import urlparse

    parsed = urlparse(careers_url)
    domain = parsed.netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    known_ats = KNOWN_ATS_BOARDS.get(domain)

    if known_ats:
        print(
            "KNOWN ATS DETECTED:",
            known_ats["ats"],
            "->",
            known_ats["url"],
        )

        return known_ats

    # ---------------------------------------------------------
    # 1. Check whether careers URL itself is an ATS URL
    # ---------------------------------------------------------

    detected = detect_ats_from_url(careers_url)

    if detected:
        print(
            "ATS DETECTED:",
            detected["ats"],
            "->",
            detected["url"],
        )

        return detected

    # ---------------------------------------------------------
    # 2. Inspect careers page
    # ---------------------------------------------------------

    detected = detect_ats_from_page(careers_url)

    if detected:
        print(
            "ATS DETECTED:",
            detected["ats"],
            "->",
            detected["url"],
        )

        return detected

    print("ATS DETECTED: NONE")

    return None