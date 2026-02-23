# Cloud Cost Estimator ☁️

A CLI tool for estimating AWS infrastructure costs from a CSV file.
Supports both static rates and real-time pricing via the **AWS Pricing API**.

![CI](https://github.com/ZhannaKutuzova/cloud-cost-estimator/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)

---

## Features

- Parse infrastructure resources from a CSV file
- Calculate costs using static rates or live AWS Pricing API
- Output as formatted table or JSON
- Zero external dependencies (uses stdlib only)
- Full test suite with pytest

---

## Quick Start

```bash
# Clone
git clone https://github.com/ZhannaKutuzova/cloud-cost-estimator.git
cd cloud-cost-estimator

# Run with sample data
python cost_calculator.py resources.csv

# Use live AWS Pricing API (no credentials needed)
python cost_calculator.py resources.csv --live-pricing

# Output as JSON
python cost_calculator.py resources.csv --output json
```

---

## CSV Format

```csv
ResourceName,UsageHours,HourlyRate
EC2 Instance,50,0.024
RDS Database,100,0.1
S3 Storage,20,0.005
```

Supported resource types: `EC2 Instance`, `RDS Database`, `S3 Storage`

---

## Sample Output

```
=================================================================
  AWS Cloud Cost Estimate
=================================================================
Resource             Hours       Rate/hr      Total
-----------------------------------------------------------------
EC2 Instance          50.0    $0.0240    $1.2000
RDS Database         100.0    $0.1000   $10.0000
S3 Storage            20.0    $0.0050    $0.1000
-----------------------------------------------------------------
                         TOTAL ESTIMATED COST      $11.3000
=================================================================

  Monthly estimate (730 hrs): $82.49
```

---

## Running Tests

```bash
pip install pytest pytest-cov
pytest test_cost_calculator.py -v --cov=cost_calculator
```

---

## Project Structure

```
cloud-cost-estimator/
├── cost_calculator.py       # Main CLI tool
├── test_cost_calculator.py  # Unit tests (pytest)
├── resources.csv            # Sample input data
└── .github/
    └── workflows/
        └── ci.yml           # GitHub Actions CI (Python 3.11, 3.12)
```

---

## Tech Stack

- Python 3.11+
- `urllib` (stdlib) — AWS Pricing API calls
- `csv`, `json`, `argparse` (stdlib) — parsing and CLI
- `pytest` — testing
- GitHub Actions — CI/CD
