"""
Seed Data Script for EvidenceBridge (Layer 4).
Ingests and verifies sample clinical notes, hospital bills, and patient forum reports
against local knowledge base guidelines and price benchmarks.
After seeding, displays per-location trust density summary table.

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
    seeded_locations: set[str] = set()

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

                    print(f"    [OK] Claim ID:    {claim.get('claim_id')}")
                    print(f"         Entity:      {fields.get('entity')}")
                    print(f"         Cost:        {fields.get('cost_range') or 'None'}")

                    # Track locations for trust density recompute
                    loc = claim.get("location") or {}
                    loc_key = loc.get("normalized_key")
                    if loc_key:
                        seeded_locations.add(loc_key)
                        loc_display = f"{loc.get('city')}, {loc.get('state_or_region')}" if loc.get("state_or_region") else loc.get("city", loc_key)
                        print(f"         Location:    {loc_display} [{loc_key}]")

                    if verify and "verification" in data:
                        verif = data["verification"]
                        verdict = verif.get("verdict")
                        action = verif.get("action")
                        score = verif.get("support_score")
                        is_anomaly = verif.get("cost_anomaly_flag")
                        anomaly = verif.get("anomaly_details") or {}

                        action_badge = {
                            "accept": "[ACCEPT]",
                            "flag": "[FLAG]",
                            "abstain": "[ABSTAIN]"
                        }.get(action, f"[{action.upper()}]")

                        print(f"         ------------------------------------------------")
                        print(f"         Action:      {action_badge}")
                        print(f"         Verdict:     {verdict} (score: {score})")
                        print(f"         Cost Flag:   {'ANOMALY' if is_anomaly else 'OK'}")
                        if is_anomaly:
                            print(f"         Severity:    {anomaly.get('severity', '').upper()} ({anomaly.get('multiplier')}x benchmark)")
                        if verif.get("abstain_reason"):
                            print(f"         Abstain:     {verif.get('abstain_reason')[:80]}")

                    success_count += 1
                else:
                    print(f"    [FAIL] HTTP {resp.status_code}: {resp.text[:120]}")
                    fail_count += 1
            except Exception as e:
                print(f"    [FAIL] Request failed: {e}")
                fail_count += 1

    print("\n" + "=" * 80)
    print(f" Processing Complete: {success_count} succeeded, {fail_count} failed.")
    print("=" * 80)

    # -- Layer 4: Recompute & display Trust Density for seeded locations --
    if seeded_locations and verify:
        print(f"\n[Layer 4] Recomputing trust density for {len(seeded_locations)} location(s)...")
        print("-" * 80)
        async with httpx.AsyncClient(timeout=30.0) as client:
            for loc_key in sorted(seeded_locations):
                try:
                    r = await client.post(f"{base}/trust-density/{loc_key}/recompute")
                    if r.status_code == 200:
                        td = r.json()
                        m = td.get("metrics", {})
                        insight = td.get("insight", {})
                        tier = m.get("trust_tier", "?").upper()
                        score = m.get("density_score", 0.0)
                        total = m.get("total_claims", 0)
                        anomaly_rate = m.get("cost_anomaly_rate", 0.0)
                        print(f"  {loc_key:<20} | Tier: {tier:<18} | Score: {score:.3f} | Claims: {total} | Anomaly Rate: {anomaly_rate:.1%}")
                        if insight and insight.get("summary_text"):
                            print(f"    Insight: {insight['summary_text'][:100]}")
                    elif r.status_code == 404:
                        print(f"  {loc_key:<20} | No claims with verifications yet (run with --verify flag)")
                    else:
                        print(f"  {loc_key:<20} | Error: HTTP {r.status_code}")
                except Exception as e:
                    print(f"  {loc_key:<20} | Recompute error: {e}")
        print("-" * 80)
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
