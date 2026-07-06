"""Verify wheel/sdist ship non-Python package data and audit CLI package."""

from __future__ import annotations

from importlib.resources import files


def test_audit_package_importable():
    from chorusgraph.audit.cli import main  # noqa: F401


def test_bundled_package_data_files_exist():
    root = files("chorusgraph")
    assert (root / "sections" / "profiles.default.json").is_file()
    assert (root / "shadow" / "dataset" / "labeled_queries.json").is_file()
    assert (root / "shadow" / "replay" / "data" / "website_chat_turns.jsonl").is_file()
