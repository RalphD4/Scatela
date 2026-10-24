from backend.models import db
from sqlalchemy.dialects.postgresql import UUID

#Child and Contacts association
child_emergency_contact = db.Table(
    "child_emergency_contact",
    db.Column("child_id", UUID(as_uuid=True), db.ForeignKey("child.user_id"), primary_key=True),
    db.Colummn("contact_id", UUID(as_uuid=True), db.ForeignKey("emergency_contact.contact_id"), primary_key=True) 
)


#Parent and Children association
guardian_child = db.Table(
    "guardian_child",
    db.Column("parent_id", UUID(as_uuid=True), db.ForeignKey("guardian.user_id"), primary_key=True),
    db.Column("children_id", UUID(as_uuid=True), db.ForeignKey("child.user_id"), primary_key=True)
)