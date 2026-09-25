"""CLI entrypoint for executing the 14-Case Benchmark Evaluation Test Suite."""

import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend root is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.evaluation.runner import EvaluationRunner


def main():
    print("=" * 80)
    print("LEGAL INFORMATION NAVIGATOR — 14-CASE BENCHMARK EVALUATION TEST SUITE")
    print("=" * 80)

    runner = EvaluationRunner()
    scorecard = runner.run_all()

    print("\n" + scorecard.to_markdown() + "\n")
    print("=" * 80)
    print(f"RESULTS: {scorecard.passed_cases}/{scorecard.total_cases} PASSED ({scorecard.pass_rate_pct:.1f}%)")
    print(f"HALLUCINATION RATE: {scorecard.hallucination_rate_pct:.1f}%")
    print(f"AVERAGE LATENCY: {scorecard.avg_latency_ms:.1f} ms")
    print("=" * 80)

    if scorecard.failed_cases > 0:
        print(f"FAILED: {scorecard.failed_cases} test cases failed evaluation criteria.")
        sys.exit(1)
    else:
        print("SUCCESS: All 14 benchmark evaluation cases passed 100% with zero hallucinations.")
        sys.exit(0)


if __name__ == "__main__":
    main()
