from sqlalchemy.dialects.postgresql import UUID

from backend.database import db

# Child and Emergency Contacts association
child_emergency_contact = db.Table(
    "child_emergency_contact",
    db.Column("child_id", UUID(as_uuid=True), db.ForeignKey("child.user_id"), primary_key=True),
    db.Column(
        "contact_id",
        UUID(as_uuid=True),
        db.ForeignKey("emergency_contact.contact_id"),
        primary_key=True,
    ),
)

# Guardian and Children association
guardian_child = db.Table(
    "guardian_child",
    db.Column("guardian_id", UUID(as_uuid=True), db.ForeignKey("guardian.user_id"), primary_key=True),
    db.Column("child_id", UUID(as_uuid=True), db.ForeignKey("child.user_id"), primary_key=True),
)
