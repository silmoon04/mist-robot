import json
from pathlib import Path
from urllib.error import HTTPError

import pytest
import httpx

from jev_comparison_20260929 import JevClient, load_key, run_cases, score_choice, validate_answers


QUESTION = {"action": {"type": "choice", "instructions": "Classify this.",
                       "criteria": {"wait": "Wait", "yield": "Yield"}}}
RESPONSE = {"model": "jev-1.13.0", "answers": {"action": {"type": "choice", "choice": "wait",
            "probabilities": {"wait": 0.8, "yield": 0.2}, "confidence": 0.6}},
            "usage": {"input_tokens": 100, "output_tokens": 12}}


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def read(self):
        return json.dumps(RESPONSE).encode()


def test_client_sends_pinned_model_and_keeps_key_out_of_result():
    def opener(request, timeout):
        payload = json.loads(request.data)
        assert payload == {"state": {"transcript": "hello"}, "model": "jev-1.13.0", "questions": QUESTION}
        assert request.get_header("Authorization") == "Bearer secret"
        assert timeout == 3
        return FakeResponse()

    result = JevClient("secret", timeout_s=3, opener=opener).decide({"transcript": "hello"}, QUESTION)
    assert result["status"] == "ok"
    assert result["response"]["answers"]["action"]["probabilities"]["wait"] == 0.8
    assert result["usage_known"]
    assert result["estimated_input_cost_usd"] == pytest.approx(0.0000042)
    assert "secret" not in json.dumps(result)


def test_pooled_httpx_transport_and_server_error_are_recorded():
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200 if len(calls) == 1 else 529,
                              json=RESPONSE if len(calls) == 1 else {"message": "busy"})

    client = JevClient("secret", transport=httpx.MockTransport(handler))
    try:
        first = client.decide("hello", QUESTION)
        second = client.decide("hello", QUESTION)
    finally:
        client.close()
    assert len(calls) == 2 and all(x["model"] == "jev-1.13.0" for x in calls)
    assert first["transport"] == "httpx_pooled_client" and first["status"] == "ok"
    assert second["status"] == "error" and second["http_status"] == 529


def test_validation_rejects_missing_or_bad_distributions():
    bad = json.loads(json.dumps(RESPONSE))
    bad["answers"]["action"]["probabilities"]["yield"] = 0.4
    with pytest.raises(ValueError):
        validate_answers(QUESTION, bad)
    bad = json.loads(json.dumps(RESPONSE))
    bad["answers"] = {}
    with pytest.raises(ValueError):
        validate_answers(QUESTION, bad)


def test_http_error_is_one_attempt_without_retry():
    attempts = []

    def opener(request, timeout):
        attempts.append(1)
        raise HTTPError(request.full_url, 429, "rate limit", {}, None)

    result = JevClient("secret", opener=opener).decide("text", QUESTION)
    assert len(attempts) == 1
    assert result["status"] == "error" and result["http_status"] == 429
    assert result["error_type"] == "http_error"


def test_bounded_runner_freezes_input_before_calls_and_preserves_errors(tmp_path):
    source = tmp_path / "cases.json"
    source.write_text(json.dumps({"cases": [{"id": "c1", "family": "ack", "state": {"text": "Mm-hm"},
                                   "questions": QUESTION, "expected": {"action": ["wait"]}}]}), encoding="utf-8")
    output = tmp_path / "out"

    class FakeClient:
        calls = 0

        def decide(self, state, questions):
            assert (output / "plan.frozen.json").exists()
            self.calls += 1
            if self.calls == 2:
                return {"status": "error", "request_model": "jev-1.13.0", "http_status": 429,
                        "wall_latency_ms": 40.0, "error_type": "http_error", "response": None,
                        "usage_known": False, "estimated_input_cost_usd": None}
            return {"status": "ok", "request_model": "jev-1.13.0", "http_status": 200,
                    "wall_latency_ms": 30.0, "error_type": None,
                    "response": validate_answers(QUESTION, RESPONSE), "usage_known": True,
                    "estimated_input_cost_usd": 0.0000042}

    client = FakeClient()
    report = run_cases(source, output, client)
    assert client.calls == 2
    assert report["successes"] == 1 and report["errors"] == 1
    assert report["correct_decisions"] == 1
    assert report["usage_unknown_attempts"] == 1
    assert len(json.loads((output / "attempts.json").read_text())[0]["scores"]) == 1
    assert score_choice(RESPONSE["answers"]["action"], ["wait"])["chosen_probability_brier"] == 0.04


def test_key_loader_reads_exact_assignment(tmp_path, monkeypatch):
    monkeypatch.delenv("JEV_API_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text("NOT_JEV_API_KEY=wrong\nJEV_API_KEY='correct'\n", encoding="utf-8")
    assert load_key(env) == "correct"


def test_provider_only_shared_questions_join_local_gold(tmp_path):
    source = tmp_path / "provider.json"
    gold = tmp_path / "gold.json"
    question = {"turn_intent": QUESTION["action"]}
    response = {**RESPONSE, "answers": {"turn_intent": RESPONSE["answers"]["action"]}}
    source.write_text(json.dumps({"model": "jev-1.13.0", "questions": question,
                                  "cases": [{"id": "c1", "question_ids": ["turn_intent"],
                                             "state": {"latest_user_transcript": "Hello",
                                                                  "assistant_is_speaking": True}}]}), encoding="utf-8")
    gold.write_text(json.dumps({"cases": [{"id": "c1", "transcript": "Hello", "family": "greeting",
                                           "allowed": ["wait"]}]}), encoding="utf-8")

    class FakeClient:
        def decide(self, state, questions):
            assert questions == question
            assert "allowed" not in json.dumps(state)
            return {"status": "ok", "request_model": "jev-1.13.0", "http_status": 200,
                    "wall_latency_ms": 20.0, "error_type": None,
                    "response": validate_answers(question, response), "usage_known": True,
                    "estimated_input_cost_usd": 0.0000042}

    report = run_cases(source, tmp_path / "out", FakeClient(), gold_path=gold)
    assert report["by_question"]["turn_intent"]["correct"] == 2
    assert report["by_family"]["greeting"]["intent_correct"] == 2
    assert report["gold_sha256"]
