"""
Tests for Cloud Cost Estimator
"""

import json
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from cost_calculator import (
    read_resources_csv,
    calculate_costs,
    get_price_for_resource,
    format_table,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────

VALID_CSV_CONTENT = """ResourceName,UsageHours,HourlyRate
EC2 Instance,50,0.024
RDS Database,100,0.1
S3 Storage,20,0.005
"""

INVALID_CSV_MISSING_COLUMN = """ResourceName,Hours
EC2 Instance,50
"""

INVALID_CSV_BAD_VALUE = """ResourceName,UsageHours,HourlyRate
EC2 Instance,not_a_number,0.024
"""


@pytest.fixture
def valid_csv_file(tmp_path):
    f = tmp_path / "resources.csv"
    f.write_text(VALID_CSV_CONTENT)
    return str(f)


@pytest.fixture
def invalid_columns_csv(tmp_path):
    f = tmp_path / "bad_columns.csv"
    f.write_text(INVALID_CSV_MISSING_COLUMN)
    return str(f)


@pytest.fixture
def invalid_values_csv(tmp_path):
    f = tmp_path / "bad_values.csv"
    f.write_text(INVALID_CSV_BAD_VALUE)
    return str(f)


@pytest.fixture
def sample_resources():
    return [
        {"name": "EC2 Instance", "usage_hours": 50.0, "hourly_rate": 0.024},
        {"name": "RDS Database", "usage_hours": 100.0, "hourly_rate": 0.1},
        {"name": "S3 Storage", "usage_hours": 20.0, "hourly_rate": 0.005},
    ]


# ─── CSV Reading ─────────────────────────────────────────────────────────────

class TestReadResourcesCsv:
    def test_reads_valid_csv(self, valid_csv_file):
        resources = read_resources_csv(valid_csv_file)
        assert len(resources) == 3

    def test_parses_resource_names(self, valid_csv_file):
        resources = read_resources_csv(valid_csv_file)
        assert resources[0]["name"] == "EC2 Instance"
        assert resources[1]["name"] == "RDS Database"
        assert resources[2]["name"] == "S3 Storage"

    def test_parses_numeric_values(self, valid_csv_file):
        resources = read_resources_csv(valid_csv_file)
        assert resources[0]["usage_hours"] == 50.0
        assert resources[0]["hourly_rate"] == 0.024

    def test_raises_for_missing_file(self):
        with pytest.raises(FileNotFoundError):
            read_resources_csv("/nonexistent/path/resources.csv")

    def test_raises_for_missing_columns(self, invalid_columns_csv):
        with pytest.raises(ValueError, match="CSV must contain columns"):
            read_resources_csv(invalid_columns_csv)

    def test_raises_for_invalid_numeric_value(self, invalid_values_csv):
        with pytest.raises(ValueError, match="Invalid data in row"):
            read_resources_csv(invalid_values_csv)


# ─── Cost Calculation ────────────────────────────────────────────────────────

class TestCalculateCosts:
    def test_calculates_correct_totals(self, sample_resources):
        results = calculate_costs(sample_resources)
        assert results[0]["total_cost"] == pytest.approx(1.2, rel=1e-4)    # 50 * 0.024
        assert results[1]["total_cost"] == pytest.approx(10.0, rel=1e-4)   # 100 * 0.1
        assert results[2]["total_cost"] == pytest.approx(0.1, rel=1e-4)    # 20 * 0.005

    def test_result_contains_all_fields(self, sample_resources):
        results = calculate_costs(sample_resources)
        for r in results:
            assert "name" in r
            assert "usage_hours" in r
            assert "rate" in r
            assert "total_cost" in r
            assert "rate_source" in r

    def test_rate_source_is_csv_by_default(self, sample_resources):
        results = calculate_costs(sample_resources)
        assert all(r["rate_source"] == "CSV" for r in results)

    def test_zero_usage_hours(self):
        resources = [{"name": "EC2 Instance", "usage_hours": 0.0, "hourly_rate": 0.024}]
        results = calculate_costs(resources)
        assert results[0]["total_cost"] == 0.0

    def test_total_cost_across_all_resources(self, sample_resources):
        results = calculate_costs(sample_resources)
        total = sum(r["total_cost"] for r in results)
        assert total == pytest.approx(11.3, rel=1e-3)

    def test_empty_resources_returns_empty_list(self):
        results = calculate_costs([])
        assert results == []


# ─── Static Pricing ──────────────────────────────────────────────────────────

class TestGetPriceForResource:
    def test_known_ec2_price(self):
        price = get_price_for_resource("EC2 Instance")
        assert price == pytest.approx(0.0104, rel=1e-3)

    def test_known_rds_price(self):
        price = get_price_for_resource("RDS Database")
        assert price == pytest.approx(0.017, rel=1e-3)

    def test_known_s3_price(self):
        price = get_price_for_resource("S3 Storage")
        assert price == pytest.approx(0.023, rel=1e-3)

    def test_unknown_resource_returns_zero(self):
        price = get_price_for_resource("Unknown Resource Type")
        assert price == 0.0


# ─── Live Pricing (mocked) ───────────────────────────────────────────────────

class TestLivePricing:
    def test_falls_back_to_csv_rate_when_api_fails(self, sample_resources):
        with patch("cost_calculator.fetch_aws_price", return_value=None):
            results = calculate_costs(sample_resources, use_live_pricing=True)
            assert results[0]["rate_source"] == "CSV"

    def test_uses_live_rate_when_api_succeeds(self, sample_resources):
        with patch("cost_calculator.fetch_aws_price", return_value=0.0104):
            results = calculate_costs(sample_resources, use_live_pricing=True)
            ec2_result = next(r for r in results if r["name"] == "EC2 Instance")
            assert ec2_result["rate_source"] == "AWS API"
            assert ec2_result["rate"] == pytest.approx(0.0104)


# ─── Output Formatting ───────────────────────────────────────────────────────

class TestFormatTable:
    def test_output_contains_resource_names(self, sample_resources):
        results = calculate_costs(sample_resources)
        output = format_table(results)
        assert "EC2 Instance" in output
        assert "RDS Database" in output
        assert "S3 Storage" in output

    def test_output_contains_total(self, sample_resources):
        results = calculate_costs(sample_resources)
        output = format_table(results)
        assert "TOTAL" in output

    def test_output_contains_monthly_estimate(self, sample_resources):
        results = calculate_costs(sample_resources)
        output = format_table(results)
        assert "Monthly estimate" in output

    def test_output_contains_source_column_when_live(self, sample_resources):
        results = calculate_costs(sample_resources)
        output = format_table(results, use_live_pricing=True)
        assert "Source" in output
