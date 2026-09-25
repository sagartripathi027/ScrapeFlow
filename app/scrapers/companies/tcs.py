import requests
from datetime import datetime

TCS_API_URL = "https://ibegin.tcsapps.com/candidate/api/v1/jobs/searchJ"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json",
    "Referer": "https://ibegin.tcsapps.com/candidate/",
}


def parse_date(value):
    if not value:
        return None

    for fmt in ("%d-%b-%Y %I:%M:%S %p", "%d-%b-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass

    return None


def build_job_url(job_id):
    if not job_id:
        return "https://ibegin.tcsapps.com/candidate/"

    return f"https://ibegin.tcsapps.com/candidate/#/jobs/{job_id}"


def scrape_tcs(page=1):
    payload = {
        "jobTitle": None,
        "jobCity": None,
        "jobFunction": None,
        "jobExperience": None,
        "jobSkill": None,
        "pageNumber": str(page),
        "userText": "",
        "jobTitleOrder": None,
        "jobCityOrder": None,
        "jobFunctionOrder": None,
        "jobExperienceOrder": None,
        "applyByOrder": None,
        "regular": True,
        "walkin": True,
    }

    try:
        response = requests.post(
            TCS_API_URL,
            json=payload,
            headers=HEADERS,
            timeout=30,
        )
        response.raise_for_status()

        result = response.json()

        if result.get("result") != "Y":
            return []

        data = result.get("data") or {}
        jobs = data.get("jobs") or []

        parsed_jobs = []

        for job in jobs:
            job_id = job.get("id")

            parsed_jobs.append({
                "title": job.get("jobTitle") or "TCS Job",
                "location": job.get("location") or "India",
                "description": "",
                "company": "TCS",
                "source": "tcs",
                "source_url": build_job_url(job_id),
                "job_type": "Walk-in" if job.get("walkin") == "J" else "Regular",
                "experience": job.get("experience") or "",
                "skills": job.get("skills") or "",
                "apply_by": parse_date(job.get("applyByDate")),
                "external_id": job_id,
            })

        return parsed_jobs

    except (requests.RequestException, ValueError):
        return []