import os
from pathlib import Path

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

BASE_DIR = Path(__file__).resolve().parent.parent


def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )

    # -----------------------------
    # Paths
    # -----------------------------
    database_dir = BASE_DIR / "database"
    upload_dir = BASE_DIR / "uploads" / "resumes"

    database_dir.mkdir(parents=True, exist_ok=True)
    upload_dir.mkdir(parents=True, exist_ok=True)

    db_path = database_dir / "jobs.db"

    # -----------------------------
    # Flask configuration
    # -----------------------------
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{db_path.as_posix()}"
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

    app.config["UPLOAD_FOLDER"] = str(upload_dir)

    # -----------------------------
    # Initialize database
    # -----------------------------
    db.init_app(app)

    # -----------------------------
    # Register routes
    # -----------------------------
    from app.routes.company import company_bp
    from app.routes.jobs import jobs_bp
    from app.routes.resume import resume_bp
    from app.routes.matching import matching_bp

    app.register_blueprint(company_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(resume_bp)
    app.register_blueprint(matching_bp)

    # -----------------------------
    # Dashboard
    # -----------------------------
    @app.route("/")
    def index():
        from app.models.company import Company
        from app.models.job import Job

        companies = Company.query.order_by(
            Company.updated_at.desc()
        ).limit(10).all()

        recent_jobs = Job.query.order_by(
            Job.created_at.desc()
        ).limit(10).all()

        company_count = Company.query.count()
        job_count = Job.query.count()

        skills_count = 0

        for job in Job.query.all():
            skills_count += len(job.skill_list())

        return render_template(
            "index.html",
            companies=companies,
            recent_jobs=recent_jobs,
            company_count=company_count,
            job_count=job_count,
            skills_count=skills_count,
            match_count=0
        )
        
    @app.route("/resume-match")
    def resume_match_page():
        return render_template("resume_match.html")


    @app.route("/settings")
    def settings_page():
        return render_template("settings.html")


    @app.route("/profile")
    def profile_page():
        return render_template("profile.html")

    # -----------------------------
    # Health check
    # -----------------------------
    @app.route("/health")
    def health():
        return {
            "status": "ok",
            "service": "ScrapeFlow"
        }

    # -----------------------------
    # Create database tables
    # -----------------------------
    with app.app_context():
        from app.models.company import Company
        from app.models.job import Job
        from app.models.resume import Resume

        db.create_all()

    return app
