from datetime import datetime

from app import db


class Match(db.Model):
    __tablename__ = "matches"

    id = db.Column(db.String(64), primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id"), nullable=False)

    result = db.Column(db.JSON, nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    job = db.relationship("Job")
    resume = db.relationship("Resume")

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "resume_id": self.resume_id,
            **(self.result or {}),
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
        }