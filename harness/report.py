"""Turn harness result folders into the tables used in the write-up, so no number is typed by hand.

    python -m harness.report results/baseline/llama3.1-8b results/baseline/qwen2.5-7b
    python -m harness.report --before results/baseline/llama3.1-8b --after results/mitigated/llama3.1-8b

Each folder is one run (it must contain summary.json and run_metadata.json). The first form prints
one row per vector and model with leaks out of trials, the 95% interval, and the matching control.
The second form prints before and after side by side. A control for attack X is the payload
named 00_X_control, falling back to nothing if there is none.
"""
import argparse
import json
import os
import sys


def load(folder):
    with open(os.path.join(folder, "summary.json"), encoding="utf-8") as f:
        summary = json.load(f)
    with open(os.path.join(folder, "run_metadata.json"), encoding="utf-8") as f:
        meta = json.load(f)
    return summary, meta


def cell(stat):
    if not stat or not stat["n"]:
        return "n/a"
    lo, hi = stat["ci95"]
    err = f", {stat['errors']} errors" if stat["errors"] else ""
    return f"{stat['successes']} of {stat['n']} ({stat['rate']:.0%}, CI {lo:.2f} to {hi:.2f}){err}"


def rows(folder):
    summary, meta = load(folder)
    per = summary["per_payload"]
    out = []
    for name, stat in per.items():
        if stat["control"]:
            continue
        out.append((name, stat, per.get(f"00_{name}_control"), stat["field_hits"]))
    return meta, out


def label(meta):
    return f"{meta.get('model_under_test', meta['backend']['model'])} ({meta.get('variant', 'baseline')})"


def table(folders):
    print("| Vector | Model | Leaks out of trials | Matching control | Canary leaked |")
    print("|---|---|---|---|---|")
    for folder in folders:
        meta, rs = rows(folder)
        for name, stat, ctrl, hits in rs:
            print(f"| {name} | {label(meta)} | {cell(stat)} | {cell(ctrl)} | {hits.get('canary', 0)} of {stat['n']} |")


def compare(before, after):
    mb, rb = rows(before)
    ma, ra = rows(after)
    ra = {r[0]: r for r in ra}
    print(f"Before: {label(mb)}   After: {label(ma)}\n")
    print("| Vector | Before | After | Control before | Control after |")
    print("|---|---|---|---|---|")
    for name, stat, ctrl, _ in rb:
        a = ra.get(name)
        print(f"| {name} | {cell(stat)} | {cell(a[1]) if a else 'n/a'} | {cell(ctrl)} | "
              f"{cell(a[2]) if a else 'n/a'} |")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folders", nargs="*")
    ap.add_argument("--before")
    ap.add_argument("--after")
    args = ap.parse_args(argv)
    if args.before and args.after:
        compare(args.before, args.after)
    elif args.folders:
        table(args.folders)
    else:
        ap.error("give result folders, or --before and --after")
    return 0


if __name__ == "__main__":
    sys.exit(main())
