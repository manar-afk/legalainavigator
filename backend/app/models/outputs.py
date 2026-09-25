from typing import Optional, List
from pydantic import BaseModel, Field


class PlainLanguageSummary(BaseModel):
    """High-level accessible overview of document terms."""
    title: str
    parties_involved: List[str] = Field(default_factory=list)
    core_purpose: str
    key_obligations: List[str] = Field(default_factory=list)
    key_rights: List[str] = Field(default_factory=list)
    crucial_deadlines: List[str] = Field(default_factory=list)
    potential_risks_or_restrictions: List[str] = Field(default_factory=list)


class ObligationTimelineItem(BaseModel):
    """Timeline entry for obligations, deadlines, and milestones."""
    date_or_trigger: str  # e.g., "Within 14 days of written notice", "Day 1 of each month"
    event_type: str  # "deadline", "payment", "notice", "renewal"
    party_responsible: str
    description: str
    source_clause: str


class ChecklistItem(BaseModel):
    """Actionable preparation task for the user."""
    id: str
    category: str  # "document_gathering", "fact_checking", "date_verification", "communication"
    task: str
    explanation: str
    is_completed: bool = False


class LawyerPrepBrief(BaseModel):
    """Structured 1-page consultation brief to prepare for an attorney/advocate."""
    client_situation: str
    stated_user_facts: List[str] = Field(default_factory=list)
    relevant_documents: List[str] = Field(default_factory=list)
    relevant_clauses_extracted: List[str] = Field(default_factory=list)
    potential_inconsistencies: List[str] = Field(default_factory=list)
    missing_facts_to_investigate: List[str] = Field(default_factory=list)
    recommended_questions_for_lawyer: List[str] = Field(default_factory=list)
    disclaimer: str = (
        "This brief is an informational preparation document generated to assist you in "
        "consulting a qualified legal professional. It does not constitute legal representation or advice."
    )
