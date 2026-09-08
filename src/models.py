from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ContactProfile(BaseModel):
    contact_id: str
    display_name: str
    relationship_category: str = "acquaintance"
    formality_score: float = 0.5
    preferred_greetings: List[str] = Field(default_factory=list)
    code_switching_rate: float = 0.0
    emoji_frequency: float = 0.0
    top_emojis: List[str] = Field(default_factory=list)
    avg_response_length: float = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class NormalizedMessage(BaseModel):
    message_id: str
    conversation_id: str
    sender_id: str
    sender_name: str
    message_text: str
    is_user: bool
    timestamp: datetime
    reply_to_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ReconstructedInteraction(BaseModel):
    interaction_id: str
    contact_id: str
    incoming_message: str
    context_history: List[str] = Field(default_factory=list)
    user_response: str
    relationship_category: str
    timestamp: datetime

class MemoryItem(BaseModel):
    memory_id: str
    contact_id: Optional[str] = None
    memory_type: str  # semantic, episodic, relationship, temporal, preference
    fact_summary: str
    confidence: float = 1.0
    created_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    temporal_target: Optional[datetime] = None
    is_active: bool = True
