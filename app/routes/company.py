from flask import Blueprint, request, jsonify
from app import db
from app.models.company import Company
from app.models.job import Job
from app.scrapers.companies.tcs import scrape_tcs
from app.scrapers.companies.infosys import scrape_infosys
from app.scrapers.companies.accenture import scrape_accenture
from app.scrapers.companies.wipro import scrape_wipro
from app.services.company_finder import discover_company
from app.services.ats_detector import discover_ats
from app.services.greenhouse import fetch_greenhouse_jobs
from app.scrapers.job_scraper import scrape_jobs


company_bp = Blueprint("company", __name__)


def get_jobs_from_source(careers_url, company_name):
    """
    Select the best available public job source.

    ATS sources are preferred over direct website scraping.
    """

    ats = discover_ats(careers_url)

    if ats:
        ats_name = ats["ats"]

        print("JOB SOURCE:", ats_name)

        if ats_name == "greenhouse":
            return fetch_greenhouse_jobs(
                ats["url"],
                fetch_details=True,
            ), ats_name

        print(
            "ATS detected but scraper is not implemented yet:",
            ats_name,
        )

    # No supported ATS detected.
    # Fall back to the normal scraper.
    print("JOB SOURCE: normal website scraper")

    company_key = company_name.strip().lower()

    if company_key == "tcs":
        jobs = scrape_tcs()
    elif company_key == "infosys":
        jobs = scrape_infosys()
    elif company_key == "accenture":
        jobs = scrape_accenture()
    elif company_key == "wipro":
        jobs = scrape_wipro()
    else:
        jobs = scrape_jobs(careers_url, company_name)

    return jobs, "website"


@company_bp.route("/api/company/discover", methods=["POST"])
def discover():

    data = request.get_json(silent=True) or {}

    print("DEBUG REQUEST DATA:", data)

    company_name = (
        data.get("company")
        or data.get("company_name")
        or data.get("name")
        or ""
    ).strip()

    if not company_name:
        return jsonify({
            "success": False,
            "error": "Company name is required",
        }), 400

    try:

        # ---------------------------------------------------------
        # 1. Discover official company website
        # ---------------------------------------------------------

        result = discover_company(company_name)

        if not result:
            return jsonify({
                "success": False,
                "error": "Could not discover company website",
            }), 404

        # ---------------------------------------------------------
        # 2. Save / update company
        # ---------------------------------------------------------

        company = Company.query.filter(
            db.func.lower(Company.name) == company_name.lower()
        ).first()

        if not company:
            company = Company(name=company_name)
            db.session.add(company)

        company.domain = result.get("domain")
        company.website_url = result.get("website_url")
        company.careers_url = result.get("careers_url")

        db.session.commit()

        # ---------------------------------------------------------
        # 3. Find jobs
        # ---------------------------------------------------------

        jobs = []
        source_type = "none"

        if company.careers_url:

            jobs, source_type = get_jobs_from_source(
                company.careers_url,
                company.name,
            )

        # ---------------------------------------------------------
        # 4. Save jobs
        # ---------------------------------------------------------

        saved_jobs = []

        for job_data in jobs:

            source_url = job_data.get("source_url")

            if not source_url:
                continue

            existing_job = Job.query.filter_by(
                source_url=source_url
            ).first()

            if existing_job:

                job = existing_job

            else:

                job = Job(
                    company_id=company.id,
                    source_url=source_url,
                )

                db.session.add(job)

            job.company_id = company.id

            job.title = (
                job_data.get("title")
                or "Untitled Job"
            )

            job.location = job_data.get("location")
            job.job_type = job_data.get("job_type")
            job.experience = job_data.get("experience")
            job.shift = job_data.get("shift")
            job.description = job_data.get("description")
            job.skills = job_data.get("skills")

            job.source = (
                job_data.get("source")
                or source_type
            )

            job.posted_date = job_data.get("posted_date")

            saved_jobs.append(job)

        db.session.commit()

        # ---------------------------------------------------------
        # 5. Response
        # ---------------------------------------------------------

        return jsonify({
            "success": True,

            "company": company.to_dict(),

            "careers_url": company.careers_url,

            "source": source_type,

            "jobs_found": len(saved_jobs),

            "jobs": [
                job.to_dict()
                for job in saved_jobs
            ],
        })

    except Exception as e:

        db.session.rollback()

        print(
            "COMPANY DISCOVERY ERROR:",
            repr(e),
        )

        return jsonify({
            "success": False,
            "error": str(e),
        }), 500