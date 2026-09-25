import json
import re

from datetime import datetime
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

MAX_CRAWL_PAGES = 20

JOB_KEYWORDS = (
    "job",
    "jobs",
    "career",
    "careers",
    "opening",
    "position",
    "vacancy",
    "opportunity",
    "employment",
)

BLOCK_PAGE_MARKERS = (
    "access denied",
    "request blocked",
    "forbidden",
    "errors.edgesuite.net",
    "akamai",
    "bot detection",
    "captcha",
)


# ============================================================
# GOOGLE CAREERS RULES
# ============================================================

# Real Google job detail path:
# /about/careers/applications/jobs/results/<job-id>-<slug>
GOOGLE_JOB_PATH_RE = re.compile(
    r"^/about/careers/applications/jobs/results/"
    r"\d+(?:-[A-Za-z0-9][A-Za-z0-9_-]*)?/?$",
    re.IGNORECASE,
)

GOOGLE_JOB_LISTING_HOSTS = (
    "google.com",
)

SKIP_URL_EXTENSIONS = (
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".zip",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".mp4",
    ".css",
    ".js",
)

NON_JOB_URL_MARKERS = (
    "know-your-rights",
    "eeoc",
    "eeo",
    "self-identification",
    "privacy",
    "terms",
    "legal",
    "cookie",
    "help",
    "support",
    "faq",
    "/students",
    "/teams",
    "/how-we-hire",
    "/saved",
    "saved-jobs",
    "job-alert",
    "alerts",
    "dashboard",
    "signin",
    "sign-in",
    "login",
    "profile",
    "account",
    "applications/support",
)


# ============================================================
# URL HELPERS
# ============================================================

def normalize_url(url):
    """
    Remove fragments and common tracking parameters.

    Also repairs the specific malformed Google Careers URL:
    /jobs/jobs/results/... -> /jobs/results/...

    Existing URLs from Microsoft/Amazon are otherwise preserved.
    """
    if not url:
        return ""

    parsed = urlparse(url)

    path = parsed.path

    # Google-specific repair only.
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    if (
        host == "google.com"
        and "/about/careers/applications/jobs/jobs/results/" in path
    ):
        path = path.replace(
            "/about/careers/applications/jobs/jobs/results/",
            "/about/careers/applications/jobs/results/",
            1,
        )

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            path.rstrip("/") or "/",
            "",
            "",
            "",
        )
    )


def is_asset_url(url):
    """PDFs, images, docs, etc. are never job postings."""
    if not url:
        return True

    path = urlparse(url).path.lower()

    return path.endswith(SKIP_URL_EXTENSIONS)


def is_non_job_url(url):
    """Legal, navigation, dashboard and account pages."""
    if not url:
        return True

    url_lower = url.lower()

    return any(
        marker in url_lower
        for marker in NON_JOB_URL_MARKERS
    )


def is_google_host(url):
    """Check whether a URL belongs to Google."""
    if not url:
        return False

    host = urlparse(url).netloc.lower()

    if host.startswith("www."):
        host = host[4:]

    return (
        host == "google.com"
        or host.endswith(".google.com")
    )
    
def is_google_job_url(url):
    """True only for real Google job detail URLs."""
    if not url:
        return False

    parsed = urlparse(url)

    host = parsed.netloc.lower()

    if host.startswith("www."):
        host = host[4:]

    if host not in GOOGLE_JOB_LISTING_HOSTS:
        return False

    return bool(
        GOOGLE_JOB_PATH_RE.search(parsed.path)
    )


def is_block_page(html):
    """Detect common access-denied/block responses."""
    if not html:
        return True

    sample = html[:10000].lower()

    return any(
        marker in sample
        for marker in BLOCK_PAGE_MARKERS
    )


# ============================================================
# FETCHING
# ============================================================

def fetch_page_requests(url):
    """Try normal HTTP requests first."""
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15,
            allow_redirects=True,
        )

        print(
            "REQUESTS:",
            response.status_code,
            "->",
            response.url,
        )

        if response.status_code >= 400:
            return None

        if is_block_page(response.text):
            print("REQUESTS: Block page detected")
            return None

        return response.text

    except requests.RequestException as exc:
        print(
            "REQUESTS ERROR:",
            repr(exc),
        )

        return None


