from datetime import datetime
from app import db

class Resume(db.Model):
    __tablename__ = "resumes"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(500), nullable=False)
    path = db.Column(db.String(1500), nullable=False)
    text = db.Column(db.Text, nullable=False)
    skills = db.Column(db.Text)
    experience = db.Column(db.Text)
    education = db.Column(db.Text)
    projects = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def skill_list(self):
        return [x.strip() for x in (self.skills or "").split(",") if x.strip()]
