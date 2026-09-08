import re
from typing import Dict, Any
from pydantic import BaseModel

class RiskDecision(BaseModel):
    decision: str  # AUTO_SEND, REVIEW, HUMAN_ONLY
    risk_level: str  # low, medium, high
    confidence: float
    reason: str

HIGH_RISK_KEYWORDS = {
    "money", "pay", "rupees", "transfer", "bank", "account", "otp", "password",
    "contract", "legal", "promise", "guarantee", "buy", "purchase", "sign",
    "password", "secret", "credentials", "credit card", "debit card"
}

MEDIUM_RISK_KEYWORDS = {
    "meeting", "appointment", "schedule", "deadline", "submit", "confirm",
    "location", "address", "call", "discuss"
}

def evaluate_response_risk(
    candidate_response: str,
    incoming_message: str,
    formality_score: float = 0.5,
    confidence: float = 0.9
) -> RiskDecision:
    combined_text = (incoming_message + " " + candidate_response).lower()

    # Check high risk
    high_matches = [w for w in HIGH_RISK_KEYWORDS if re.search(r"\b" + re.escape(w) + r"\b", combined_text)]
    if high_matches:
        return RiskDecision(
            decision="HUMAN_ONLY",
            risk_level="high",
            confidence=confidence,
            reason=f"High-risk topic detected: {', '.join(high_matches)}"
        )

    # Check medium risk / professional formality
    med_matches = [w for w in MEDIUM_RISK_KEYWORDS if re.search(r"\b" + re.escape(w) + r"\b", combined_text)]
    if med_matches or formality_score >= 0.7:
        return RiskDecision(
            decision="REVIEW",
            risk_level="medium",
            confidence=confidence,
            reason="Medium-risk schedule/formal commitment requiring approval"
        )

    # Low risk
    return RiskDecision(
        decision="AUTO_SEND",
        risk_level="low",
        confidence=confidence,
        reason="Low-risk routine social interaction"
    )