def fetch_page_playwright(url):
    """
    Render a publicly accessible page using Chromium.

    This is a browser fallback for JavaScript-rendered pages
    or pages that do not return useful HTML through requests.
    """
    if sync_playwright is None:
        print("PLAYWRIGHT: Not installed")
        return None

    try:
        print(
            "PLAYWRIGHT: Opening",
            url,
        )

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True
            )

            page = browser.new_page(
                user_agent=HEADERS["User-Agent"],
                viewport={
                    "width": 1440,
                    "height": 900,
                },
            )

            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            status = (
                response.status
                if response
                else None
            )

            print(
                "PLAYWRIGHT STATUS:",
                status,
                "URL:",
                page.url,
            )

            # Give client-side JavaScript a short time to render.
            page.wait_for_timeout(2000)

            html = page.content()

            browser.close()

            if not html:
                return None

            if is_block_page(html):
                print(
                    "PLAYWRIGHT: Page still appears blocked"
                )
                return None

            return html

    except Exception as exc:
        print(
            "PLAYWRIGHT ERROR:",
            repr(exc),
        )

        return None


def fetch_page(url):
    """
    Fetch page using Requests first.

    If Requests returns HTML but the page contains
    no detectable jobs and no useful links, assume the
    page may be JavaScript-rendered and try Playwright.
    """
    html = fetch_page_requests(url)

    if html:
        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        json_jobs = parse_json_ld(
            soup,
            url,
        )

        google_jobs = parse_google_jobs(
            soup,
            url,
        )

        generic_jobs = parse_generic_jobs(
            soup,
            url,
        )

        links = get_page_links(
            soup,
            url,
        )

        # Requests got HTML, but it looks like a JS shell.
        if (
            not json_jobs
            and not google_jobs
            and not generic_jobs
            and not links
        ):
            print(
                "REQUESTS: HTML received but no jobs/links found"
            )

            print(
                "FALLBACK: Trying Playwright for",
                url,
            )

            playwright_html = fetch_page_playwright(
                url
            )

            if playwright_html:
                return playwright_html

        return html

    print(
        "FALLBACK: Trying Playwright for",
        url,
    )

    return fetch_page_playwright(url)


# ============================================================
# TEXT / FIELD EXTRACTION
# ============================================================

def clean_text(text):
    if not text:
        return ""

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def extract_skills(text):
    skills = [
        "python",
        "java",
        "javascript",
        "typescript",
        "react",
        "angular",
        "vue",
        "node.js",
        "flask",
        "fastapi",
        "django",
        "sql",
        "mysql",
        "postgresql",
        "mongodb",
        "aws",
        "azure",
        "gcp",
        "docker",
        "kubernetes",
        "git",
        "github",
        "linux",
        "html",
        "css",
        "machine learning",
        "deep learning",
        "artificial intelligence",
        "data science",
        "pandas",
        "numpy",
        "tensorflow",
        "pytorch",
        "spark",
        "rest api",
    ]

    text_lower = text.lower()

    found = []

    for skill in skills:
        if skill in text_lower:
            found.append(skill)

    return ", ".join(found)


def extract_location(text):
    patterns = [
        r"location\s*[:\-]\s*([^|;\n]+)",
        r"locations?\s*[:\-]\s*([^|;\n]+)",
        r"based in\s*[:\-]?\s*([^|;\n]+)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            return clean_text(
                match.group(1)
            )[:500]

    return None


def extract_job_type(text):
    text_lower = text.lower()

    if (
        "full-time" in text_lower
        or "full time" in text_lower
    ):
        return "Full-time"

    if (
        "part-time" in text_lower
        or "part time" in text_lower
    ):
        return "Part-time"

    if (
        "internship" in text_lower
        or "intern" in text_lower
    ):
        return "Internship"

    if "contract" in text_lower:
        return "Contract"

    return None


def extract_experience(text):
    patterns = [
        r"(\d+\s*(?:-|\bto\b)\s*\d+\s*years?)",
        r"(\d+\+?\s*years?)\s*(?:of)?\s*experience",
        r"experience\s*[:\-]\s*([^.;]+)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            return clean_text(
                match.group(1)
            )[:200]

    return None


