from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

BLOCKED_DOMAINS = {
    "facebook.com",
    "linkedin.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "wikipedia.org",
    "glassdoor.com",
    "indeed.com",
    "ambitionbox.com",
    "naukri.com",
}

# Common companies -> official domains.
# This is only a fast path; unknown companies still use search.
KNOWN_DOMAINS = {
    "tcs": "https://www.tcs.com",
    "tata consultancy services": "https://www.tcs.com",
    "infosys": "https://www.infosys.com",
    "microsoft": "https://www.microsoft.com",
    "google": "https://www.google.com",
    "amazon": "https://www.amazon.jobs",
    "wipro": "https://www.wipro.com",
    "accenture": "https://www.accenture.com",
    "aqr": "https://www.aqr.com",
    "ibm": "https://www.ibm.com",
    "cognizant": "https://www.cognizant.com",
    "hcl": "https://www.hcltech.com",
    "hcltech": "https://www.hcltech.com",
    "capgemini": "https://www.capgemini.com",
    "tech mahindra": "https://www.techmahindra.com",
    "deloitte": "https://www.deloitte.com",
}



KNOWN_CAREERS = {
    "tcs": "https://www.tcs.com/careers",
    "tata consultancy services": "https://www.tcs.com/careers",
    "infosys": "https://digitalcareers.infosys.com/infosys/global-careers",
    "microsoft": "https://careers.microsoft.com/",
    "google": "https://www.google.com/about/careers/applications/jobs/results/",
    "amazon": "https://www.amazon.jobs/en/search",
    "wipro": "https://careers.wipro.com/",
    "accenture": "https://www.accenture.com/in-en/careers",
    "aqr": "https://www.aqr.com/careers",
    "ibm": "https://www.ibm.com/careers",
    "cognizant": "https://careers.cognizant.com/",
    "hcl": "https://www.hcltech.com/careers",
    "hcltech": "https://www.hcltech.com/careers",
    "capgemini": "https://www.capgemini.com/careers/",
    "tech mahindra": "https://careers.techmahindra.com/",
    "deloitte": "https://www.deloitte.com/in/en/careers.html",
}


CAREERS_WORDS = (
    "career",
    "careers",
    "jobs",
    "job openings",
    "job opportunities",
    "join us",
    "work with us",
    "opportunities",
    "vacancies",
    "open positions",
    "employment",
)


def get_domain(url):
    try:
        domain = urlparse(url).netloc.lower()

        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    except Exception:
        return ""


def is_blocked(domain):
    domain = domain.lower()

    return any(
        domain == blocked or domain.endswith("." + blocked)
        for blocked in BLOCKED_DOMAINS
    )


def verify_website(url):
    """
    Verify that the website exists.
    Some company websites return 403 to automated requests,
    so 403 is still treated as a reachable website.
    """
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15,
            allow_redirects=True,
        )

        print("VERIFY STATUS:", response.status_code)
        print("VERIFY URL:", response.url)

        final_url = response.url
        domain = get_domain(final_url)

        if not domain:
            return None

        if is_blocked(domain):
            print("VERIFY BLOCKED:", domain)
            return None

        # 403 can mean the site blocks bots, not that the
        # website is invalid.
        if response.status_code in (200, 301, 302, 403):
            return final_url

        return None

    except requests.RequestException as exc:
        print("VERIFY ERROR:", repr(exc))
        return None


def search_official_website(company_name):
    """
    Find an official company website.

    First checks known companies.
    For unknown companies, uses DuckDuckGo HTML search.
    """

    normalized = " ".join(company_name.lower().split())

    # ---------------------------------------------------------
    # FAST PATH: known companies
    # ---------------------------------------------------------

    known_url = KNOWN_DOMAINS.get(normalized)

    if known_url:
        verified = verify_website(known_url)

        if verified:
            return verified

    # ---------------------------------------------------------
    # SEARCH PATH: unknown companies
    # ---------------------------------------------------------

    search_url = "https://html.duckduckgo.com/html/"

    try:
        response = requests.get(
            search_url,
            params={
                "q": f"{company_name} official website"
            },
            headers=HEADERS,
            timeout=15,
        )

        response.raise_for_status()

    except requests.RequestException as exc:
        print("SEARCH ERROR:", exc)
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    candidates = []

    for link in soup.select("a.result__a"):

        href = link.get("href", "").strip()

        if not href:
            continue

        domain = get_domain(href)

        if not domain:
            continue

        if is_blocked(domain):
            continue

        if any(
            engine in domain
            for engine in (
                "duckduckgo",
                "google.",
                "bing.",
                "yahoo.",
            )
        ):
            continue

        candidates.append(href)

    # Verify candidates instead of blindly trusting first result.
    for candidate in candidates:

        verified = verify_website(candidate)

        if verified:
            return verified

    return None


