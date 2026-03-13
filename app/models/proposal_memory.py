import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SQLEnum

from app.models.project import Base

class ProposalOutcome(str, enum.Enum):
    pending = "pending"
    won = "won"
    lost = "lost"
    no_response = "no_response"

class ProposalMemory(Base):
    __tablename__ = "proposal_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, nullable=True, index=True)
    category = Column(String, nullable=True, index=True)
    
    proposal_text = Column(Text, nullable=False)
    price = Column(String, nullable=True)
    delivery_days = Column(String, nullable=True)
    
    outcome = Column(SQLEnum(ProposalOutcome), default=ProposalOutcome.pending, nullable=False, index=True)
    client_response = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    lessons_learned = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "category": self.category,
            "proposal_text": self.proposal_text,
            "price": self.price,
            "delivery_days": self.delivery_days,
            "outcome": self.outcome.value,
            "client_response": self.client_response,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "lessons_learned": self.lessons_learned
        }
