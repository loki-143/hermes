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
    "secret", "credentials", "credit card", "debit card"
}

MEDIUM_RISK_KEYWORDS = {
    "meeting", "appointment", "schedule", "deadline", "submit", "confirm",
    "location", "address", "call", "discuss", "ready", "time", "pm", "am",
    "today", "tomorrow", "tonight", "reach", "come", "repu", "kaali", "free"
}

# Match time expressions (e.g. 5:00, 5pm, 5:30)
TIME_PATTERN = re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b", re.IGNORECASE)

def evaluate_response_risk(
    candidate_response: str,
    incoming_message: str,
    formality_score: float = 0.5,
    confidence: float = 0.9
) -> RiskDecision:
    combined_text = (incoming_message + " " + candidate_response).lower()

    # 1. Check High Risk (Financial / Legal / Security)
    high_matches = [w for w in HIGH_RISK_KEYWORDS if re.search(r"\b" + re.escape(w) + r"\b", combined_text)]
    if high_matches:
        return RiskDecision(
            decision="HUMAN_ONLY",
            risk_level="high",
            confidence=confidence,
            reason=f"High-risk security/financial topic detected: {', '.join(high_matches)}"
        )

    # 2. Check Time Commitments & Scheduling (Medium Risk -> Needs Review)
    has_time_spec = bool(TIME_PATTERN.search(incoming_message) or TIME_PATTERN.search(candidate_response))
    med_matches = [w for w in MEDIUM_RISK_KEYWORDS if re.search(r"\b" + re.escape(w) + r"\b", combined_text)]

    if has_time_spec or med_matches or formality_score >= 0.7:
        matched_reasons = []
        if has_time_spec:
            matched_reasons.append("Time commitment / specific time pattern")
        if med_matches:
            matched_reasons.append(f"Scheduling keywords ({', '.join(med_matches[:3])})")
        if formality_score >= 0.7:
            matched_reasons.append("High formality recipient")

        return RiskDecision(
            decision="REVIEW",
            risk_level="medium",
            confidence=confidence,
            reason=f"Requires user approval: {' + '.join(matched_reasons)}"
        )

    # 3. Low Risk (Ordinary social banter without commitments)
    return RiskDecision(
        decision="AUTO_SEND",
        risk_level="low",
        confidence=confidence,
        reason="Low-risk routine social interaction"
    )
