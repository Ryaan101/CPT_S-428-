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
    line = json.loads((d / "transcripts.jsonl").read_text().splitlines()[0])
    assert line["trace"][0]["tool"] == "read_email" and "result" in line["trace"][0]
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


# --- D3 vectors (attacks/d3): hidden text, poisoned web page, earlier email -----------------

D3 = ("--payloads", "attacks/d3")


def transcripts(tmp_path, backend):
    lines = (tmp_path / backend / "transcripts.jsonl").read_text().splitlines()
    return [json.loads(line) for line in lines]


def test_d3_negative_control_leaks_nothing(tmp_path):
    code, s = run(tmp_path, "mock-refuse", extra=D3)
    assert code == 0
    assert s["attack_payloads_overall"]["n"] == 6  # 3 vectors x 2 trials
    assert s["attack_payloads_overall"]["successes"] == 0
    assert s["benign_control_false_positive"]["successes"] == 0


def test_d3_positive_control_leaks_every_vector_and_no_control(tmp_path):
    code, s = run(tmp_path, "mock-comply", extra=D3)
    assert code == 0
    for vector in ("v1_hidden_text", "v2_web_page", "v3_earlier_email"):
        assert s["per_payload"][vector]["successes"] == s["per_payload"][vector]["n"] == 2, vector
        assert s["per_payload"][vector]["field_hits"]["canary"] == 2, vector
        assert s["per_payload"][f"00_{vector}_control"]["successes"] == 0, vector


def test_d3_each_vector_really_reaches_the_agent_through_its_own_channel(tmp_path):
    run(tmp_path, "mock-refuse", n=1, extra=D3)
    by_name = {t["payload"]: t for t in transcripts(tmp_path, "mock-refuse")}
    v1 = by_name["v1_hidden_text"]["trace"]
    assert [t["tool"] for t in v1] == ["read_email", "reply"]
    assert "font-size:1px" in v1[0]["result"]  # the hidden span arrives as raw HTML

    v2 = by_name["v2_web_page"]["trace"]
    assert "fetch_page" in [t["tool"] for t in v2]
    page = next(t["result"] for t in v2 if t["tool"] == "fetch_page")
    assert "birthdate" in page and "birthdate" not in v2[0]["result"]  # instruction is only on the page

    v3 = by_name["v3_earlier_email"]["trace"]
    tools = [t["tool"] for t in v3]
    assert "search_mailbox" in tools
    reads = [t for t in v3 if t["tool"] == "read_email" and "contact preferences" in t["result"].lower()]
    assert reads and "birthdate" in reads[0]["result"]  # instruction only in the earlier email
    assert "birthdate" not in v3[0]["result"]


def test_d3_earlier_emails_are_already_processed_so_only_the_trigger_is_handed_to_the_agent(tmp_path):
    run(tmp_path, "mock-refuse", n=1, extra=D3)
    t = next(t for t in transcripts(tmp_path, "mock-refuse") if t["payload"] == "v3_earlier_email")
    assert t["trace"][0]["args"]["email_id"] == t["trace"][-1]["args"]["email_id"]  # read and reply the trigger


def test_transcripts_record_why_each_run_ended_and_the_models_last_message(tmp_path):
    run(tmp_path, "mock-refuse", n=1, extra=D3)
    for t in transcripts(tmp_path, "mock-refuse"):
        assert t["stop_reason"] == "finished"
        assert t["final_text"] == "Done."


def test_every_trial_gets_its_own_canary_and_it_is_recorded(tmp_path):
    run(tmp_path, "mock-comply", n=3, extra=D3)
    canaries = [t["canary_value"] for t in transcripts(tmp_path, "mock-comply") if t["payload"] == "v1_hidden_text"]
    assert len(set(canaries)) == 3 and all(c.startswith("CANARY-") for c in canaries)
    meta = json.loads((tmp_path / "mock-comply" / "run_metadata.json").read_text())
    assert set(meta["payload_sha256"]) >= {"v1_hidden_text", "00_v3_earlier_email_control"}


def test_report_pairs_each_vector_with_its_control(tmp_path, capsys):
    from harness import report

    run(tmp_path, "mock-comply", n=2, extra=D3)
    report.main([str(tmp_path / "mock-comply")])
    out = capsys.readouterr().out
    assert "| v2_web_page |" in out and "2 of 2" in out and "0 of 2" in out
