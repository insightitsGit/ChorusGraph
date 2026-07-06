"""Tests for `chorusgraph audit` cold path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmark.shared.instrumented_gemini import _INPUT_USD_PER_M, _OUTPUT_USD_PER_M
from chorusgraph.audit.benchmark_reference import load_portfolio_benchmark
from chorusgraph.audit.cli import main
from chorusgraph.audit.ingest import detect_format, load_log
from chorusgraph.audit.ledger_report import (
    LEDGER_DISCLAIMER,
    analyze_ledger_run,
    format_ledger_console_report,
)
from chorusgraph.audit.report import DISCLAIMER, audit_to_dict, format_console_report
from chorusgraph.audit.simulate import gemini_cost_usd, run_cold_audit
from chorusgraph.cache_gate.thresholds import COARSE_THRESHOLD, measured_thresholds
from chorusgraph.ledger import LedgerStep, RouteLedger, SqliteLedgerSink

FIXTURES = Path(__file__).resolve().parent / "fixtures"
JSONL_FIXTURE = FIXTURES / "audit_cold_queries.jsonl"
CSV_FIXTURE = FIXTURES / "audit_cold_queries.csv"
PROMPT_CSV = FIXTURES / "audit_cold_queries_prompt.csv"
TEXT_CSV = FIXTURES / "audit_cold_queries_text.csv"

# Hand-verified with PrismlangOnnxEmbedder + measured_thresholds() gate defaults.
EXPECTED_HITS = 4
EXPECTED_TOTAL = 10
EXPECTED_HIT_RATE = 0.4
HIT_RATE_TOLERANCE = 0.05


def test_detect_format_jsonl_and_csv():
    assert detect_format(JSONL_FIXTURE) == "jsonl"
    assert detect_format(CSV_FIXTURE) == "csv"


def test_auto_detect_query_column_names():
    rows_question = load_log(CSV_FIXTURE)
    assert len(rows_question) == EXPECTED_TOTAL
    assert rows_question[0].query.startswith("What is the Acme Corp")

    rows_prompt = load_log(PROMPT_CSV)
    assert len(rows_prompt) == 2
    assert "return policy" in rows_prompt[1].query

    rows_text = load_log(TEXT_CSV)
    assert len(rows_text) == 2
    assert rows_text[0].query.startswith("What is the Acme Corp")


def test_jsonl_cold_audit_hit_rate_matches_known_answer():
    rows = load_log(JSONL_FIXTURE)
    result = run_cold_audit(rows)
    assert result.total_queries == EXPECTED_TOTAL
    assert result.simulated_hits == EXPECTED_HITS
    assert abs(result.simulated_hit_rate - EXPECTED_HIT_RATE) <= HIT_RATE_TOLERANCE
    assert result.coarse_threshold == COARSE_THRESHOLD
    assert result.verify_threshold == measured_thresholds().verify_for("general")
    assert result.date_range_start is not None
    assert result.has_token_counts is True


def test_csv_cold_audit_hit_rate_matches_known_answer():
    rows = load_log(CSV_FIXTURE)
    result = run_cold_audit(rows)
    assert result.simulated_hits == EXPECTED_HITS
    assert abs(result.simulated_hit_rate - EXPECTED_HIT_RATE) <= HIT_RATE_TOLERANCE


def test_report_includes_disclaimer_and_benchmark_comparison():
    rows = load_log(JSONL_FIXTURE)
    result = run_cold_audit(rows)
    text = format_console_report(result, log_path=str(JSONL_FIXTURE))
    assert DISCLAIMER in text
    assert "simulated" in text.lower()
    assert "Portfolio" in text
    assert "44%" in text or "35%" in text
    assert "Finance, single-agent" in text
    portfolio = load_portfolio_benchmark()
    assert portfolio.mean_llm_reduction_pct == pytest.approx(44.2, abs=0.5)
    assert portfolio.mean_cost_reduction_pct == pytest.approx(35.1, abs=0.5)


def test_token_cost_uses_benchmark_gemini_constants():
    cost = gemini_cost_usd(1_000_000, 1_000_000)
    assert cost == pytest.approx(_INPUT_USD_PER_M + _OUTPUT_USD_PER_M)
    rows = load_log(JSONL_FIXTURE)
    result = run_cold_audit(rows)
    assert result.projected_cost_baseline_usd is not None
    assert result.projected_cost_savings_usd is not None
    assert result.projected_cost_savings_usd > 0


def test_cli_json_output(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--log", str(JSONL_FIXTURE), "--json"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["simulated_hits"] == EXPECTED_HITS
    assert payload["disclaimer"] == DISCLAIMER
    assert "token_cost_estimate" in payload


def test_cli_markdown_output(tmp_path: Path):
    out_path = tmp_path / "report.md"
    with pytest.raises(SystemExit) as exc:
        main(["--log", str(JSONL_FIXTURE), "--markdown", "--output", str(out_path)])
    assert exc.value.code == 0
    text = out_path.read_text(encoding="utf-8")
    assert DISCLAIMER in text
    assert "Portfolio" in text


def test_cli_ledger_pilot_report(tmp_path: Path):
    db = tmp_path / "ledger.db"
    sink = SqliteLedgerSink(db)
    ledger = RouteLedger(
        tenant_id="acme-pilot",
        graph_id="support-agent",
        steps=[
            LedgerStep(node="cache_gate", duration_ms=18, cache_hit=True, cache_score=0.97),
            LedgerStep(node="cache_gate", duration_ms=210, cache_hit=False, cache_score=0.41),
            LedgerStep(node="intake", duration_ms=1800),
            LedgerStep(node="writer", duration_ms=900),
        ],
    )
    sink.write(ledger)

    out_path = tmp_path / "ledger.txt"
    with pytest.raises(SystemExit) as exc:
        main(["--ledger", ledger.run_id, "--ledger-db", str(db), "--output", str(out_path)])
    assert exc.value.code == 0
    text = out_path.read_text(encoding="utf-8")
    assert LEDGER_DISCLAIMER in text
    assert "50.0%" in text  # 1 hit / 2 gate evals
    assert "tokens_in/tokens_out" in text
    assert "not available" in text.lower()


def test_cli_list_ledger_runs(tmp_path: Path, capsys):
    db = tmp_path / "ledger.db"
    sink = SqliteLedgerSink(db)
    ledger = RouteLedger(
        tenant_id="acme",
        graph_id="agent",
        steps=[LedgerStep(node="cache_gate", cache_hit=True, cache_score=0.9, duration_ms=10)],
    )
    sink.write(ledger)
    with pytest.raises(SystemExit) as exc:
        main(["--list-runs", "--ledger-db", str(db), "--json"])
    assert exc.value.code == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["runs"]) == 1
    assert payload["runs"][0]["run_id"] == ledger.run_id


def test_analyze_ledger_run_gate_detection():
    ledger = RouteLedger(
        tenant_id="t",
        graph_id="g",
        steps=[
            LedgerStep(node="cache_gate", cache_hit=True, cache_score=0.95, duration_ms=12),
            LedgerStep(node="cache_gate", cache_hit=False, cache_score=0.2, duration_ms=200),
        ],
    )
    audit = analyze_ledger_run(ledger)
    assert audit.measured_cache_hit_rate == 0.5
    text = format_ledger_console_report(audit)
    assert "50.0%" in text


def test_cli_rejects_mixed_cold_and_ledger(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--log", str(JSONL_FIXTURE), "--ledger", "run-123"])
    assert exc.value.code == 2
    assert "not both" in capsys.readouterr().err.lower()


def test_audit_to_dict_without_tokens(tmp_path: Path):
    p = tmp_path / "minimal.jsonl"
    p.write_text(
        '{"text": "What is the Acme Corp return policy for online orders?"}\n'
        '{"text": "Tell me the Acme Corp return policy for online orders."}\n',
        encoding="utf-8",
    )
    rows = load_log(p)
    result = run_cold_audit(rows)
    data = audit_to_dict(result)
    assert "token_cost_estimate" not in data
