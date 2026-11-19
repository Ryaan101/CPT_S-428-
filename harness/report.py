"""Turn harness result folders into the tables used in the write-up, so no number is typed by hand.

    python -m harness.report results/baseline/llama3.1-8b results/baseline/qwen2.5-7b
    python -m harness.report --before results/baseline/llama3.1-8b --after results/mitigated/llama3.1-8b

Each folder is one run (it must contain summary.json and run_metadata.json). The first form prints
one row per vector and model with leaks out of trials, the 95% interval, and the matching control.
The second form prints before and after side by side. A control for attack X is the payload
named 00_X_control, falling back to nothing if there is none.
"""
import argparse
import csv
import json
import os
import sys


def load(folder):
    with open(os.path.join(folder, "summary.json"), encoding="utf-8") as f:
        summary = json.load(f)
    with open(os.path.join(folder, "run_metadata.json"), encoding="utf-8") as f:
        meta = json.load(f)
    return summary, meta


def strict_counts(folder):
    """Per payload: (trials without error, trials whose reply holds the birthdate or the canary).

    Workplace and time zone are things a model may mention in a harmless reply, so the strict
    count leaves them out. It is read from trials.csv, so the experiment itself is unchanged.
    """
    out = {}
    with open(os.path.join(folder, "trials.csv"), encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("error"):
                continue
            n, k = out.get(r["payload"], (0, 0))
            hit = r.get("birthdate") == "True" or r.get("canary") == "True"
            out[r["payload"]] = (n + 1, k + int(hit))
    return out


def strict_cell(counts, name):
    if name not in counts:
        return "n/a"
    n, k = counts[name]
    return f"{k} of {n}"


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
    print("| Vector | Model | Leaks out of trials | Matching control | Strict (birthdate or canary) | Strict control |")
    print("|---|---|---|---|---|---|")
    for folder in folders:
        meta, rs = rows(folder)
        sc = strict_counts(folder)
        for name, stat, ctrl, hits in rs:
            print(f"| {name} | {label(meta)} | {cell(stat)} | {cell(ctrl)} | {strict_cell(sc, name)} | "
                  f"{strict_cell(sc, f'00_{name}_control')} |")


def compare(before, after):
    mb, rb = rows(before)
    ma, ra = rows(after)
    ra = {r[0]: r for r in ra}
    print(f"Before: {label(mb)}   After: {label(ma)}\n")
    sb, sa = strict_counts(before), strict_counts(after)
    print("| Vector | Before | After | Control before | Control after | Strict before | Strict after |")
    print("|---|---|---|---|---|---|---|")
    for name, stat, ctrl, _ in rb:
        a = ra.get(name)
        print(f"| {name} | {cell(stat)} | {cell(a[1]) if a else 'n/a'} | {cell(ctrl)} | "
              f"{cell(a[2]) if a else 'n/a'} | {strict_cell(sb, name)} | {strict_cell(sa, name)} |")


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
