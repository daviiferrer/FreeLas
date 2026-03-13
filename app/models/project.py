import enum
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class ProjectStatus(str, enum.Enum):
    new = "new"
    phase1_pass = "phase1_pass"
    phase2_pass = "phase2_pass"
    phase3_pass = "phase3_pass" # Completed analysis + strategist
    pending_approval = "pending_approval" # Waiting user action via WAHA
    approved = "approved"       # User replied YES
    rejected = "rejected"       # User replied NO
    sent = "sent"               # Playwright sent it


class Project(Base):
    __tablename__ = "projects"

    project_id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    experience_level = Column(String, nullable=True)
    client_name = Column(String, nullable=True)
    client_rating = Column(String, nullable=True)
    proposals_count = Column(String, nullable=True)
    interested_count = Column(String, nullable=True)
    published_time = Column(String, nullable=True)
    url = Column(String, nullable=True)
    scraped_at = Column(DateTime, default=lambda: datetime.now())
    status = Column(Enum(ProjectStatus), default=ProjectStatus.new, index=True)

    # AI pipeline fields
    ai_score_phase1 = Column(Integer, nullable=True)
    ai_reason_phase1 = Column(Text, nullable=True)
    ai_score_phase2 = Column(Integer, nullable=True)
    ai_analysis = Column(Text, nullable=True)
    ai_complexity = Column(String, nullable=True)
    ai_estimated_effort = Column(String, nullable=True)
    ai_summary = Column(Text, nullable=True) # One-line summary

    # Proposal fields
    ai_action = Column(String, nullable=True) # "SEND_PROPOSAL" or "ASK_QUESTION"
    proposal_text = Column(Text, nullable=True)
    ai_question = Column(Text, nullable=True)
    recommended_price = Column(String, nullable=True)
    recommended_delivery_time = Column(String, nullable=True)
    
    # WAHA HITL
    waha_message_id = Column(String, nullable=True)

    def to_dict(self):
        return {
            "project_id": self.project_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "experience_level": self.experience_level,
            "client_name": self.client_name,
            "client_rating": self.client_rating,
            "proposals_count": self.proposals_count,
            "interested_count": self.interested_count,
            "published_time": self.published_time,
            "url": self.url,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "status": self.status.value if self.status else None,
            "ai_score_phase1": self.ai_score_phase1,
            "ai_reason_phase1": self.ai_reason_phase1,
            "ai_score_phase2": self.ai_score_phase2,
            "ai_analysis": self.ai_analysis,
            "ai_complexity": self.ai_complexity,
            "ai_estimated_effort": self.ai_estimated_effort,
            "ai_action": self.ai_action,
            "ai_summary": self.ai_summary,
            "proposal_text": self.proposal_text,
            "ai_question": self.ai_question,
            "recommended_price": self.recommended_price,
            "recommended_delivery_time": self.recommended_delivery_time,
            "waha_message_id": self.waha_message_id,
        }
