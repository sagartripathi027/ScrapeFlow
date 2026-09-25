import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}


SKILLS = [
    # Programming
    "python",
    "java",
    "c++",
    "c#",
    "javascript",
    "typescript",
    "sql",
    "r",
    "matlab",
    "scala",

    # Backend / Web
    "fastapi",
    "flask",
    "django",
    "spring",
    "node.js",
    "nodejs",
    "express",
    "rest api",
    "restful api",
    "api",

    # Frontend
    "html",
    "css",
    "react",
    "angular",
    "vue",
    "bootstrap",

    # Databases
    "mysql",
    "postgresql",
    "mongodb",
    "sqlite",
    "redis",
    "oracle",

    # Cloud / DevOps
    "aws",
    "azure",
    "gcp",
    "docker",
    "kubernetes",
    "linux",
    "git",
    "github",
    "ci/cd",

    # Data / AI
    "machine learning",
    "deep learning",
    "artificial intelligence",
    "data analysis",
    "data analytics",
    "data science",
    "statistics",
    "pandas",
    "numpy",
    "scikit-learn",
    "tensorflow",
    "pytorch",
    "natural language processing",
    "nlp",

    # Finance / Business
    "finance",
    "financial analysis",
    "financial modeling",
    "investment management",
    "portfolio management",
    "quantitative analysis",
    "quantitative research",
    "risk management",
    "capital markets",
    "financial markets",
    "economics",
    "accounting",

    # Tools
    "excel",
    "microsoft excel",
    "powerpoint",
    "microsoft powerpoint",
    "power bi",
    "tableau",
    "jira",
    "confluence",

    # General professional skills
    "analytical skills",
    "analytical thinking",
    "problem solving",
    "problem-solving",
    "communication",
    "written communication",
    "oral communication",
    "research",
    "data visualization",
]

def extract_job_details(job_url):
    """
    Fetch and extract full details from a Greenhouse job page.
    """

    if not job_url:
        return {}

    try:
        response = requests.get(
            job_url,
            headers=HEADERS,
            timeout=20,
            allow_redirects=True,
        )

        print(
            "GREENHOUSE DETAIL:",
            response.status_code,
            job_url,
        )

        if response.status_code != 200:
            return {}

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        # ---------------------------------------------------------
        # 1. Meta description
        # ---------------------------------------------------------
        meta = soup.find(
            "meta",
            attrs={"name": "description"},
        )

        if meta:
            description = meta.get(
                "content",
                "",
            ).strip()

            if len(description) > 300:
                print(
                    "GREENHOUSE DETAIL SOURCE: META DESCRIPTION"
                )

                return {
                    "description": description,
                }

        # ---------------------------------------------------------
        # 2. Open Graph description
        # ---------------------------------------------------------
        og = soup.find(
            "meta",
            attrs={"property": "og:description"},
        )

        if og:
            description = og.get(
                "content",
                "",
            ).strip()

            if len(description) > 300:
                print(
                    "GREENHOUSE DETAIL SOURCE: OG DESCRIPTION"
                )

                return {
                    "description": description,
                }

        # ---------------------------------------------------------
        # 3. Greenhouse page containers
        # ---------------------------------------------------------
        selectors = [
            ".job__description",
            ".job-post",
            ".job-posting",
            ".job-description",
            "[class*='job-description']",
            "[class*='description']",
            "#content",
        ]

        for selector in selectors:

            element = soup.select_one(selector)

            if not element:
                continue

            for tag in element.find_all(
                [
                    "script",
                    "style",
                    "noscript",
                    "svg",
                ]
            ):
                tag.decompose()

            description = element.get_text(
                " ",
                strip=True,
            )

            if len(description) > 300:
                print(
                    "GREENHOUSE DETAIL SOURCE:",
                    selector,
                )

                return {
                    "description": description,
                }

        print(
            "GREENHOUSE DETAIL: NO FULL DESCRIPTION FOUND"
        )

        return {}

    except requests.RequestException as exc:

        print(
            "GREENHOUSE DETAIL ERROR:",
            repr(exc),
        )

        return {}
def extract_job_id(url):
    if not url:
        return None

    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        values = query.get("gh_jid")

        if values:
            return values[0]

    except Exception:
        pass

    return None
