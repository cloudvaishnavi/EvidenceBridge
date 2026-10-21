"""
Seed Data Script for EvidenceBridge (Layer 2).
Ingests and verifies sample clinical notes, hospital bills, and patient forum reports
against local knowledge base guidelines and price benchmarks.

Usage:
    python scripts/seed_data.py [--url http://localhost:8000] [--file data/samples/samples.json] [--verify]
"""

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any
import httpx


def load_samples(samples_path: Path) -> list[dict[str, Any]]:
    """Load samples from json array file or directory of individual json files."""
    if samples_path.is_file():
        with open(samples_path, "r", encoding="utf-8") as f:
            return json.load(f)

    if samples_path.is_dir():
        samples = []
        for file in sorted(samples_path.glob("*.json")):
            if file.name == "samples.json":
                continue
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    samples.extend(data)
                elif isinstance(data, dict):
                    samples.append(data)
        return samples

    raise FileNotFoundError(f"Sample path not found: {samples_path}")


async def ingest_via_api(api_base_url: str, samples: list[dict[str, Any]], verify: bool = False) -> None:
    """Send each sample to the running FastAPI backend."""
    base = api_base_url.rstrip("/")
    endpoint = f"{base}/extract-and-verify" if verify else f"{base}/extract"
    health_url = f"{base}/health"

    print("=" * 80)
    print(" EvidenceBridge - Data Seeder & Claim Auditor")
    print(f" Target Endpoint: {endpoint}")
    print(f" Mode:            {'Extraction + Claim Verification + Cost Anomaly Audit' if verify else 'Extraction + Provenance Only'}")
    print(f" Total Samples:   {len(samples)}")
    print("=" * 80)

    # Check health first
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            h_resp = await client.get(health_url)
            print(f"[✓] Backend health check: HTTP {h_resp.status_code}")
            h_data = h_resp.json()
            services = h_data.get("services", {})
            print(f"    - MongoDB:      {services.get('mongodb', {}).get('status')}")
            print(f"    - Ollama:       {services.get('ollama', {}).get('status')} (model: {services.get('ollama', {}).get('configured_model')})")
            print(f"    - Vector Store: {services.get('vector_store', {}).get('status')}")
        except Exception as e:
            print(f"[!] Warning: Health check failed ({e}). Proceeding anyway...")

    success_count = 0
    fail_count = 0

    async with httpx.AsyncClient(timeout=120.0) as client:
        for idx, item in enumerate(samples, start=1):
            sample_id = item.get("id", f"sample_{idx}")
            text = item.get("text", "").strip()
            source_type = item.get("source_type", "clinical_note")
            source_url = item.get("source_url")

            print(f"\n[{idx}/{len(samples)}] Ingesting {sample_id} ({source_type})...")
            payload = {
                "text": text,
                "source_type": source_type,
                "source_url": source_url,
                "store_claim": True
            }

            try:
                resp = await client.post(endpoint, json=payload)
                if resp.status_code in (200, 201):
                    data = resp.json()
                    claim = data.get("claim", {})
                    fields = claim.get("extracted_fields", {})
                    prov = claim.get("provenance", {})

                    print(f"    [✓] Claim ID:    {claim.get('claim_id')}")
                    print(f"        • Entity:     {fields.get('entity')}")
                    print(f"        • Outcome:    {fields.get('effect_or_outcome')}")
                    print(f"        • Cost:       {fields.get('cost_range') or 'None'}")
                    print(f"        • Sentiment:  {fields.get('sentiment')}")
                    print(f"        • Confidence: {claim.get('confidence')}")

                    if verify and "verification" in data:
                        verif = data["verification"]
                        verdict = verif.get("verdict")
                        action = verif.get("action")
                        score = verif.get("support_score")
                        is_anomaly = verif.get("cost_anomaly_flag")
                        anomaly = verif.get("anomaly_details") or {}

                        action_badge = {
                            "accept": "[ACCEPT - VERIFIED]",
                            "flag": "[FLAG - SUSPICIOUS/CONTRADICTED]",
                            "abstain": "[ABSTAIN - INSUFFICIENT EVIDENCE]"
                        }.get(action, f"[{action.upper()}]")

                        print(f"        --------------------------------------------------------")
                        print(f"        • Action:     {action_badge}")
                        print(f"        • Verdict:    {verdict} (support score: {score})")
                        print(f"        • Cost Flag:  {'⚠️ ANOMALY DETECTED' if is_anomaly else '✓ Normal / Unflagged'}")
                        if is_anomaly:
                            print(f"          Severity:   {anomaly.get('severity', '').upper()} ({anomaly.get('multiplier')}× max benchmark)")
                            print(f"          Detail:     {anomaly.get('explanation')}")
                        if verif.get("abstain_reason"):
                            print(f"          Abstain:    {verif.get('abstain_reason')}")
                        print(f"        • Audit:      {verif.get('reasoning')}")

                    success_count += 1
                else:
                    print(f"    [✗] HTTP {resp.status_code}: {resp.text}")
                    fail_count += 1
            except Exception as e:
                print(f"    [✗] Request failed: {e}")
                fail_count += 1

    print("\n" + "=" * 80)
    print(f" Processing Complete: {success_count} succeeded, {fail_count} failed.")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Seed EvidenceBridge with sample clinical & billing records.")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="FastAPI base URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--file",
        default=str(Path(__file__).parent.parent / "data" / "samples" / "samples.json"),
        help="Path to samples.json or directory with samples"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run claim verification and cost anomaly detection in addition to extraction"
    )

    args = parser.parse_args()
    samples_path = Path(args.file)

    if not samples_path.exists():
        print(f"Error: Sample path '{samples_path}' does not exist.")
        sys.exit(1)

    samples = load_samples(samples_path)
    asyncio.run(ingest_via_api(args.url, samples, verify=args.verify))


if __name__ == "__main__":
    main()
