import uuid

from sqlalchemy.dialects.postgresql import UUID

from backend.database import db


class Users(db.Model):
    """Core user account record shared by guardians and children."""

    __tablename__ = "users"

    user_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False, unique=True)
    phone_number = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())

    guardian_profile = db.relationship("Guardian", back_populates="user", uselist=False)
    child_profile = db.relationship("Child", back_populates="user", uselist=False)

    def to_dict(self):
        return {
            "user_id": str(self.user_id),
            "username": self.username,
            "email": self.email,
            "phone_number": self.phone_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