def normalize_job_url(url):
    """
    Remove duplicate query parameters and keep one gh_jid.
    """

    if not url:
        return None

    job_id = extract_job_id(url)

    if not job_id:
        return url

    return f"https://careers.aqr.com/jobs?gh_jid={job_id}"


def clean_html(html):
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
        ]
    ):
        tag.decompose()

    text = soup.get_text(" ", strip=True)

    return text or None

def extract_skills(text):

    if not text:
        return None

    text_lower = text.lower()

    found = []

    for skill in SKILLS:

        pattern = (
            r"(?<!\w)"
            + re.escape(skill)
            + r"(?!\w)"
        )

        if re.search(
            pattern,
            text_lower,
        ):
            found.append(skill)

    return ", ".join(found) if found else None


def extract_job_type(text):

    if not text:
        return None

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
        or re.search(r"\bintern\b", text_lower)
    ):
        return "Internship"

    if "contract" in text_lower:
        return "Contract"

    return None


def extract_experience(text):

    if not text:
        return None

    patterns = [
        r"\b\d+\+?\s*(?:years?|yrs?)\b",
        r"\b\d+\s*-\s*\d+\s*(?:years?|yrs?)\b",
    ]

    found = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        for match in matches:

            value = match.strip()

            if value not in found:
                found.append(value)

    return (
        ", ".join(found[:5])
        if found
        else None
    )


def process_job(item, fetch_details=True):

    location = item.get("location")

    if isinstance(location, dict):
        location = location.get("name")

    source_url = item.get("absolute_url")

    source_url = normalize_job_url(
        source_url
    )

    description = None

    if fetch_details and source_url:

        details = extract_job_details(
            source_url
        )

        description = details.get(
            "description"
        )

    return {
        "title": item.get("title")
        or "Untitled Job",

        "location": location,

        "job_type": extract_job_type(
            description
        ),

        "experience": extract_experience(
            description
        ),

        "shift": None,

        "description": description,

        "skills": extract_skills(
            description
        ),

        "source_url": source_url,

        "source": "greenhouse",

        "posted_date": None,
    }


def fetch_greenhouse_jobs(
    board_url,
    fetch_details=True,
):

    if not board_url:
        return []

    clean_board_url = board_url.rstrip("/")

    parts = clean_board_url.split("/")

    if not parts:
        return []

    token = parts[-1].split("?")[0]

    if not token:
        print(
            "GREENHOUSE: Could not extract board token"
        )
        return []

    api_url = (
        "https://boards-api.greenhouse.io/"
        f"v1/boards/{token}/jobs"
    )

    print(
        "GREENHOUSE API:",
        api_url,
    )

    try:

        response = requests.get(
            api_url,
            headers=HEADERS,
            timeout=20,
        )

        print(
            "GREENHOUSE STATUS:",
            response.status_code,
        )

        if response.status_code != 200:

            print(
                "GREENHOUSE ERROR:",
                response.text[:300],
            )

            return []

        data = response.json()

    except (
        requests.RequestException,
        ValueError,
    ) as exc:

        print(
            "GREENHOUSE FETCH ERROR:",
            repr(exc),
        )

        return []

    items = data.get(
        "jobs",
        [],
    )

    print(
        "GREENHOUSE JOB LIST:",
        len(items),
    )

    if not fetch_details:

        return [
            process_job(
                item,
                fetch_details=False,
            )
            for item in items
        ]

    jobs = []

    # Fetch job pages concurrently.
    max_workers = min(
        8,
        max(1, len(items)),
    )

    with ThreadPoolExecutor(
        max_workers=max_workers
    ) as executor:

        futures = {
            executor.submit(
                process_job,
                item,
                True,
            ): item
            for item in items
        }

        for future in as_completed(
            futures
        ):

            item = futures[future]

            try:

                job = future.result()

                jobs.append(job)

            except Exception as exc:

                print(
                    "GREENHOUSE JOB ERROR:",
                    item.get("title"),
                    repr(exc),
                )

                # Keep the job even if details fail.
                jobs.append(
                    process_job(
                        item,
                        fetch_details=False,
                    )
                )

    # Keep API order.
    order = {
        item.get("absolute_url"): index
        for index, item in enumerate(items)
    }

    jobs.sort(
        key=lambda job: order.get(
            job.get("source_url"),
            999999,
        )
    )

    print(
        "GREENHOUSE JOBS FOUND:",
        len(jobs),
    )

    return jobs