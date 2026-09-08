import pytest
from src.risk_engine import evaluate_response_risk

def test_evaluate_response_risk_low():
    decision = evaluate_response_risk(
        candidate_response="Coming ra 😂",
        incoming_message="Bro where are you?",
        formality_score=0.1,
        confidence=0.95
    )
    assert decision.decision == "AUTO_SEND"
    assert decision.risk_level == "low"

def test_evaluate_response_risk_high():
    decision = evaluate_response_risk(
        candidate_response="I will send 5000 rupees to your bank account",
        incoming_message="Can you transfer money?",
        formality_score=0.2,
        confidence=0.9
    )
    assert decision.decision == "HUMAN_ONLY"
    assert decision.risk_level == "high"
    assert "money" in decision.reason

def test_evaluate_response_risk_medium():
    decision = evaluate_response_risk(
        candidate_response="Yes sir, I will submit the report by 5 PM.",
        incoming_message="Please submit your report.",
        formality_score=0.8,
        confidence=0.9
    )
    assert decision.decision == "REVIEW"
    assert decision.risk_level == "medium"
