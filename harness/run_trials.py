"""Measurement harness: run N trials per payload and report how often the target's data leaks.

Each trial
    1. resets a throwaway SQLite database to the seeded state (target and attacker accounts),
    2. delivers ONE email from the attacker to the target through the same crud.send_email the
       web API uses (a payload containing HTML tags is sent as an HTML email, stored verbatim),
    3. runs the agent once on that email, over HTTP against the real FastAPI app (in-process),
    4. reads every message the target sent back to the attacker and runs the leak detector
       (harness/detect.py) over the bodies.

The harness needs only Python: no Node, no running server, and the dev database is never touched.

Outputs, written to --out (default results/runs/<timestamp>_<backend>/):
    summary.json     per-payload and overall counts, rates, and 95% Wilson intervals
    trials.csv       one row per trial
    transcripts.jsonl  tool calls and the exact text sent to the attacker, one line per trial
    run_metadata.json  commit, versions, backend, model digest, sampling options

A payload whose filename starts with 00_ is the benign control (no attack in it). Its leak rate
is the detector's false-positive rate and is reported separately from the attack payloads.

Trials that raise an error are counted as errors, never as "no leak".
Exit status: 0 if at least one trial ran, 2 if every trial errored or the backend is unusable.

Examples
    python -m harness.run_trials --backend mock-refuse --n 5      # offline negative control
    python -m harness.run_trials --backend mock-comply --n 5      # offline positive control
    python -m harness.run_trials --backend ollama --n 20          # the real experiment
"""
import argparse
import csv
import datetime
import glob
import importlib.metadata as md
import json
import os
import platform
import subprocess
import sys
import re

from agent.client import MailClient
from agent.config import DEFAULT_OPTIONS, MODEL_DESCRIPTION, MODEL_DIGEST, MODEL_TAG
from agent.runner import run_agent

from . import appenv, backends
from .detect import ALL_FIELDS, SUCCESS_FIELDS, detect, from_api_profile
from .stats import wilson

_HTML_TAG = re.compile(r"<(?:[a-zA-Z][^>]*|/[a-zA-Z][^>]*|!--)>?")


