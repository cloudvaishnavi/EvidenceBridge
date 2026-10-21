"""
Seed Data Script for EvidenceBridge.
Ingests sample clinical notes, hospital bills, and patient forum reports
into the EvidenceBridge extraction and provenance engine.

Usage:
    python scripts/seed_data.py [--url http://localhost:8000] [--file data/samples/samples.json]
"""

import argparse
import asyncio
import json
import os
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


async def ingest_via_api(api_base_url: str, samples: list[dict[str, Any]]) -> None:
    """Send each sample to the running FastAPI /extract endpoint."""
    extract_url = f"{api_base_url.rstrip('/')}/extract"
    health_url = f"{api_base_url.rstrip('/')}/health"

    print("=" * 70)
    print(" EvidenceBridge - Data Seeder")
    print(f" Target Endpoint: {extract_url}")
    print(f" Total Samples to Ingest: {len(samples)}")
    print("=" * 70)

    # Check health first
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            h_resp = await client.get(health_url)
            print(f"[✓] Backend health check: HTTP {h_resp.status_code}")
            h_data = h_resp.json()
            services = h_data.get("services", {})
            print(f"    - MongoDB: {services.get('mongodb', {}).get('status')}")
            print(f"    - Ollama:  {services.get('ollama', {}).get('status')} (model: {services.get('ollama', {}).get('configured_model')})")
        except Exception as e:
            print(f"[!] Warning: Health check failed ({e}). Proceeding with extraction anyway...")

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
                resp = await client.post(extract_url, json=payload)
                if resp.status_code in (200, 201):
                    data = resp.json()
                    claim = data.get("claim", {})
                    fields = claim.get("extracted_fields", {})
                    prov = claim.get("provenance", {})

                    print(f"    [✓] Extracted Claim ID: {claim.get('claim_id')}")
                    print(f"        • Entity:     {fields.get('entity')}")
                    print(f"        • Outcome:    {fields.get('effect_or_outcome')}")
                    print(f"        • Cost Range: {fields.get('cost_range') or 'None'}")
                    print(f"        • Location:   {fields.get('location_city') or 'None'}")
                    print(f"        • Sentiment:  {fields.get('sentiment')}")
                    print(f"        • Confidence: {claim.get('confidence')}")
                    print(f"        • SHA-256:    {prov.get('source_hash', '')[:16]}...")
                    print(f"        • Stored:     {data.get('stored')}")
                    success_count += 1
                else:
                    print(f"    [✗] HTTP {resp.status_code}: {resp.text}")
                    fail_count += 1
            except Exception as e:
                print(f"    [✗] Request failed: {e}")
                fail_count += 1

    print("\n" + "=" * 70)
    print(f" Seeding Complete: {success_count} succeeded, {fail_count} failed.")
    print("=" * 70)


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

    args = parser.parse_args()
    samples_path = Path(args.file)

    if not samples_path.exists():
        print(f"Error: Sample path '{samples_path}' does not exist.")
        sys.exit(1)

    samples = load_samples(samples_path)
    asyncio.run(ingest_via_api(args.url, samples))


if __name__ == "__main__":
    main()
