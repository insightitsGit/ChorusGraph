# Handoffback E9 — API 1.0

**Status:** Complete on branch `P1_Enterprice1`  
**Version:** 1.0.0

## Summary

Public API frozen in `chorusgraph/public.py`, documented in `docs/API_1_0.md`, stability policy in `docs/STABILITY.md`, version bumped to 1.0.0. Namespace remains `chorusgraph`.

## Namespace recommendation

Keep **`chorusgraph`** as the primary install (`pip install chorusgraph`). Prism family packages stay optional extras — defer `prismlib-plus[orchestrator]` merge to Phase 2.

## Release

Tag when ready: `git tag v1.0.0` (not pushed — awaiting Director sign-off).
