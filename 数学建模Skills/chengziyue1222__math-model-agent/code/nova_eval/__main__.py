"""Command line entry point for ``python -m nova_eval benchmark``."""

from __future__ import annotations

import argparse
import json

from .runner import run_benchmark
from .p05 import adjudicate_final_output, run_p05, run_v02_challenge


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m nova_eval")
    command = parser.add_subparsers(dest="command", required=True)
    benchmark = command.add_parser("benchmark", help="run the controlled P0 benchmark")
    benchmark.add_argument("--seed", type=int, default=20260810)
    benchmark.add_argument("--cases", type=int, default=84, help="minimum total cases; rounded up evenly across families")
    benchmark.add_argument("--output", default="artifacts/nova_eval_v0_1")
    benchmark.add_argument("--baseline", default="all", help="all or comma-separated nova,fixed-early-stop,fixed-all,surface-metric,llm-only")
    benchmark.add_argument("--partition", choices=("dev", "calibration", "hidden", "challenge"), default="hidden")
    p05 = command.add_parser("p05", help="run P0.5 semantic audit and the single v0.2 final evaluation")
    p05.add_argument("--repo", default=".")
    p05.add_argument("--output", default="artifacts/nova_eval_v0_2")
    p05.add_argument("--seed", type=int, default=20260920)
    challenge = command.add_parser("p05-challenge", help="run the post-final non-tuning P0.5 challenge set")
    challenge.add_argument("--output", default="artifacts/nova_eval_v0_2/challenge_set")
    challenge.add_argument("--seed", type=int, default=20260921)
    adjudicate = command.add_parser("p05-adjudicate", help="write a post-final failure addendum without rerunning the final")
    adjudicate.add_argument("--output", default="artifacts/nova_eval_v0_2")
    args = parser.parse_args()
    if args.command == "benchmark":
        result = run_benchmark(seed=args.seed, cases=args.cases, output=args.output, baselines=[item.strip() for item in args.baseline.split(",")], partition=args.partition)
        print(json.dumps({"output": result["output"], "strategies": result["summary"]["strategies"], "failure_count": len(result["failures"])}, ensure_ascii=False, indent=2))
    if args.command == "p05":
        result = run_p05(args.repo, args.output, seed=args.seed)
        print(json.dumps({"output": args.output, "final_manifest": result["manifest"], "strategies": result["summary"]["strategies"]}, ensure_ascii=False, indent=2))
    if args.command == "p05-challenge":
        result = run_v02_challenge(args.output, seed=args.seed)
        print(json.dumps({"output": args.output, **result}, ensure_ascii=False, indent=2))
    if args.command == "p05-adjudicate":
        result = adjudicate_final_output(args.output)
        print(json.dumps({"output": args.output, "adjudicated_failure_count": len(result)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
