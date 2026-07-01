"""Tests for Section schema."""

from chorusgraph.sections.models import CachePolicy, Section


def test_section_defaults():
    s = Section(section_id="route", category_slug="greeting", content={"route": "hi"})
    assert s.cache_policy == CachePolicy.NO_CACHE
    assert s.vector is None


def test_cache_policy_values():
    assert CachePolicy.SEMANTIC.value == "semantic"
    assert CachePolicy.REPLAY_SAFE.value == "replay_safe"
