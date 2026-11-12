from sqlalchemy.dialects.postgresql import UUID

from backend.database import db
from .associations import guardian_child


class Guardian(db.Model):
    """Guardian role profile storing current location and managed relationships."""

    __tablename__ = "guardian"

    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.user_id"), primary_key=True)
    longitude = db.Column(db.Float, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    location_updated_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("Users", back_populates="guardian_profile")
    children = db.relationship("Child", secondary=guardian_child, back_populates="guardians")
    bases = db.relationship("Bases", back_populates="guardian", cascade="all, delete-orphan")
    alerts = db.relationship("Alert", back_populates="guardian", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "user_id": str(self.user_id),
            "username": self.user.username if self.user else None,
            "email": self.user.email if self.user else None,
            "phone_number": self.user.phone_number if self.user else None,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "location_updated_at": (
                self.location_updated_at.isoformat() if self.location_updated_at else None
            ),
        }
