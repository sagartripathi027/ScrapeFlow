import os
import uuid
from werkzeug.utils import secure_filename

from app import db
from app.models.resume import Resume
from app.services.resume_parser import parse_resume
from flask import Blueprint, request, jsonify, current_app, render_template
resume_bp = Blueprint("resume", __name__)

ALLOWED_EXTENSIONS = {"pdf", "docx"}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@resume_bp.route("/api/resume/upload", methods=["POST"])
def upload_resume():

    if "resume" not in request.files:
        return jsonify({
            "success": False,
            "error": "Resume file is required"
        }), 400

    file = request.files["resume"]

    if not file.filename:
        return jsonify({
            "success": False,
            "error": "No file selected"
        }), 400

    if not allowed_file(file.filename):
        return jsonify({
            "success": False,
            "error": "Only PDF and DOCX files are supported"
        }), 400

    try:
        original_filename = secure_filename(file.filename)

        extension = original_filename.rsplit(".", 1)[1].lower()

        unique_filename = f"{uuid.uuid4().hex}.{extension}"

        upload_folder = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)

        file_path = os.path.join(
            upload_folder,
            unique_filename
        )

        file.save(file_path)

        parsed_data = parse_resume(file_path)

        resume = Resume(
            filename=original_filename,
            path=file_path,
            text=parsed_data.get("text", ""),
            skills=parsed_data.get("skills", ""),
            experience=parsed_data.get("experience", ""),
            education=parsed_data.get("education", ""),
            projects=parsed_data.get("projects", "")
        )

        db.session.add(resume)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Resume uploaded successfully",
            "resume": {
                "id": resume.id,
                "filename": resume.filename,
                "skills": resume.skill_list(),
                "experience": resume.experience,
                "education": resume.education,
                "projects": resume.projects
            }
        }), 201

    except Exception as e:

        db.session.rollback()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@resume_bp.route("/api/resume/<int:resume_id>", methods=["GET"])
def get_resume(resume_id):

    resume = db.session.get(Resume, resume_id)

    if not resume:
        return jsonify({
            "success": False,
            "error": "Resume not found"
        }), 404

    return jsonify({
        "success": True,
        "resume": {
            "id": resume.id,
            "filename": resume.filename,
            "skills": resume.skill_list(),
            "experience": resume.experience,
            "education": resume.education,
            "projects": resume.projects,
            "text": resume.text
        }
    })
@resume_bp.route("/jobs/<int:job_id>/upload")
def upload_resume_page(job_id):
    from app.models.job import Job

    job = db.session.get(Job, job_id)

    if not job:
        return "Job not found", 404

    return render_template(
        "upload_resume.html",
        job=job
    )