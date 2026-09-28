#!/usr/bin/env python3
"""
compute_f1.py — Compute Precision / Recall / F1 for citation matching
between a ground-truth paper and a generated paper, partitioned by
P0 (must-cite) and P1 (good-to-cite).

Implements the Citation F1 metric from arXiv:2604.05018, §5.2 "Citation
F1" — uses Semantic Scholar paper IDs to match references between the two
lists.

Inputs:
  --gt-partition  JSON dict {ref_num: "P0"|"P1"} from the autorater for the GT paper
  --gt-refs       JSON list [{ref_num, paper_id, title}] for the GT references
  --gen-partition same shape, for the generated paper
  --gen-refs      same shape, for the generated references

Output: JSON report at --out with P0 / P1 / overall P / R / F1.

Usage:
    python compute_f1.py \\
        --gt-partition gt_partition.json \\
        --gt-refs gt_refs.json \\
        --gen-partition gen_partition.json \\
        --gen-refs gen_refs.json \\
        --out f1_report.json
"""
import argparse
import json
import sys


def precision_recall_f1(gt_set: set[str], gen_set: set[str]) -> dict:
    if not gen_set and not gt_set:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0,
                "n_gt": 0, "n_gen": 0, "n_intersection": 0}
    intersection = gt_set & gen_set
    p = len(intersection) / len(gen_set) if gen_set else 0.0
    r = len(intersection) / len(gt_set) if gt_set else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return {
        "precision":      round(p, 4),
        "recall":         round(r, 4),
        "f1":             round(f1, 4),
        "n_gt":           len(gt_set),
        "n_gen":          len(gen_set),
        "n_intersection": len(intersection),
    }


def build_id_set(refs: list[dict], partition: dict[str, str], wanted: set[str]) -> set[str]:
    """Return the set of S2 paper IDs whose ref_num falls into one of the
    wanted partitions (e.g., {"P0"})."""
    ids: set[str] = set()
    for ref in refs:
        num = str(ref.get("ref_num"))
        pid = ref.get("paper_id") or ref.get("paperId")
        if not pid:
            continue
        if partition.get(num) in wanted:
            ids.add(str(pid))
    return ids


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gt-partition",  required=True)
    p.add_argument("--gt-refs",       required=True)
    p.add_argument("--gen-partition", required=True)
    p.add_argument("--gen-refs",      required=True)
    p.add_argument("--out",           required=True)
    args = p.parse_args()

    try:
        gt_part  = json.load(open(args.gt_partition))
        gt_refs  = json.load(open(args.gt_refs))
        gen_part = json.load(open(args.gen_partition))
        gen_refs = json.load(open(args.gen_refs))
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: failed to load inputs: {e}", file=sys.stderr)
        return 1

    p0_gt  = build_id_set(gt_refs,  gt_part,  {"P0"})
    p0_gen = build_id_set(gen_refs, gen_part, {"P0"})
    p1_gt  = build_id_set(gt_refs,  gt_part,  {"P1"})
    p1_gen = build_id_set(gen_refs, gen_part, {"P1"})
    all_gt  = p0_gt  | p1_gt
    all_gen = p0_gen | p1_gen

    report = {
        "P0":      precision_recall_f1(p0_gt,  p0_gen),
        "P1":      precision_recall_f1(p1_gt,  p1_gen),
        "overall": precision_recall_f1(all_gt, all_gen),
    }

    with open(args.out, "w") as f:
        json.dump(report, f, indent=2)

    for name, m in report.items():
        print(f"{name:8s}  P={m['precision']:.3f}  R={m['recall']:.3f}  F1={m['f1']:.3f}  "
              f"(intersect={m['n_intersection']}/gen={m['n_gen']}/gt={m['n_gt']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
