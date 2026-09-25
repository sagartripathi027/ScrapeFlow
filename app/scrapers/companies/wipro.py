import requests
from bs4 import BeautifulSoup
from urllib.parse import quote


API_URL = "https://careers.wipro.com/services/recruiting/v1/jobs"
BASE_URL = "https://careers.wipro.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def clean_text(value):
    if not value:
        return ""

    return BeautifulSoup(str(value), "html.parser").get_text(
        " ", strip=True
    )


def build_job_url(job):
    response = job.get("response", {})

    job_id = response.get("id")
    title = response.get("unifiedStandardTitle")

    if not job_id or not title:
        return ""

    return (
        f"{BASE_URL}/job/{quote(title)}/{job_id}-en_US/"
    )

def fetch_job_details(url):
    if not url:
        return "", ""

    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": HEADERS["User-Agent"],
                "Accept": "text/html",
            },
            timeout=30,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        description = ""
        skills = []

        # Job Description section
        description_heading = soup.find(
            string=lambda s: s and "Job Description" in s
        )

        if description_heading:
            parent = description_heading.parent
            description = parent.parent.get_text(
                " ", strip=True
            ) if parent.parent else ""

        # Key Skills section
        skills_heading = soup.find(
            string=lambda s: s and "Key Skills" in s
        )

        if skills_heading:
            section = skills_heading.parent

            # Get only list items after Key Skills
            container = section.parent if section.parent else section

            for li in container.find_all("li"):
                text = li.get_text(" ", strip=True)
                if text:
                    skills.append(text)

        return description.strip(), ", ".join(skills)

    except requests.RequestException as exc:
        print("WIPRO DETAIL ERROR:", exc)
        return "", ""
def parse_job(job):
    response = job.get("response", {})

    title = response.get("unifiedStandardTitle", "").strip()

    locations = response.get("jobLocationShort") or []

    location = ""
    if locations:
        location = clean_text(locations[0])

    country = ""
    countries = response.get("jobLocationCountry") or []
    if countries:
        country = countries[0]

    state = ""
    states = response.get("jobLocationState") or []
    if states:
        state = states[0]

    if not location:
        parts = [x for x in [state, country] if x]
        location = ", ".join(parts)

    job_id = response.get("id")
    
    source_url = build_job_url(job)
    description, skills = fetch_job_details(source_url)

    return {
        "title": title or "Wipro Job",
        "location": location,
        "description": description,
        "company": "Wipro",
        "source": "wipro",
        "source_url": build_job_url(job),
        "job_type": "Full Time",
        "experience": "",
        "skills": skills,
        "external_id": str(job_id) if job_id else "",
        "posted_date": None,
    }


def scrape_wipro(
    keywords="",
    location="",
    max_pages=3,
    page_size=50,
):
    jobs = []

    for page in range(max_pages):
        payload = {
            "keywords": keywords,
            "locale": "en_US",
            "location": location,
            "pageNumber": page,
            "sortBy": "recent",
        }

        try:
            response = requests.post(
                API_URL,
                json=payload,
                headers=HEADERS,
                timeout=30,
            )

            response.raise_for_status()

            data = response.json()
            results = data.get("jobSearchResult") or []

            if not results:
                break

            print(
                f"WIPRO PAGE {page + 1}: "
                f"{len(results)} jobs"
            )

            for item in results:
                job = parse_job(item)

                if job["title"] and job["source_url"]:
                    jobs.append(job)

            if len(results) < page_size:
                break

        except (requests.RequestException, ValueError) as exc:
            print("WIPRO SCRAPER ERROR:", exc)
            break

    unique_jobs = []
    seen = set()

    for job in jobs:
        key = job["source_url"] or job["external_id"]

        if key and key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    print("WIPRO JOBS FOUND:", len(unique_jobs))

    return unique_jobs