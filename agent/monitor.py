"""Live monitor: poll the target inbox and run the agent on each new email.

    python -m agent.monitor --api http://localhost:8000 --backend ollama

Needs the backend running and, for --backend ollama, a local Ollama server with the pinned
model pulled. Use --backend mock-comply or mock-refuse to demo without a GPU.
Use --once to process what is waiting and exit.
"""
import argparse
import os
import sys
import time

from .client import MailClient
from .config import DEFAULT_OPTIONS, MODEL_TAG
from .runner import run_agent

DEV_AGENT_TOKEN = "dev-only-agent-token-change-me"  # same default as backend/app/config.py


def main(argv=None):
    from harness import backends  # the mock backends and Ollama preflight live there

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default=os.environ.get("WEMAIL_API", "http://localhost:8000"))
    ap.add_argument("--token", default=os.environ.get("AGENT_TOKEN", DEV_AGENT_TOKEN))
    ap.add_argument("--backend", choices=backends.BACKENDS, default="ollama")
    ap.add_argument("--model", default=MODEL_TAG)
    ap.add_argument("--variant", default="baseline")
    ap.add_argument("--interval", type=float, default=5.0, help="seconds between polls")
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args(argv)

    try:
        info = backends.preflight(args.backend, args.model)
    except RuntimeError as e:
        print(f"PREFLIGHT FAILED: {e}", file=sys.stderr)
        return 2
    for w in info["warnings"]:
        print(f"WARNING: {w}", file=sys.stderr)

    chat_fn = backends.get_chat_fn(args.backend)
    client = MailClient.from_url(args.api, args.token)
    print(f"monitoring {args.api} with {info['model']} (variant={args.variant})")
    attempts = {}
    while True:
        try:
            pending = client.list_unprocessed()
        except Exception as e:
            print(f"cannot reach backend: {e}", file=sys.stderr)
            if args.once:
                return 2
            pending = []
        for item in pending:
            if attempts.get(item["id"], 0) >= 3:
                continue  # gave up on this email after 3 failed runs; leave it unprocessed
            attempts[item["id"]] = attempts.get(item["id"], 0) + 1
            print(f"processing email {item['id']} from {item['from']}: {item['subject']!r}")
            try:
                trace = run_agent(client, item["id"], model=args.model, variant=args.variant,
                                  chat_fn=chat_fn, options=dict(DEFAULT_OPTIONS))
            except Exception as e:
                print(f"  agent error on email {item['id']}: {e}", file=sys.stderr)
                continue
            for t in trace:
                print(f"  {t['tool']}({t['args']}) -> {t['result']}")
        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
