from datetime import datetime

from app import db


class Company(db.Model):
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(200),
        unique=True,
        nullable=False
    )

    domain = db.Column(db.String(300))
    website_url = db.Column(db.String(500))
    careers_url = db.Column(db.String(500))

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    jobs = db.relationship(
        "Job",
        backref="company",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "website_url": self.website_url,
            "careers_url": self.careers_url,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at else None
            ),
        }