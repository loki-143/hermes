from typing import List, Dict, Any
from src.risk_engine import evaluate_response_risk
from src.context_assembler import ContextAssembler

class EvaluationSuite:
    """
    Offline evaluation suite asserting style matching, risk classification safety,
    and prompt hierarchy construction across test scenarios.
    """
    @staticmethod
    def evaluate_risk_classification(test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        passed = 0
        total = len(test_cases)
        results = []

        for tc in test_cases:
            decision = evaluate_response_risk(
                candidate_response=tc["candidate_response"],
                incoming_message=tc["incoming_message"],
                formality_score=tc.get("formality_score", 0.5)
            )
            is_correct = (decision.decision == tc["expected_decision"])
            if is_correct:
                passed += 1
            results.append({
                "scenario": tc["scenario"],
                "passed": is_correct,
                "expected": tc["expected_decision"],
                "actual": decision.decision
            })

        return {
            "accuracy": round(passed / total, 2) if total > 0 else 0.0,
            "passed": passed,
            "total": total,
            "details": results
        }
