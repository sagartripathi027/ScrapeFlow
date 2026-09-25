import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
ACCENTURE_API_URL = (
    "https://accenture.wd103.myworkdayjobs.com"
    "/wday/cxs/accenture/AccentureCareers/jobs"
)

BASE_URL = (
    "https://accenture.wd103.myworkdayjobs.com"
    "/en-US/AccentureCareers"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def clean_text(value):
    if not value:
        return ""
    return BeautifulSoup(value, "html.parser").get_text(" ", strip=True)


def scrape_accenture(page=0, limit=20):
    payload = {
        "appliedFacets": {},
        "limit": limit,
        "offset": page * limit,
        "searchText": "",
    }

    try:
        response = requests.post(
            ACCENTURE_API_URL,
            json=payload,
            headers=HEADERS,
            timeout=30,
        )

        response.raise_for_status()
        data = response.json()

        jobs = data.get("jobPostings") or []

        parsed_jobs = []

        for job in jobs:
            external_path = job.get("externalPath")

            if not external_path:
                continue

            title = job.get("title") or "Accenture Job"
            location = job.get("locationsText") or job.get("location") or ""

            if not location:
                parts = external_path.strip("/").split("/")
                if len(parts) >= 2:
                    location = parts[1].replace("-", " ")
                else:
                    location = "India"

            job_url = BASE_URL + external_path

            parsed_jobs.append(
                {
                    "title": title,
                    "location": location,
                    "description": "",
                    "company": "Accenture",
                    "source": "accenture",
                    "source_url": job_url,
                    "job_type": "Full Time",
                    "experience": "",
                    "skills": "",
                    "external_id": external_path,
                    "posted_date": None,
                }
            )

        print("ACCENTURE JOBS FOUND:", len(parsed_jobs))

        return parsed_jobs

    except (requests.RequestException, ValueError) as exc:
        print("ACCENTURE SCRAPER ERROR:", exc)
        return []