from uuid import uuid4

from flask import Blueprint, request, jsonify, render_template

from app import db
from app.models.job import Job
from app.models.resume import Resume
from app.models.match import Match
from app.services.job_matcher import match_job


matching_bp = Blueprint("matching", __name__)


@matching_bp.post("/api/match/<int:job_id>")
def create_match(job_id):
    data = request.get_json(silent=True) or {}

    resume_id = data.get("resume_id")

    if not resume_id:
        return jsonify({
            "success": False,
            "error": "resume_id is required."
        }), 400

    try:
        resume_id = int(resume_id)
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "error": "resume_id must be a valid integer."
        }), 400

    job = db.session.get(Job, job_id)

    if not job:
        return jsonify({
            "success": False,
            "error": "Job not found."
        }), 404

    resume = db.session.get(Resume, resume_id)

    if not resume:
        return jsonify({
            "success": False,
            "error": "Resume not found."
        }), 404

    try:
        result = match_job(job, resume)

        match_id = uuid4().hex

        match = Match(
            id=match_id,
            job_id=job.id,
            resume_id=resume.id,
            result=result,
        )

        db.session.add(match)
        db.session.commit()

        return jsonify(match.to_dict()), 201

    except Exception as exc:
        db.session.rollback()

        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500


@matching_bp.get("/api/match/<match_id>")
def get_match(match_id):
    match = db.session.get(Match, match_id)

    if not match:
        return jsonify({
            "success": False,
            "error": "Match result not found."
        }), 404

    return jsonify(match.to_dict())


@matching_bp.get("/match/<match_id>")
def match_page(match_id):
    match = db.session.get(Match, match_id)

    if not match:
        return "Match result not found", 404

    job = db.session.get(Job, match.job_id)

    return render_template(
        "match_result.html",
        match=match.to_dict(),
        job=job.to_dict() if job else None,
        match_id=match_id,
    )