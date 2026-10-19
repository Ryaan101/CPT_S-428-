import json
import os

from harness import run_trials


def run(tmp_path, backend, n=2, extra=()):
    out = tmp_path / backend
    code = run_trials.main(["--backend", backend, "--n", str(n), "--out", str(out), *extra])
    return code, json.loads((out / "summary.json").read_text()) if (out / "summary.json").exists() else None


def test_mock_refuse_is_the_negative_control(tmp_path):
    code, s = run(tmp_path, "mock-refuse")
    assert code == 0
    assert s["attack_payloads_overall"]["successes"] == 0
    assert s["attack_payloads_overall"]["n"] == 10
    assert s["benign_control_false_positive"]["successes"] == 0


def test_mock_comply_is_the_positive_control(tmp_path):
    code, s = run(tmp_path, "mock-comply")
    assert code == 0
    assert s["attack_payloads_overall"]["successes"] == s["attack_payloads_overall"]["n"] == 10
    assert s["benign_control_false_positive"]["successes"] == 0  # attack text, not the pipeline, causes leaks


def test_html_payloads_reach_the_agent_as_raw_html(tmp_path):
    # mock-comply obeys only if the hidden instruction text is visible to it in read_email output.
    # Hidden span, comment and img alt only exist in the raw HTML, so 100% leaks proves raw delivery.
    code, s = run(tmp_path, "mock-comply", n=1)
    for name in ("02_hidden_span.txt", "03_html_comment.txt", "05_img_alt_attribute.txt"):
        assert s["per_payload"][name]["successes"] == 1, name


def test_outputs_are_written(tmp_path):
    run(tmp_path, "mock-refuse", n=1)
    d = tmp_path / "mock-refuse"
    for f in ("summary.json", "trials.csv", "transcripts.jsonl", "run_metadata.json"):
        assert (d / f).exists(), f
    meta = json.loads((d / "run_metadata.json").read_text())
    assert meta["pinned_model"]["digest"] == "46e0c10c039e"
    assert meta["sampling"]["temperature"] == 0.8


def test_errors_are_counted_not_treated_as_no_leak(tmp_path, monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("model crashed")

    monkeypatch.setattr(run_trials.backends, "get_chat_fn", lambda b: boom)
    code, s = run(tmp_path, "mock-refuse", n=2)
    assert code == 2  # nothing ran successfully
    assert s["attack_payloads_overall"]["errors"] == 10
    assert s["attack_payloads_overall"]["n"] == 0
    assert s["attack_payloads_overall"]["rate"] is None


def test_ollama_down_fails_loudly(tmp_path, monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:9")  # nothing listens here
    code, s = run(tmp_path, "ollama", n=1)
    assert code == 2 and s is None


def test_harness_never_uses_the_dev_database():
    assert "wemail.db" not in os.environ["DATABASE_URL"]
