import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

INFOSYS_CAREERS_URL = (
    "https://digitalcareers.infosys.com/infosys/global-careers"
)

BASE_URL = "https://digitalcareers.infosys.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
}


def clean_text(value):
    return " ".join((value or "").split())


def parse_infosys_jobs(html):
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    seen = set()

    for link in soup.find_all("a", href=True):

        href = link.get("href", "").strip()
        text = clean_text(link.get_text(" ", strip=True))

        if "/global-careers/company-job/description/reqid/" not in href:
            continue

        job_url = urljoin(BASE_URL, href)

        if job_url in seen:
            continue

        seen.add(job_url)

        parts = text.split()

        req_id = ""
        for part in parts:
            if part.endswith("BR") and part[:-2].isdigit():
                req_id = part
                break

        # Remove "Apply" from the displayed text
        title_text = text.replace("Apply", "").strip()

        jobs.append({
            "title": title_text,
            "location": "",
            "description": "",
            "company": "Infosys",
            "source": "infosys",
            "source_url": job_url,
            "job_type": "Regular",
            "experience": "",
            "skills": "",
            "external_id": req_id,
        })

    return jobs


def scrape_infosys():
    try:
        response = requests.get(
            INFOSYS_CAREERS_URL,
            headers=HEADERS,
            timeout=30,
        )

        response.raise_for_status()

        jobs = parse_infosys_jobs(response.text)

        print("INFOSYS JOBS FOUND:", len(jobs))

        return jobs

    except requests.RequestException as exc:
        print("INFOSYS SCRAPER ERROR:", exc)
        return []