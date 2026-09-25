from flask import Blueprint, request, jsonify, render_template

from app import db
from app.models.job import Job
from app.models.company import Company


jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.route("/api/jobs", methods=["GET"])
def get_jobs():
    query = Job.query

    company = request.args.get("company")
    location = request.args.get("location")
    job_type = request.args.get("job_type")
    experience = request.args.get("experience")
    skill = request.args.get("skill")
    search = request.args.get("search")

    # Company filter
    if company:
        try:
            company_id = int(company)
            query = query.filter(Job.company_id == company_id)
        except ValueError:
            query = query.join(Company).filter(
                Company.name.ilike(f"%{company}%")
            )

    # Location filter
    if location:
        query = query.filter(
            Job.location.ilike(f"%{location}%")
        )

    # Job type filter
    if job_type:
        query = query.filter(
            Job.job_type.ilike(f"%{job_type}%")
        )

    # Experience filter
    if experience:
        query = query.filter(
            Job.experience.ilike(f"%{experience}%")
        )

    # Skill filter
    if skill:
        query = query.filter(
            Job.skills.ilike(f"%{skill}%")
        )

    # General search
    if search:
        query = query.filter(
            db.or_(
                Job.title.ilike(f"%{search}%"),
                Job.description.ilike(f"%{search}%"),
                Job.skills.ilike(f"%{search}%"),
                Job.location.ilike(f"%{search}%")
            )
        )

    jobs = query.order_by(
        Job.created_at.desc()
    ).all()

    return jsonify({
        "success": True,
        "count": len(jobs),
        "jobs": [
            job.to_dict()
            for job in jobs
        ]
    })


@jobs_bp.route("/api/jobs/<int:job_id>", methods=["GET"])
def get_job(job_id):
    job = db.session.get(Job, job_id)

    if not job:
        return jsonify({
            "success": False,
            "error": "Job not found"
        }), 404

    return jsonify({
        "success": True,
        "job": job.to_dict()
    })


@jobs_bp.route("/jobs")
def jobs_page():
    jobs = Job.query.order_by(
        Job.created_at.desc()
    ).all()

    companies = Company.query.order_by(
        Company.name.asc()
    ).all()

    return render_template(
        "jobs.html",
        jobs=jobs,
        companies=companies
    )


@jobs_bp.route("/jobs/<int:job_id>")
def job_detail_page(job_id):
    job = db.session.get(Job, job_id)

    if not job:
        return "Job not found", 404

    return render_template(
        "job_detail.html",
        job=job
    )