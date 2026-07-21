"""
build_snapshot.py — génère un instantané statique du dashboard.

Réutilise la couche data testée (catalog.py + data.py) pour récupérer + scorer
toutes les séries, puis écrit `snapshot.js` :  window.SNAPSHOT = { ... };

La page web (index.html) lit ce fichier — aucune connexion réseau ni clé côté
navigateur. Relancer ce script (cron, GitHub Action, manuellement) rafraîchit
les données.

Usage :  python build_snapshot.py
"""

import json
import math
from datetime import datetime, timezone

import numpy as np

from catalog import (
    SERIES_CATALOG, FAMILY_LABELS, FAMILY_ICONS,
    EURO_RECESSION_PERIODS, all_series_count,
)
from data import (
    fetch_all_series, compute_dashboard, compute_predictive_power,
    apply_weights, family_scores, global_score, reconstruct_historical_score,
    status_color, regime_from_score,
)

SPARK_POINTS = 48   # points conservés pour les mini-courbes


def _generated_at():
    """Timestamp UTC explicite pour les consommateurs machine."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _num(x):
    """float JSON-safe (NaN/inf -> None)."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(x) or math.isinf(x)) else round(x, 4)


def _spark(series):
    if series is None or len(series) == 0:
        return []
    s = series.tail(SPARK_POINTS)
    return [_num(v) for v in s.values if _num(v) is not None]


def build():
    print("Récupération BCE & Eurostat…")
    raw, errors = fetch_all_series()
    dashboard = compute_dashboard(raw)
    power = compute_predictive_power(raw)
    dashboard = apply_weights(dashboard, power)
    hist = reconstruct_historical_score(raw, power)
    fam = family_scores(dashboard)
    g = global_score(dashboard)
    label, color = regime_from_score(g)

    counts = {
        "ok":   sum(1 for d in dashboard.values() if d["status"] == "ok"),
        "warn": sum(1 for d in dashboard.values() if d["status"] == "warning"),
        "dang": sum(1 for d in dashboard.values() if d["status"] == "danger"),
        "total": len(dashboard),
    }

    ciss = None
    if "CISS" in dashboard:
        c = dashboard["CISS"]
        ciss = {"value": _num(c["current"]), "status": c["status"], "z": _num(c.get("signed_z"))}

    families = []
    for fkey, series in SERIES_CATALOG.items():
        inds = []
        for code, meta in series.items():
            if code not in dashboard or meta.get("hidden"):
                continue
            d = dashboard[code]
            inds.append({
                "code": code,
                "name": meta["name"],
                "unit": meta.get("unit", ""),
                "value": _num(d["current"]),
                "status": d["status"],
                "color": status_color(d["status"]),
                "z": _num(d.get("signed_z")),
                "mom_1y": _num(d.get("mom_1y")),
                "baseline": _num(d.get("baseline")),
                "spark": _spark(d.get("history")),
            })
        if not inds:
            continue
        sc, n = fam.get(fkey, (float("nan"), 0))
        _, fcol = regime_from_score(sc)
        families.append({
            "key": fkey,
            "label": FAMILY_LABELS.get(fkey, fkey),
            "icon": FAMILY_ICONS.get(fkey, "•"),
            "score": _num(sc),
            "color": fcol,
            "indicators": inds,
        })

    alerts = sorted(
        [d for d in dashboard.values() if d["status"] in ("warning", "danger")],
        key=lambda d: d.get("signed_z", 0) or 0, reverse=True,
    )
    alerts_out = [{
        "name": d["meta"]["name"], "value": _num(d["current"]),
        "unit": d["meta"].get("unit", ""), "status": d["status"],
        "color": status_color(d["status"]), "z": _num(d.get("signed_z")),
    } for d in alerts]

    hist_out = [[ts.strftime("%Y-%m"), _num(v)]
                for ts, v in hist.items() if _num(v) is not None]

    snap = {
        "generated_at": _generated_at(),
        "global_score": _num(g),
        "regime": {"label": label, "color": color},
        "counts": counts,
        "ciss": ciss,
        "families": families,
        "alerts": alerts_out,
        "history": hist_out,
        "recessions": [list(p) for p in EURO_RECESSION_PERIODS],
        "catalog_total": all_series_count(),
        "errors": errors,
    }

    payload = json.dumps(snap, ensure_ascii=False, separators=(",", ":"))
    with open("snapshot.js", "w", encoding="utf-8") as f:
        f.write("window.SNAPSHOT = " + payload + ";\n")
    with open("snapshot.json", "w", encoding="utf-8") as f:
        f.write(payload)

    print(f"OK — {counts['total']} indicateurs · score {g} · "
          f"{len(errors)} série(s) en erreur")
    print("Écrit : snapshot.js (+ snapshot.json)")


if __name__ == "__main__":
    build()
