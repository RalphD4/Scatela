from sqlalchemy.dialects.postgresql import UUID

from backend.database import db
from .associations import child_emergency_contact, guardian_child


class Child(db.Model):
    """Child role profile storing latest known location and guardian associations."""

    __tablename__ = "child"

    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.user_id"), primary_key=True)
    longitude = db.Column(db.Float, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    location_updated_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("Users", back_populates="child_profile")
    guardians = db.relationship("Guardian", secondary=guardian_child, back_populates="children")
    emergency_contacts = db.relationship(
        "Emergency_Contact",
        secondary=child_emergency_contact,
        back_populates="children",
    )
    logs = db.relationship(
        "Child_Log",
        back_populates="child",
        order_by="desc(Child_Log.created_at)",
        cascade="all, delete-orphan",
    )
    base_statuses = db.relationship(
        "ChildBaseStatus",
        back_populates="child",
        cascade="all, delete-orphan",
    )
    alerts = db.relationship("Alert", back_populates="child", cascade="all, delete-orphan")

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
