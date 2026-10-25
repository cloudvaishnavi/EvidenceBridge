#!/usr/bin/env python3
"""
CLI Evaluation Runner for EvidenceBridge (Layer 6).
Triggers benchmark evaluation over labeled clinical claims, displays formatted
statistical performance and calibration tables, and optionally exports Markdown/JSON reports.

Usage:
    python scripts/run_evaluation.py
    python scripts/run_evaluation.py --dataset data/evaluation/controlled_cases.json
    python scripts/run_evaluation.py --save-md evaluation_report.md
    python scripts/run_evaluation.py --save-json evaluation_report.json
"""

import argparse
import asyncio
import json
from pathlib import Path
import sys

# Ensure backend directory is in python path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Handle Windows cp1252 output encoding safely
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.services.evaluation import evaluation_service
from app.services.storage import storage_service


def print_banner():
    print("=" * 78)
    print("  EvidenceBridge: Clinical Evidence & Cost Audit Evaluation Harness")
    print("  Layer 6: Verdict Precision/Recall/F1, Action Accuracy & ECE Calibration")
    print("=" * 78)


def format_table_row(col1: str, col2: str, col3: str, col4: str, col5: str, widths=(24, 12, 12, 12, 12)) -> str:
    return f"{col1:<{widths[0]}} {col2:>{widths[1]}} {col3:>{widths[2]}} {col4:>{widths[3]}} {col5:>{widths[4]}}"


def display_terminal_summary(report):
    print(f"\n[Run ID]    {report.run_id}")
    print(f"[Timestamp] {report.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"[Dataset]   {report.dataset_name} ({report.total_samples} samples)")
    print("-" * 78)

    print("\n-- 1. EXECUTIVE PERFORMANCE SUMMARY --")
    print("-" * 78)
    print(f"  * Overall Verdict Accuracy:          {report.overall_verdict_accuracy * 100:.1f}%")
    print(f"  * Macro Verdict F1:                  {report.macro_verdict_f1:.4f}")
    print(f"  * Overall Action Accuracy:           {report.overall_action_accuracy * 100:.1f}%")
    print(f"  * Macro Action F1:                   {report.macro_action_f1:.4f}")
    print(f"  * Cost Anomaly Detection F1:         {report.cost_anomaly_metrics.f1_score:.4f}")
    print(f"  * Abstention Safety Recall:          {report.abstention_metrics.abstention_recall * 100:.1f}%")
    print(f"  * Expected Calibration Error (ECE):  {report.expected_calibration_error:.4f}")

    print("\n-- 2. VERDICT CLASSIFICATION BREAKDOWN --")
    print("-" * 78)
    header = format_table_row("Verdict Class", "Precision", "Recall", "F1 Score", "Support")
    print(header)
    print("-" * 78)
    for c, m in report.verdict_metrics.items():
        row = format_table_row(
            c,
            f"{m.precision:.3f}",
            f"{m.recall:.3f}",
            f"{m.f1_score:.3f}",
            str(m.support_count),
        )
        print(row)

    print("\n-- 3. TRIAGE ACTION BREAKDOWN (ACCEPT / FLAG / ABSTAIN) --")
    print("-" * 78)
    header_act = format_table_row("Action", "Precision", "Recall", "F1 Score", "Support")
    print(header_act)
    print("-" * 78)
    for a, m in report.action_metrics.items():
        row = format_table_row(
            a,
            f"{m.precision:.3f}",
            f"{m.recall:.3f}",
            f"{m.f1_score:.3f}",
            str(m.support_count),
        )
        print(row)

    print("\n-- 4. COST ANOMALY DETECTION PERFORMANCE --")
    print("-" * 78)
    ca = report.cost_anomaly_metrics
    print(f"  * Precision:  {ca.precision * 100:.1f}% ({ca.true_positives}/{ca.predicted_count} predicted anomalies confirmed)")
    print(f"  * Recall:     {ca.recall * 100:.1f}% ({ca.true_positives}/{ca.support_count} ground-truth anomalies detected)")
    print(f"  * F1 Score:   {ca.f1_score:.4f}")
    print(f"  * False Positives: {ca.false_positives} | False Negatives: {ca.false_negatives}")

    print("\n-- 5. ABSTENTION SAFETY GATE CALIBRATION --")
    print("-" * 78)
    abs_m = report.abstention_metrics
    print(f"  * Total Abstained:       {abs_m.total_abstained}/{abs_m.total_samples} ({abs_m.abstention_rate * 100:.1f}%)")
    print(f"  * Correct Abstentions:   {abs_m.correct_abstentions}")
    print(f"  * Over-Abstentions:      {abs_m.over_abstentions} (excessive refusals on valid claims)")
    print(f"  * Under-Abstentions:     {abs_m.under_abstentions} (dangerous assertions without evidence)")
    print(f"  * Abstention F1 Score:   {abs_m.abstention_f1:.4f}")

    print("\n-- 6. RELIABILITY CALIBRATION BINS (ECE) --")
    print("-" * 78)
    header_cal = format_table_row("Bin Interval", "Count", "Avg Conf", "Emp Accuracy", "Cal Error")
    print(header_cal)
    print("-" * 78)
    for b in report.calibration_bins:
        interval_str = f"[{b.bin_lower:.2f}, {b.bin_upper:.2f})"
        row = format_table_row(
            interval_str,
            str(b.sample_count),
            f"{b.avg_confidence:.3f}",
            f"{b.empirical_accuracy * 100:.1f}%",
            f"{b.calibration_error:.4f}",
        )
        print(row)
    print(f"  --> Weighted Expected Calibration Error: {report.expected_calibration_error:.4f}")

    print("\n-- 7. ACTIONABLE RECOMMENDATIONS --")
    print("-" * 78)
    for rec in report.recommendations:
        print(f"  -> {rec}")
    print("=" * 78)


async def main():
    parser = argparse.ArgumentParser(
        description="Run clinical evaluation harness across labeled benchmark cases."
    )
    parser.add_argument(
        "--dataset", "-d",
        type=str,
        default=None,
        help="Path to evaluation dataset JSON (default: data/evaluation/controlled_cases.json)"
    )
    parser.add_argument(
        "--save-md",
        type=str,
        default=None,
        help="Path to save output Markdown report (e.g. report.md)"
    )
    parser.add_argument(
        "--save-json",
        type=str,
        default=None,
        help="Path to save output JSON report (e.g. report.json)"
    )
    parser.add_argument(
        "--force-reverify",
        action="store_true",
        help="Force re-verifying claims even if cached results exist in MongoDB"
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run evaluation using deterministic local guidelines without calling Ollama LLM"
    )

    args = parser.parse_args()

    print_banner()

    # Connect storage if available
    try:
        await storage_service.connect()
    except Exception as e:
        print(f"⚠️  Note: MongoDB connection deferred or offline ({e}). Running in standalone mode.")

    print(f"🚀 Running evaluation over dataset...")
    try:
        report = await evaluation_service.run_evaluation(
            dataset_path=args.dataset,
            force_reverify=args.force_reverify,
            offline_mode=args.offline,
        )
    except Exception as e:
        print(f"❌ Evaluation run failed: {e}")
        sys.exit(1)

    display_terminal_summary(report)

    # Optional export
    if args.save_md:
        out_path = Path(args.save_md)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report.markdown_report)
        print(f"\n💾 Markdown report saved to: {out_path.resolve()}")

    if args.save_json:
        out_path = Path(args.save_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))
        print(f"💾 JSON report saved to:     {out_path.resolve()}")

    # Cleanup storage
    try:
        await storage_service.close()
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(main())
