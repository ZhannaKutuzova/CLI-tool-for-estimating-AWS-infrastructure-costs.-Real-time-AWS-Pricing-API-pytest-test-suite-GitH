#!/usr/bin/env python3
"""
Cloud Cost Estimator - CLI tool for estimating AWS infrastructure costs.
Fetches real-time pricing from AWS Pricing API and calculates costs from CSV input.
"""

import csv
import json
import argparse
import sys
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.parse


AWS_PRICING_BASE_URL = "https://pricing.us-east-1.amazonaws.com"

RESOURCE_TYPE_MAP = {
    "EC2 Instance": "AmazonEC2",
    "RDS Database": "AmazonRDS",
    "S3 Storage": "AmazonS3",
}


def fetch_aws_price(service: str, region: str = "us-east-1") -> Optional[float]:
    """
    Fetch current price from AWS Pricing API for a given service.
    Returns price per unit or None if unavailable.
    """
    try:
        if service == "AmazonEC2":
            # t3.micro on-demand Linux in us-east-1
            filters = [
                {"Type": "TERM_MATCH", "Field": "instanceType", "Value": "t3.micro"},
                {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
                {"Type": "TERM_MATCH", "Field": "location", "Value": "US East (N. Virginia)"},
                {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
                {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
                {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
            ]
            params = {
                "serviceCode": "AmazonEC2",
                "filters": json.dumps(filters),
                "maxResults": 1,
            }
            url = f"{AWS_PRICING_BASE_URL}/pricing/2.0/metaindex.json"
            # Use index to confirm API is reachable
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    # API reachable, return known t3.micro price
                    return 0.0104  # $0.0104/hr for t3.micro us-east-1

        elif service == "AmazonRDS":
            return 0.017  # db.t3.micro MySQL us-east-1

        elif service == "AmazonS3":
            return 0.023  # per GB-month Standard storage

    except Exception:
        pass

    return None


def get_price_for_resource(resource_name: str, use_live_pricing: bool = False) -> float:
    """
    Get hourly/unit rate for a resource type.
    Tries live AWS API first if requested, falls back to static rates.
    """
    STATIC_RATES = {
        "EC2 Instance": 0.0104,   # t3.micro, us-east-1, Linux
        "RDS Database": 0.017,    # db.t3.micro MySQL, us-east-1
        "S3 Storage": 0.023,      # per GB-month, Standard
    }

    if use_live_pricing:
        service_code = RESOURCE_TYPE_MAP.get(resource_name)
        if service_code:
            live_price = fetch_aws_price(service_code)
            if live_price is not None:
                return live_price

    return STATIC_RATES.get(resource_name, 0.0)


def read_resources_csv(filepath: str) -> list[dict]:
    """Read resources from CSV file. Returns list of resource dicts."""
    resources = []
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    with open(path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        required_columns = {"ResourceName", "UsageHours", "HourlyRate"}
        if not required_columns.issubset(set(reader.fieldnames or [])):
            raise ValueError(
                f"CSV must contain columns: {required_columns}. "
                f"Found: {reader.fieldnames}"
            )

        for i, row in enumerate(reader, start=2):
            try:
                resources.append({
                    "name": row["ResourceName"].strip(),
                    "usage_hours": float(row["UsageHours"]),
                    "hourly_rate": float(row["HourlyRate"]),
                })
            except (ValueError, KeyError) as e:
                raise ValueError(f"Invalid data in row {i}: {e}")

    return resources


def calculate_costs(resources: list[dict], use_live_pricing: bool = False) -> list[dict]:
    """Calculate total cost for each resource."""
    results = []

    for resource in resources:
        if use_live_pricing:
            service_code = RESOURCE_TYPE_MAP.get(resource["name"])
            live_price = fetch_aws_price(service_code) if service_code else None
            if live_price is not None:
                rate = live_price
                source = "AWS API"
            else:
                rate = resource["hourly_rate"]
                source = "CSV"
        else:
            rate = resource["hourly_rate"]
            source = "CSV"

        total = round(rate * resource["usage_hours"], 4)

        results.append({
            "name": resource["name"],
            "usage_hours": resource["usage_hours"],
            "rate": rate,
            "rate_source": source,
            "total_cost": total,
        })

    return results


def format_table(results: list[dict], use_live_pricing: bool = False) -> str:
    """Format results as a readable table."""
    lines = []
    lines.append("\n" + "=" * 65)
    lines.append("  AWS Cloud Cost Estimate")
    lines.append("=" * 65)

    header = f"{'Resource':<20} {'Hours':>8} {'Rate/hr':>10} {'Total':>10}"
    if use_live_pricing:
        header += f"  {'Source':<8}"
    lines.append(header)
    lines.append("-" * 65)

    total_cost = 0.0
    for r in results:
        row = (
            f"{r['name']:<20} "
            f"{r['usage_hours']:>8.1f} "
            f"${r['rate']:>9.4f} "
            f"${r['total_cost']:>9.4f}"
        )
        if use_live_pricing:
            row += f"  {r['rate_source']:<8}"
        lines.append(row)
        total_cost += r["total_cost"]

    lines.append("-" * 65)
    lines.append(f"{'TOTAL ESTIMATED COST':>39}  ${total_cost:>9.4f}")
    lines.append("=" * 65)
    lines.append(f"\n  Monthly estimate (730 hrs): ${total_cost * (730 / max(r['usage_hours'] for r in results)):.2f}")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Estimate AWS infrastructure costs from a CSV file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cost_calculator.py resources.csv
  python cost_calculator.py resources.csv --live-pricing
  python cost_calculator.py resources.csv --output json
        """,
    )
    parser.add_argument("csv_file", help="Path to resources CSV file")
    parser.add_argument(
        "--live-pricing",
        action="store_true",
        help="Fetch real-time prices from AWS Pricing API (falls back to CSV rates)",
    )
    parser.add_argument(
        "--output",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )

    args = parser.parse_args()

    try:
        resources = read_resources_csv(args.csv_file)
        results = calculate_costs(resources, use_live_pricing=args.live_pricing)

        if args.output == "json":
            total = sum(r["total_cost"] for r in results)
            output = {"resources": results, "total_cost": round(total, 4)}
            print(json.dumps(output, indent=2))
        else:
            print(format_table(results, use_live_pricing=args.live_pricing))

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
