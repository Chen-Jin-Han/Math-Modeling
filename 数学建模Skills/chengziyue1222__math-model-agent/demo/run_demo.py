"""Run one fixed, local Zhigan Nova competition demonstration case."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "code"
for path in (PROJECT_ROOT, CODE_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from demo.cases import available_cases, get_case
from demo.reporting import diagnosis_console_report, diagnosis_markdown
from nova_api.services import DiagnosisApiService


def run_case(case_id: str, output_root: Path) -> tuple[dict[str, object], dict[str, object]]:
    """Invoke the existing API service, then retrieve its full Core result."""

    case = get_case(case_id)
    service = DiagnosisApiService(artifact_root=output_root)
    summary = service.run(case.request)
    full_run = service.get(str(summary["run_id"]), full=True)
    if full_run is None:
        raise RuntimeError("Nova completed a run but the saved diagnosis record was not found.")
    return summary, full_run


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    cases = available_cases()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=tuple(cases), default="CASE-DEMO-001", help="Fixed competition case to run.")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "demo" / "outputs", help="Directory for this run's traceable artifacts.")
    parser.add_argument("--save-report", action="store_true", help="Also save a Markdown copy beside the generated run artifacts.")
    args = parser.parse_args()

    case = get_case(args.case)
    summary, full_run = run_case(case.case_id, args.output_root)
    gate = str(summary["gate"]["decision"])
    if gate != case.expected_gate:
        raise RuntimeError(f"Demo case expected {case.expected_gate}, but Nova returned {gate}.")

    report = diagnosis_console_report(case.title, full_run)
    print(report)
    if args.save_report:
        report_path = args.output_root / str(summary["run_id"]) / "competition_report.md"
        report_path.write_text(diagnosis_markdown(case.title, full_run), encoding="utf-8")
        print(f"\n已导出报告：{report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
