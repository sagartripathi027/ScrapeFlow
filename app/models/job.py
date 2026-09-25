from datetime import datetime

from app import db


class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)

    company_id = db.Column(
        db.Integer,
        db.ForeignKey("companies.id"),
        nullable=False
    )

    title = db.Column(db.String(300), nullable=False)

    location = db.Column(db.String(500))
    job_type = db.Column(db.String(100))
    experience = db.Column(db.String(200))
    shift = db.Column(db.String(100))

    description = db.Column(db.Text)

    # Stored as comma-separated skills
    skills = db.Column(db.Text)

    source_url = db.Column(
        db.String(1000),
        unique=True,
        nullable=False
    )

    source = db.Column(
        db.String(100),
        default="company_website"
    )

    posted_date = db.Column(db.DateTime)

    scraped_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def skill_list(self):
        if not self.skills:
            return []

        return [
            skill.strip()
            for skill in self.skills.split(",")
            if skill.strip()
        ]

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "company": (
                self.company.name
                if self.company
                else None
            ),
            "title": self.title,
            "location": self.location,
            "job_type": self.job_type,
            "experience": self.experience,
            "shift": self.shift,
            "description": self.description,
            "skills": self.skill_list(),
            "source_url": self.source_url,
            "source": self.source,
            "posted_date": (
                self.posted_date.isoformat()
                if self.posted_date
                else None
            ),
            "scraped_at": (
                self.scraped_at.isoformat()
                if self.scraped_at
                else None
            ),
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
        }