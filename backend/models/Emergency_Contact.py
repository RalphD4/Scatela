from backend.database import db
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Emergency_Contact(db.model):
    contact_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_name = db.Column(db.String(20), nullable=False)
    phone_number = db.Column(db.Text, nullable=False)
    
