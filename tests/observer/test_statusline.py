import json

from scc.observer.statusline import append_statusline_sample, format_statusline, normalize_statusline_payload


def test_statusline_sample_keeps_only_context_fields():
    sample = normalize_statusline_payload({
        "session_id": "session-2",
        "prompt_id": "prompt-4",
        "prompt": "do not store this",
        "context_window": {
            "total_input_tokens": 1500,
            "total_output_tokens": 300,
            "context_window_size": 200000,
            "used_percentage": 0.75,
            "remaining_percentage": 99.25,
            "current_usage": {
                "input_tokens": 500,
                "output_tokens": 300,
                "cache_creation_input_tokens": 700,
                "cache_read_input_tokens": 300,
                "private": "ignore",
            },
        },
        "cost": {"total_cost_usd": 42.0},
    })
    assert sample["session_id"] == "session-2"
    assert sample["context_window_size"] == 200000
    assert sample["used_percentage"] == 0.75
    assert sample["current_usage"] == {
        "input_tokens": 500,
        "output_tokens": 300,
        "cache_creation_input_tokens": 700,
        "cache_read_input_tokens": 300,
    }
    encoded = json.dumps(sample)
    assert "do not store" not in encoded
    assert "total_cost_usd" not in encoded
    assert "private" not in encoded


def test_statusline_nulls_are_unavailable_not_zero():
    sample = normalize_statusline_payload({"context_window": None})
    assert sample["total_input_tokens"] is None
    assert sample["context_window_size"] is None
    assert sample["used_percentage"] is None
    assert sample["current_usage"] is None
    assert format_statusline(sample) == "SCC context: unavailable"


def test_context_sample_appends_one_allowlisted_record(tmp_path):
    data = {
        "session_id": "session-3",
        "context_window": {
            "total_input_tokens": 20000,
            "context_window_size": 200000,
            "used_percentage": 10,
            "remaining_percentage": 90,
        },
    }
    append_statusline_sample(tmp_path, data)
    rows = [json.loads(line) for line in (tmp_path / "context_samples.jsonl").read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["used_percentage"] == 10
    assert "prompt" not in rows[0]
    assert "20,000/200,000" in format_statusline(rows[0])