def extract_posted_date(text):
    patterns = [
        (
            r"posted\s*(?:on)?\s*[:\-]?\s*"
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
        ),
        r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            value = match.group(1)

            for fmt in (
                "%d/%m/%Y",
                "%d-%m-%Y",
                "%Y/%m/%d",
                "%Y-%m-%d",
            ):
                try:
                    return datetime.strptime(
                        value,
                        fmt,
                    )
                except ValueError:
                    pass

    return None


# ============================================================
# JSON-LD PARSER
# ============================================================

def parse_location_data(location_data):
    """Handle JSON-LD jobLocation as dict or list."""
    if not location_data:
        return None

    if isinstance(location_data, dict):
        location_data = [location_data]

    if not isinstance(location_data, list):
        return None

    locations = []

    for location in location_data:
        if not isinstance(location, dict):
            continue

        address = location.get(
            "address",
            {},
        )

        if not isinstance(address, dict):
            continue

        parts = [
            address.get("addressLocality"),
            address.get("addressRegion"),
            address.get("addressCountry"),
        ]

        value = ", ".join(
            str(part)
            for part in parts
            if part
        )

        if value:
            locations.append(value)

    if locations:
        return " | ".join(
            dict.fromkeys(locations)
        )

    return None


def parse_json_ld(soup, page_url):
    jobs = []

    scripts = soup.find_all(
        "script",
        type="application/ld+json",
    )

    for script in scripts:
        try:
            raw = (
                script.string
                or script.get_text()
            )

            data = json.loads(raw)

        except (
            json.JSONDecodeError,
            TypeError,
        ):
            continue

        items = []

        if isinstance(data, list):
            items.extend(data)

        elif isinstance(data, dict):
            items.append(data)

            # Some sites store JobPosting inside @graph.
            graph = data.get("@graph")

            if isinstance(graph, list):
                items.extend(graph)

        for item in items:
            if not isinstance(item, dict):
                continue

            item_type = item.get("@type")

            if isinstance(item_type, list):
                is_job = (
                    "JobPosting"
                    in item_type
                )
            else:
                is_job = (
                    item_type
                    == "JobPosting"
                )

            if not is_job:
                continue

            title = clean_text(
                item.get(
                    "title",
                    "",
                )
            )

            description_html = item.get(
                "description",
                "",
            )

            description = clean_text(
                BeautifulSoup(
                    description_html,
                    "html.parser",
                ).get_text(" "),
            )

            source_url = item.get("url")

            if source_url:
                source_url = urljoin(
                    page_url,
                    source_url,
                )
            else:
                source_url = page_url

            source_url = normalize_url(
                source_url
            )

            location = parse_location_data(
                item.get("jobLocation")
            )

            if not location:
                location_type = item.get(
                    "jobLocationType"
                )

                if location_type:
                    location = clean_text(
                        str(location_type)
                    )

            posted_date = None

            date_value = item.get(
                "datePosted"
            )

            if date_value:
                try:
                    posted_date = (
                        datetime.fromisoformat(
                            str(date_value).replace(
                                "Z",
                                "+00:00",
                            )
                        )
                        .replace(tzinfo=None)
                    )

                except ValueError:
                    posted_date = None

            skills_text = " ".join(
                [
                    title,
                    description,
                    str(
                        item.get(
                            "skills",
                            "",
                        )
                    ),
                    str(
                        item.get(
                            "qualifications",
                            "",
                        )
                    ),
                ]
            )

            jobs.append(
                {
                    "title": title,
                    "location": location,
                    "job_type": item.get(
                        "employmentType"
                    ),
                    "experience": (
                        extract_experience(
                            description
                        )
                    ),
                    "shift": None,
                    "description": description,
                    "skills": extract_skills(
                        skills_text
                    ),
                    "source_url": source_url,
                    "source": "json-ld",
                    "posted_date": posted_date,
                }
            )

    return jobs


# ============================================================
# GOOGLE CAREERS PARSER
# ============================================================

def parse_google_jobs(soup, page_url):
    """
    Extract Google Careers jobs.

    Google job URL pattern:
    /about/careers/applications/jobs/results/<job-id>-<slug>
    """
    jobs = []

    for link in soup.find_all("a", href=True):
        href = link.get("href")
        if not href:
            continue

        absolute_url = urljoin(page_url, href)

        if not absolute_url.startswith(("http://", "https://")):
            continue

        normalized_url = normalize_url(absolute_url)

        if not is_google_job_url(normalized_url):
            continue

        if is_asset_url(normalized_url):
            continue

        if is_non_job_url(normalized_url):
            continue

        # Find the surrounding Google job card
        card = link

        for _ in range(8):
            if card.parent is None:
                break

            card = card.parent

            if card.name in ("li", "article", "div"):
                card_text_temp = clean_text(
                    card.get_text(" ", strip=True)
                )

                if len(card_text_temp) >= 20 and (
                    card.find(["h1", "h2", "h3", "h4"])
                    or "place" in card_text_temp.lower()
                    or "location" in card_text_temp.lower()
                ):
                    break

        # -----------------------------
        # TITLE
        # -----------------------------
        title = ""

        heading = card.find(
            ["h1", "h2", "h3", "h4"]
        )

        if heading:
            title = clean_text(
                heading.get_text(" ", strip=True)
            )

        if not title or title.lower() == "see details":
            title = clean_text(
                link.get_text(" ", strip=True)
            )

        if (
            not title
            or title.lower() == "see details"
            or len(title) < 4
        ):
            continue

        # -----------------------------
        # CARD TEXT
        # -----------------------------
        card_text = clean_text(
            card.get_text(" ", strip=True)
        )

        # -----------------------------
        # LOCATION
        # -----------------------------
        location = extract_location(card_text)

        # Google-specific location format:
        #
        # place Mountain View, CA, USA bar_chart
        # place Dublin, Ireland bar_chart
        # place New York, NY, USA ; +2 more bar_chart
        #
        if not location:
            google_location_match = re.search(
                r"\bplace\s+(.+?)(?=\s+bar_chart\b|\s+Minimum qualifications\b|\s+Preferred qualifications\b|\s+Learn more\b|$)",
                card_text,
                re.IGNORECASE,
            )

            if google_location_match:
                location = clean_text(
                    google_location_match.group(1)
                )

        # -----------------------------
        # LOCATION ELEMENT FALLBACK
        # -----------------------------
        if not location:
            for element in card.find_all(True):
                classes = " ".join(
                    element.get("class", [])
                ).lower()

                aria_label = str(
                    element.get("aria-label", "")
                ).lower()

                if (
                    "location" in classes
                    or "location" in aria_label
                ):
                    candidate = clean_text(
                        element.get_text(
                            " ",
                            strip=True,
                        )
                    )

                    if (
                        candidate
                        and len(candidate) < 300
                    ):
                        location = candidate
                        break

        # -----------------------------
        # OTHER FIELDS
        # -----------------------------
        description = card_text[:2000]

        jobs.append(
            {
                "title": title,
                "location": location,
                "job_type": extract_job_type(
                    card_text
                ),
                "experience": extract_experience(
                    card_text
                ),
                "shift": None,
                "description": description,
                "skills": extract_skills(
                    f"{title} {description}"
                ),
                "source_url": normalized_url,
                "source": "google_careers",
                "posted_date": extract_posted_date(
                    card_text
                ),
            }
        )

    return jobs
# ============================================================
# GENERIC JOB PARSER
# ============================================================

def is_likely_job_link(title, href):
    combined = (
        f"{title} {href}"
    ).lower()

    return any(
        keyword in combined
        for keyword in JOB_KEYWORDS
    )


def parse_generic_jobs(soup, page_url):
    """
    Extract likely job-posting links.

    Supports:
    - Microsoft Careers job cards
    - Generic career/job posting links

    Google-specific jobs are handled separately by
    parse_google_jobs().
    """
    jobs = []

    # ========================================================
    # 1. MICROSOFT CAREERS JOB CARDS
    # ========================================================

    microsoft_cards = soup.select(
        "div.careers-joblistResponsive-columnList"
    )

    for card in microsoft_cards:
        title_el = card.select_one(
            "h3.careers-joblistResponsive-subheading"
        )

        date_el = card.select_one(
            ".careers-joblistResponsive-postdate"
        )

        location_el = card.select_one(
            ".careers-joblistResponsive-primarylocation"
        )

        description_el = card.select_one(
            ".careers-joblistResponsive-desc"
        )

        link_el = card.select_one(
            "a.careers-joblistResponsive-button[href]"
        )

        if not title_el or not link_el:
            continue

        title = clean_text(
            title_el.get_text(
                " ",
                strip=True,
            )
        )

        href = link_el.get("href")

        if not title or not href:
            continue

        absolute_url = urljoin(
            page_url,
            href,
        )

        if not absolute_url.startswith(
            ("http://", "https://")
        ):
            continue

        normalized_url = normalize_url(
            absolute_url
        )

        posted_date = None

        if date_el:
            posted_date = clean_text(
                date_el.get_text(
                    " ",
                    strip=True,
                )
            )

        location = None

        if location_el:
            location = clean_text(
                location_el.get_text(
                    " ",
                    strip=True,
                )
            )

        description = ""

        if description_el:
            description = clean_text(
                description_el.get_text(
                    " ",
                    strip=True,
                )
            )

        jobs.append(
            {
                "title": title,
                "location": location,
                "job_type": None,
                "experience": None,
                "shift": None,
                "description": description,
                "skills": extract_skills(
                    f"{title} {description}"
                ),
                "source_url": normalized_url,
                "source": "microsoft_careers",
                "posted_date": posted_date,
            }
        )

    # ========================================================
    # 2. GENERIC JOB POSTING LINKS
    # ========================================================

    NON_JOB_WORDS = (
        "about",
        "academy",
        "benefits",
        "culture",
        "diversity",
        "inclusion",
        "hiring-tips",
        "locations",
        "location",
        "professions",
        "programs",
        "students",
        "military",
        "accessibility",
        "explore",
        "life-at",
        "recentgraduate",
        "university",
        "internship-program",
    )

    JOB_URL_PATTERNS = (
        "/job/",
        "/jobs/",
        "/job?",
        "/jobs?",
        "jobid=",
        "job-id=",
        "job_id=",
        "gh_jid=",
        "lever.co/",
        "ashbyhq.com/",
    )

    for link in soup.find_all(
        "a",
        href=True,
    ):
        title = clean_text(
            link.get_text(
                " ",
                strip=True,
            )
        )

        href = link.get("href")

        if not title or not href:
            continue

        if len(title) < 4 or len(title) > 300:
            continue

        absolute_url = urljoin(
            page_url,
            href,
        )

        if not absolute_url.startswith(
            ("http://", "https://")
        ):
            continue

        normalized_url = normalize_url(
            absolute_url
        )

        # Never treat assets as jobs.
        if is_asset_url(
            normalized_url
        ):
            continue

        # Never treat known non-job pages as jobs.
        if is_non_job_url(
            normalized_url
        ):
            continue

        # Google job detail URLs are handled
        # by parse_google_jobs().
        if is_google_job_url(
            normalized_url
        ):
            continue

        # Don't add Microsoft "See details"
        # links again.
        if link.select_one(
            ".careers-joblistResponsive-button-text"
        ):
            continue

        combined = (
            f"{title} {normalized_url}"
        ).lower()

        if any(
            word in combined
            for word in NON_JOB_WORDS
        ):
            continue

        if not any(
            pattern in normalized_url.lower()
            for pattern in JOB_URL_PATTERNS
        ):
            continue

        jobs.append(
            {
                "title": title,
                "location": None,
                "job_type": None,
                "experience": None,
                "shift": None,
                "description": "",
                "skills": extract_skills(
                    title
                ),
                "source_url": normalized_url,
                "source": "career_page",
                "posted_date": None,
            }
        )

    return jobs


# ============================================================
# LINK HANDLING
# ============================================================

def same_domain(url1, url2):
    domain1 = urlparse(
        url1
    ).netloc.lower()

    domain2 = urlparse(
        url2
    ).netloc.lower()

    if domain1.startswith("www."):
        domain1 = domain1[4:]

    if domain2.startswith("www."):
        domain2 = domain2[4:]

    return domain1 == domain2


def get_page_links(soup, page_url):
    links = []

    for link in soup.find_all(
        "a",
        href=True,
    ):
        href = link.get("href")

        if not href:
            continue

        absolute_url = urljoin(
            page_url,
            href,
        )

        if not absolute_url.startswith(
            ("http://", "https://")
        ):
            continue

        absolute_url = normalize_url(
            absolute_url
        )

        # Do not crawl files/assets.
        if is_asset_url(
            absolute_url
        ):
            continue

        # Do not crawl obvious non-job pages.
        if is_non_job_url(
            absolute_url
        ):
            continue

        # Google detail pages are parsed directly
        # from the listing page, so don't crawl them.
        if is_google_job_url(
            absolute_url
        ):
            continue

        if same_domain(
            page_url,
            absolute_url,
        ):
            links.append(
                absolute_url
            )

    return list(
        dict.fromkeys(links)
    )


# ============================================================
# SINGLE PAGE SCRAPER
# ============================================================

def scrape_single_page(url):
    print(
        "\nSCRAPING:",
        url,
    )

    html = fetch_page(url)

    if not html:
        print(
            "NO USABLE HTML:",
            url,
        )

        return [], []

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    json_jobs = parse_json_ld(
        soup,
        url,
    )

    # Google-specific parser.
    google_jobs = parse_google_jobs(
        soup,
        url,
    )

    # Existing Microsoft + generic parser.
    generic_jobs = parse_generic_jobs(
        soup,
        url,
    )

    # Google first so deduplication keeps
    # the richer Google record.
    jobs = (
        json_jobs
        + google_jobs
        + generic_jobs
    )

    links = get_page_links(
        soup,
        url,
    )

    print(
        "PAGE RESULT:",
        len(jobs),
        "job candidates,",
        len(links),
        "links",
    )

    return jobs, links


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate_jobs(jobs):
    unique = {}

    seen_titles = set()

    for job in jobs:
        source_url = job.get(
            "source_url"
        )

        if source_url:
            key = normalize_url(
                source_url
            ).lower()

        else:
            key = (
                job.get(
                    "title",
                    "",
                )
                .lower()
                .strip()
                + "|"
                + str(
                    job.get(
                        "location",
                        "",
                    )
                )
                .lower()
                .strip()
            )

        if key in unique:
            continue

        title_key = (
            job.get(
                "title",
                "",
            )
            .lower()
            .strip(),
            str(
                job.get(
                    "location",
                    "",
                )
            )
            .lower()
            .strip(),
        )

        if title_key in seen_titles:
            continue

        seen_titles.add(
            title_key
        )

        unique[key] = job

    return list(
        unique.values()
    )


# ============================================================
# CRAWL RULES
# ============================================================

def should_follow_link(link):
    if not link:
        return False

    # Never crawl assets.
    if is_asset_url(link):
        return False

    # Google-specific crawl rules.
    #
    # Google job detail pages are already parsed
    # directly from the listing page.
    if is_google_host(link):

        if is_google_job_url(link):
            return False

        # Do not follow Google navigation,
        # recommendations, AI, Cloud, YouTube,
        # jobs/jobs and other non-job pages.
        if is_non_job_url(link):
            return False

        path = urlparse(link).path.lower()

        google_allowed_paths = (
            "/about/careers/applications/jobs/results",
        )

        # Only continue crawling Google job-result pages.
        if not any(
            path.startswith(prefix)
            for prefix in google_allowed_paths
        ):
            return False

        return True

    # Existing Microsoft/Amazon/generic behavior.
    if is_non_job_url(link):
        return False

    return any(
        keyword in link.lower()
        for keyword in JOB_KEYWORDS
    )


# ============================================================
# MAIN SCRAPER
# ============================================================

def scrape_jobs(
    careers_url,
    company_name=None,
):
    """
    Scrape publicly accessible job pages
    from a careers URL.

    Requests is tried first.
    Playwright is used as a browser fallback
    when the page is blocked or requires rendering.
    """
    if not careers_url:
        return []

    careers_url = normalize_url(
        careers_url
    )

    visited = set()

    queue = [
        careers_url
    ]

    all_jobs = []

    while (
        queue
        and len(visited) < MAX_CRAWL_PAGES
    ):
        url = queue.pop(0)

        url = normalize_url(
            url
        )

        if not url:
            continue

        if url in visited:
            continue

        visited.add(url)

        jobs, links = scrape_single_page(
            url
        )

        all_jobs.extend(
            jobs
        )

        for link in links:
            link = normalize_url(
                link
            )

            if not link:
                continue

            if link in visited:
                continue

            if not same_domain(
                careers_url,
                link,
            ):
                continue

            if should_follow_link(
                link
            ):
                queue.append(
                    link
                )

        # Keep crawl bounded.
        if len(queue) > MAX_CRAWL_PAGES:
            queue = queue[
                :MAX_CRAWL_PAGES
            ]

    jobs = deduplicate_jobs(
        all_jobs
    )

    for job in jobs:
        if not job.get(
            "source_url"
        ):
            job["source_url"] = (
                careers_url
            )

    print(
        "\n========== SCRAPER SUMMARY =========="
    )

    print(
        "Company:",
        company_name or "Unknown",
    )

    print(
        "Pages visited:",
        len(visited),
    )

    print(
        "Raw jobs:",
        len(all_jobs),
    )

    print(
        "Unique jobs:",
        len(jobs),
    )

    print(
        "======================================"
    )

    return jobs