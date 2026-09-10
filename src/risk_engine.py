import re
import json
from typing import Dict, Any, Optional, Callable
from pydantic import BaseModel

class RiskDecision(BaseModel):
    decision: str  # AUTO_SEND, REVIEW, HUMAN_ONLY
    risk_level: str  # low, medium, high
    confidence: float
    reason: str
    suggested_options: Optional[list] = None

HIGH_RISK_KEYWORDS = {
    "money", "pay", "rupees", "transfer", "bank", "account", "otp", "password",
    "contract", "legal", "promise", "guarantee", "buy", "purchase", "sign",
    "secret", "credentials", "credit card", "debit card"
}

MEDIUM_RISK_KEYWORDS = {
    "meeting", "appointment", "schedule", "deadline", "confirm",
    "repu", "kaali", "eldhama", "oddha", "vosthava", "osthava", "plans", "plan",
    "movie ki", "lunch ki", "dinner ki", "tea ki", "coffee ki"
}

# Match specific time expressions (e.g. 5:00pm, 5:30, 9am, 9pm, repu 9 ki)
TIME_PATTERN = re.compile(r"\b(?:\d{1,2}:\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm))\b", re.IGNORECASE)

RISK_EVALUATION_PROMPT = """
You are the AI Risk & Decision Gatekeeper for Loki's Personal WhatsApp Agent.
Your job is to analyze an incoming WhatsApp message and candidate response to determine if it involves a REAL-WORLD DECISION or COMMITMENT that requires Loki's explicit human approval.

Rules for Classification:
1. HUMAN_ONLY (High Risk):
   - Involves money, financial transfers, passwords, OTPs, legal promises, sensitive credentials.
2. REVIEW (Medium Risk):
   - Involves scheduling, meeting times, availability ("repu kaali eh na", "9 ki free ah"), plans ("movie ki eldhama"), or making a real-world commitment without prior confirmation.
3. AUTO_SEND (Low Risk):
   - Casual social banter, emotional reactions ("miss u", "chinna help", "happy huff", "happy holi"), greetings, or general chat with zero real-world schedule/financial commitment.

Analyze the following:
Incoming Message: "{incoming_message}"
Candidate Response: "{candidate_response}"

Output JSON strictly matching this schema:
{{
  "decision": "AUTO_SEND" | "REVIEW" | "HUMAN_ONLY",
  "risk_level": "low" | "medium" | "high",
  "reason": "Brief explanation of why approval is or is not needed",
  "suggested_options": ["Option 1 (Affirmative)", "Option 2 (Negative)", "Option 3 (Tentative)"]
}}
"""

def evaluate_response_risk(
    candidate_response: str,
    incoming_message: str,
    formality_score: float = 0.5,
    confidence: float = 0.9,
    llm_evaluator_fn: Optional[Callable] = None
) -> RiskDecision:
    """
    Evaluates risk using AI Decision Reasoning + Rule Safety Net.
    """
    combined_text = (incoming_message + " " + candidate_response).lower()

    # 1. Fast Rule Safety Net for High Risk (Financial / Credentials)
    high_matches = [w for w in HIGH_RISK_KEYWORDS if re.search(r"\b" + re.escape(w) + r"\b", combined_text)]
    if high_matches:
        return RiskDecision(
            decision="HUMAN_ONLY",
            risk_level="high",
            confidence=1.0,
            reason=f"High-risk topic detected: {', '.join(high_matches)}"
        )

    # 2. LLM AI Risk Evaluator (if function provided)
    if llm_evaluator_fn:
        try:
            ai_res = llm_evaluator_fn(incoming_message, candidate_response)
            if isinstance(ai_res, dict) and "decision" in ai_res:
                return RiskDecision(
                    decision=ai_res["decision"],
                    risk_level=ai_res.get("risk_level", "medium"),
                    confidence=0.95,
                    reason=ai_res.get("reason", "AI Decision Gate evaluation"),
                    suggested_options=ai_res.get("suggested_options")
                )
        except Exception:
            pass  # Fall back to heuristic engine

    # 3. Dynamic Rule Safety Net for Scheduling & Real-World Commitments
    has_time_spec = bool(TIME_PATTERN.search(incoming_message) or TIME_PATTERN.search(candidate_response))
    med_matches = [w for w in MEDIUM_RISK_KEYWORDS if re.search(r"\b" + re.escape(w) + r"\b", combined_text)]

    if has_time_spec or med_matches or formality_score >= 0.7:
        matched_reasons = []
        if has_time_spec:
            matched_reasons.append("Time pattern / schedule specification")
        if med_matches:
            matched_reasons.append(f"Decision/commitment keywords ({', '.join(med_matches[:3])})")
        if formality_score >= 0.7:
            matched_reasons.append("High formality recipient")

        return RiskDecision(
            decision="REVIEW",
            risk_level="medium",
            confidence=confidence,
            reason=f"Real-world decision detected: {' + '.join(matched_reasons)}"
        )

    # 4. Low Risk (Ordinary social banter)
    return RiskDecision(
        decision="AUTO_SEND",
        risk_level="low",
        confidence=confidence,
        reason="Low-risk routine social interaction"
    )
