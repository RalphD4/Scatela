import uuid

from sqlalchemy.dialects.postgresql import UUID

from backend.database import db
from .associations import child_emergency_contact


class Emergency_Contact(db.Model):
    """Emergency contact record associated with one or more children."""

    __tablename__ = "emergency_contact"

    contact_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_name = db.Column(db.String(20), nullable=False)
    phone_number = db.Column(db.Text, nullable=False)

    children = db.relationship(
        "Child",
        secondary=child_emergency_contact,
        back_populates="emergency_contacts",
    )

    def to_dict(self):
        return {
            "contact_id": str(self.contact_id),
            "contact_name": self.contact_name,
            "phone_number": self.phone_number,
        }
