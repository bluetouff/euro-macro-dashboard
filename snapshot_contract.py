"""Contrat minimal d'un instantané publiable en production."""

import math
import re
from datetime import datetime


REQUIRED_INDICATORS = {"CISS", "HICP", "UNEMP", "EEI", "ESI"}
REVISION_RE = re.compile(r"^(?:[0-9a-f]{40}|worktree)$")


class SnapshotValidationError(ValueError):
    """L'instantané ne satisfait pas le contrat de publication."""


def _parse_utc(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise SnapshotValidationError("generated_at doit être un timestamp UTC en Z")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SnapshotValidationError("generated_at invalide") from exc


def validate_snapshot(snapshot):
    """Valide la structure, la couverture et la traçabilité d'un snapshot."""
    if not isinstance(snapshot, dict):
        raise SnapshotValidationError("racine JSON invalide")

    _parse_utc(snapshot.get("generated_at"))
    revision = snapshot.get("source_sha")
    if not isinstance(revision, str) or not REVISION_RE.fullmatch(revision):
        raise SnapshotValidationError("source_sha absent ou invalide")

    score = snapshot.get("global_score")
    if not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 100:
        raise SnapshotValidationError("score global absent ou hors limites")

    quality = snapshot.get("quality")
    if not isinstance(quality, dict):
        raise SnapshotValidationError("bloc quality absent")
    active = quality.get("active")
    expected = quality.get("expected")
    if not isinstance(active, int) or not isinstance(expected, int) or expected <= 0:
        raise SnapshotValidationError("couverture quality invalide")
    if active < max(20, math.ceil(expected * 0.8)):
        raise SnapshotValidationError(f"couverture insuffisante : {active}/{expected}")

    indicators = [indicator
                  for family in snapshot.get("families", [])
                  for indicator in family.get("indicators", [])]
    if len(indicators) != active or snapshot.get("counts", {}).get("total") != active:
        raise SnapshotValidationError("compteurs et indicateurs incohérents")

    codes = {indicator.get("code") for indicator in indicators}
    missing = sorted(REQUIRED_INDICATORS - codes)
    if missing:
        raise SnapshotValidationError("indicateurs critiques absents : " + ", ".join(missing))

    for indicator in indicators:
        if not isinstance(indicator.get("as_of"), str):
            raise SnapshotValidationError(f"date source absente : {indicator.get('code', '?')}")
        try:
            datetime.fromisoformat(indicator["as_of"])
        except ValueError as exc:
            raise SnapshotValidationError(
                f"date source invalide : {indicator.get('code', '?')}") from exc
        source_url = indicator.get("source_url")
        if not isinstance(source_url, str) or not source_url.startswith("https://"):
            raise SnapshotValidationError(f"source absente : {indicator.get('code', '?')}")

    errors = snapshot.get("errors", {})
    error_sources = snapshot.get("error_sources", {})
    if not isinstance(errors, dict) or not isinstance(error_sources, dict):
        raise SnapshotValidationError("diagnostic des erreurs invalide")
    for code in errors:
        source_url = error_sources.get(code)
        if not isinstance(source_url, str) or not source_url.startswith("https://"):
            raise SnapshotValidationError(f"source d'erreur absente : {code}")

    return snapshot
