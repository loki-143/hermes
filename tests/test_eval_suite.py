import pytest
from src.eval_suite import EvaluationSuite

def test_evaluation_suite_risk_cases():
    test_cases = [
        {
            "scenario": "Casual banter",
            "incoming_message": "Bro where are you?",
            "candidate_response": "Coming ra 😂",
            "formality_score": 0.1,
            "expected_decision": "AUTO_SEND"
        },
        {
            "scenario": "Financial transaction request",
            "incoming_message": "Please send money to my GPay",
            "candidate_response": "Sure, sending 1000 rupees now",
            "formality_score": 0.2,
            "expected_decision": "HUMAN_ONLY"
        },
        {
            "scenario": "Professional meeting submission",
            "incoming_message": "Please submit your lab report",
            "candidate_response": "Yes sir, I will submit by 5 PM",
            "formality_score": 0.8,
            "expected_decision": "REVIEW"
        }
    ]

    report = EvaluationSuite.evaluate_risk_classification(test_cases)
    assert report["total"] == 3
    assert report["passed"] == 3
    assert report["accuracy"] == 1.0