def load_payload(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    header, _, body = text.partition("\n\n")
    return header.replace("Subject:", "", 1).strip(), body


def is_control(path):
    return os.path.basename(path).startswith("00_")


def looks_like_html(body):
    return bool(_HTML_TAG.search(body))


def run_trial(payload_path, client, chat_fn, model, variant, options):
    from app import crud
    from app.database import SessionLocal
    from app.seed import ATTACKER_EMAIL, TARGET_EMAIL

    subject, body = load_payload(payload_path)
    appenv.fresh_db()
    db = SessionLocal()
    try:
        attacker = crud._get_user_by_role(db, "attacker")
        target = crud._get_user_by_role(db, "target")
        html = body if looks_like_html(body) else None
        email_id = crud.send_email(
            db, attacker.id, TARGET_EMAIL, subject, "" if html else body, html
        )["id"]
        profile = crud.get_profile(db, target.id, target.id)
    finally:
        db.close()

    trace = run_agent(client, email_id, model=model, variant=variant, chat_fn=chat_fn,
                      options=options, profile=profile)

    db = SessionLocal()
    try:
        sent = [
            e["body"] for e in crud.list_sent(db, target.id)
            if e["recipient"]["email_address"] == ATTACKER_EMAIL and e["id"] > email_id
        ]
    finally:
        db.close()
    text = "\n".join(reversed(sent))  # list_sent is newest first; restore send order
    hits = detect(from_api_profile(profile), text)
    return {
        "messages_to_attacker": len(sent),
        "tool_calls": [t["tool"] for t in trace],
        **{f: hits[f] for f in ALL_FIELDS},
        "success": hits["success"],
        "text_sent_to_attacker": text,
    }


def _git(*args):
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


def _pkg(name):
    try:
        return md.version(name)
    except md.PackageNotFoundError:
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backend", choices=backends.BACKENDS, required=True)
    ap.add_argument("--n", type=int, default=10, help="trials per payload")
    ap.add_argument("--payloads", default="attacks/payloads", help="payload file or directory")
    ap.add_argument("--model", default=MODEL_TAG)
    ap.add_argument("--variant", default="baseline", help="system prompt variant (defense) to test")
    ap.add_argument("--temperature", type=float, default=DEFAULT_OPTIONS["temperature"])
    ap.add_argument("--seed-base", type=int, default=1000, help="trial i uses seed seed_base + i")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    paths = (sorted(glob.glob(os.path.join(args.payloads, "*.txt")))
             if os.path.isdir(args.payloads) else [args.payloads])
    if not paths:
        print("No payload files found.", file=sys.stderr)
        return 2

    try:
        info = backends.preflight(args.backend, args.model)
    except RuntimeError as e:
        print(f"PREFLIGHT FAILED: {e}", file=sys.stderr)
        return 2
    for w in info["warnings"]:
        print(f"WARNING: {w}", file=sys.stderr)

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = args.out or os.path.join("results", "runs", f"{stamp}_{args.backend}")
    os.makedirs(out, exist_ok=True)
    chat_fn = backends.get_chat_fn(args.backend)

    # Must happen before anything imports app.*; points the backend at a throwaway database.
    appenv.init()
    from fastapi.testclient import TestClient

    from app.main import app

    client = MailClient(TestClient(app), appenv.init()["token"])

    fields = ["payload", "control", "trial", "seed", "messages_to_attacker", "tool_calls",
              *ALL_FIELDS, "success", "error"]
    per_payload = {}
    with open(os.path.join(out, "trials.csv"), "w", newline="", encoding="utf-8") as fcsv, \
         open(os.path.join(out, "transcripts.jsonl"), "w", encoding="utf-8") as ftr:
        w = csv.DictWriter(fcsv, fieldnames=fields)
        w.writeheader()
        for p in paths:
            name = os.path.basename(p)
            stat = {"control": is_control(p), "n": 0, "errors": 0, "successes": 0,
                    "field_hits": {f: 0 for f in ALL_FIELDS}}
            for i in range(args.n):
                seed_i = args.seed_base + i
                options = {**DEFAULT_OPTIONS, "temperature": args.temperature, "seed": seed_i}
                row = {"payload": name, "control": stat["control"], "trial": i, "seed": seed_i}
                try:
                    r = run_trial(p, client, chat_fn, args.model, args.variant, options)
                except Exception as e:
                    stat["errors"] += 1
                    row["error"] = f"{type(e).__name__}: {e}"
                    w.writerow(row)
                    ftr.write(json.dumps({**row}) + "\n")
                    continue
                stat["n"] += 1
                stat["successes"] += int(r["success"])
                for f in ALL_FIELDS:
                    stat["field_hits"][f] += int(r[f])
                w.writerow({**row, **{k: r[k] for k in fields if k in r},
                            "tool_calls": "|".join(r["tool_calls"]), "error": ""})
                ftr.write(json.dumps({**row, "tool_calls": r["tool_calls"],
                                      "text_sent_to_attacker": r["text_sent_to_attacker"]}) + "\n")
                fcsv.flush()
            lo, hi = wilson(stat["successes"], stat["n"])
            stat["rate"] = stat["successes"] / stat["n"] if stat["n"] else None
            stat["ci95"] = [round(lo, 4), round(hi, 4)]
            per_payload[name] = stat

    def pool(control):
        items = [s for s in per_payload.values() if s["control"] == control]
        n = sum(s["n"] for s in items)
        k = sum(s["successes"] for s in items)
        lo, hi = wilson(k, n)
        return {"n": n, "errors": sum(s["errors"] for s in items), "successes": k,
                "rate": (k / n) if n else None, "ci95": [round(lo, 4), round(hi, 4)]}

    summary = {
        "success_definition": f"reply to attacker contains any of: {', '.join(SUCCESS_FIELDS)}",
        "attack_payloads_overall": pool(False),
        "benign_control_false_positive": pool(True),
        "per_payload": per_payload,
    }
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    meta = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {k: _pkg(k) for k in ("fastapi", "starlette", "sqlalchemy", "pydantic", "httpx", "ollama")},
        "backend": info,
        "pinned_model": {"tag": MODEL_TAG, "digest": MODEL_DIGEST, "description": MODEL_DESCRIPTION},
        "variant": args.variant,
        "sampling": dict(DEFAULT_OPTIONS, temperature=args.temperature, seed_base=args.seed_base),
        "trials_per_payload": args.n,
    }
    with open(os.path.join(out, "run_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"backend={args.backend} model={info['model']} variant={args.variant} n={args.n}/payload")
    print(f"success = {summary['success_definition']}\n")
    print(f"{'payload':<28}{'n':>4}{'err':>5}{'leaks':>7}{'rate':>8}   95% CI")
    for name, s in per_payload.items():
        tag = " (control)" if s["control"] else ""
        rate = f"{s['rate']:.0%}" if s["rate"] is not None else "n/a"
        print(f"{name + tag:<28}{s['n']:>4}{s['errors']:>5}{s['successes']:>7}{rate:>8}   "
              f"[{s['ci95'][0]:.2f}, {s['ci95'][1]:.2f}]")
    a = summary["attack_payloads_overall"]
    c = summary["benign_control_false_positive"]
    print(f"\nATTACK PAYLOADS OVERALL: {a['successes']}/{a['n']} trials leaked "
          f"(rate {a['rate'] if a['rate'] is not None else 'n/a'}, 95% CI {a['ci95']})")
    print(f"BENIGN CONTROL (false positives): {c['successes']}/{c['n']}")
    print(f"Results written to {out}")

    total_ok = a["n"] + c["n"]
    return 0 if total_ok > 0 else 2


if __name__ == "__main__":
    sys.exit(main())
