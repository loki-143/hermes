import pytest
from datetime import datetime
from src.models import ReconstructedInteraction
from src.dataset_curator import build_fine_tuning_dataset

def test_build_fine_tuning_dataset():
    interactions = [
        ReconstructedInteraction(
            interaction_id="inter_1",
            contact_id="rahul_123",
            incoming_message="Bro where are you?",
            context_history=["Rahul: I am waiting at cafe"],
            user_response="Coming ra 😂",
            relationship_category="close_friend",
            timestamp=datetime.now()
        )
    ]
    global_style = {
        "code_switch_ratio": 0.5,
        "slang_words": {"ra": 10},
        "emoji_dist": {"😂": 8},
        "avg_sentence_len": 4.5
    }

    dataset = build_fine_tuning_dataset(interactions, global_style)
    assert len(dataset) == 1
    sample = dataset[0]
    assert len(sample["messages"]) == 3
    assert sample["messages"][0]["role"] == "system"
    assert sample["messages"][1]["role"] == "user"
    assert sample["messages"][2]["role"] == "assistant"
    assert sample["messages"][2]["content"] == "Coming ra 😂"