def find_careers_url(website_url):
    """
    Find a company's careers/jobs page.

    Some websites block automated access to their homepage with 403.
    In that case, try common careers URL patterns directly.
    """

    base_url = website_url.rstrip("/")

    # Common careers URL patterns
    candidate_paths = [
        "/careers",
        "/careers/",
        "/jobs",
        "/jobs/",
        "/career",
        "/career/",
        "/job-opportunities",
        "/work-with-us",
        "/join-us",
    ]

    # ---------------------------------------------------------
    # First try direct careers URLs
    # ---------------------------------------------------------

    for path in candidate_paths:

        candidate_url = urljoin(
            base_url + "/",
            path.lstrip("/")
        )

        try:
            response = requests.get(
                candidate_url,
                headers=HEADERS,
                timeout=10,
                allow_redirects=True,
            )

            print(
                "CAREERS CHECK:",
                candidate_url,
                "->",
                response.status_code
            )

            final_url = response.url
            domain = get_domain(final_url)

            if not domain:
                continue

            if is_blocked(domain):
                continue

            # 200 = page accessible
            # 301/302 = valid redirect
            # 403 = server exists but blocks bots
            if response.status_code in (200, 301, 302, 403):
                return final_url

        except requests.RequestException:
            continue

    # ---------------------------------------------------------
    # If direct paths fail, inspect homepage
    # ---------------------------------------------------------

    try:
        response = requests.get(
            website_url,
            headers=HEADERS,
            timeout=15,
            allow_redirects=True,
        )

        if response.status_code < 400:

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            candidates = []

            for link in soup.find_all("a", href=True):

                text = " ".join(
                    link.stripped_strings
                ).lower()

                href = link.get(
                    "href",
                    ""
                ).strip()

                if not href:
                    continue

                combined = (
                    f"{text} {href.lower()}"
                )

                if not any(
                    keyword in combined
                    for keyword in CAREERS_WORDS
                ):
                    continue

                absolute_url = urljoin(
                    response.url,
                    href
                )

                if not absolute_url.startswith(
                    ("http://", "https://")
                ):
                    continue

                candidates.append(
                    absolute_url
                )

            if candidates:
                candidates.sort(
                    key=lambda url: (
                        0
                        if any(
                            word in url.lower()
                            for word in (
                                "careers",
                                "career",
                                "jobs",
                                "job",
                            )
                        )
                        else 1,
                        len(url),
                    )
                )

                return candidates[0]

    except requests.RequestException as exc:
        print(
            "HOMEPAGE CAREERS ERROR:",
            exc
        )

    return None

def discover_company(company_name):
    """Discover an official company site and a usable careers/jobs source."""
    normalized = " ".join(company_name.strip().lower().split())
    if not normalized:
        raise ValueError("Company name is required.")

    known_careers = KNOWN_CAREERS.get(normalized)
    if known_careers:
        known_domain = get_domain(known_careers)
        known_website = KNOWN_DOMAINS.get(normalized, known_careers)
        return {
            "name": company_name.strip(),
            "website_url": known_website,
            "domain": known_domain,
            "careers_url": known_careers,
        }

    website_url = search_official_website(company_name)
    if not website_url:
        raise RuntimeError("Could not discover the official company website.")

    careers_url = find_careers_url(website_url)
    return {
        "name": company_name.strip(),
        "website_url": website_url,
        "domain": get_domain(website_url),
        "careers_url": careers_url,
    }

