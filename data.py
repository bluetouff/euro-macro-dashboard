"""
data.py — Récupération des données + moteur de scoring du Euro Macro Risk Dashboard.

Sources (toutes publiques, sans clé) :
  - ECB Data Portal via le package `ecbdata`
  - API REST Eurostat (dissemination, format JSON-stat 2.0)

Moteur de scoring (identique à la version US) :
  - baseline pré-Covid (2015-2019)
  - z-score sur fenêtre glissante 5 ans (orienté par `direction`)
  - drift (écart vs baseline) + momentum (variations 3M / 1A)
  - pondération hiérarchique heuristique (corrélation historique aux récessions CEPR à +6 mois)
  - score global 0-100 + reconstruction historique
"""

import numpy as np
import pandas as pd
import requests
from datetime import datetime

from catalog import (
    SERIES_CATALOG, PRE_COVID_START, PRE_COVID_END,
    ZSCORE_WINDOW_YEARS, ZSCORE_WARNING, ZSCORE_DANGER,
    EURO_RECESSION_PERIODS, REGIME_CHANGE_SERIES, NO_MOMENTUM_SERIES,
    FRESHNESS_DAYS,
)

EUROSTAT_BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
EUROSTAT_SDMX = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/"
START = "2008-01-01"     # historique chargé (couvre GFC -> aujourd'hui)


def _fetch_eurostat_sdmx(dataset, key, start=START):
    """
    Récupère UNE série Eurostat via l'endpoint SDMX 2.1 + clé complète.
    Robuste pour les gros datasets (une_rt_m...) : la clé identifie une seule série,
    donc pas d'explosion dimensionnelle, pas de 413, pas de réponse vide.
    Essaie plusieurs variantes de format CSV (l'endpoint sert vnd.sdmx.data+csv ;
    un Accept restrictif déclenche un 406, on laisse donc `format=` piloter).
    Ex. dataset='une_rt_m', key='M.SA.TOTAL.PC_ACT.T.EA21'.
    """
    from io import StringIO
    last_err = None
    for fmt in ("SDMX-CSV", "csvdata", "CSV"):
        try:
            url = (f"{EUROSTAT_SDMX}{dataset}/{key}"
                   f"?format={fmt}&startPeriod={start[:7]}")
            r = requests.get(url, timeout=45, headers={"Accept": "*/*"})
            r.raise_for_status()
            df = pd.read_csv(StringIO(r.text))
            tcol = "TIME_PERIOD" if "TIME_PERIOD" in df.columns else None
            vcol = ("OBS_VALUE" if "OBS_VALUE" in df.columns
                    else "values" if "values" in df.columns else None)
            if tcol and vcol:
                s = pd.Series(
                    pd.to_numeric(df[vcol], errors="coerce").values,
                    index=pd.to_datetime(
                        _normalize_periods(df[tcol].astype(str)), errors="coerce"),
                )
                s = s[~s.index.isna()].dropna().sort_index()
                if len(s):
                    return s
        except Exception as e:  # noqa: BLE001 — on essaie le format suivant
            last_err = e
            continue
    if last_err:
        raise last_err
    return None


# ============================================================
# RÉCUPÉRATION BAS NIVEAU
# ============================================================

ECB_BASE = "https://data-api.ecb.europa.eu/service/data/"


def _fetch_ecb(key, start=START):
    """
    Récupère une série ECB Data Portal via l'API CSV (aucune dépendance externe).
    La clé 'FLOW.dim1.dim2...' est scindée en flowRef + clé de série.
    """
    from io import StringIO
    flow, skey = key.split(".", 1)
    url = (f"{ECB_BASE}{flow}/{skey}"
           f"?format=csvdata&startPeriod={start[:7]}")
    r = requests.get(url, timeout=30, headers={"Accept": "text/csv"})
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text))
    if df is None or len(df) == 0:
        return None
    tcol = "TIME_PERIOD" if "TIME_PERIOD" in df.columns else df.columns[-2]
    vcol = "OBS_VALUE"  if "OBS_VALUE"  in df.columns else df.columns[-1]
    s = pd.Series(
        pd.to_numeric(df[vcol], errors="coerce").values,
        index=pd.to_datetime(_normalize_periods(df[tcol].astype(str)), errors="coerce"),
    )
    s = s[~s.index.isna()].dropna().sort_index()
    return s if len(s) else None


def _parse_jsonstat(payload, select=None):
    """
    Parse un JSON-stat 2.0 Eurostat -> pd.Series indexée par date.

    `select` = dict {dimension: code} de la cellule voulue. Le parseur sélectionne
    la bonne combinaison à partir de la STRUCTURE réelle de la réponse (et non en
    supposant l'index 0), ce qui le rend robuste que l'API ait honoré ou non chaque
    filtre de la requête.
    """
    if "value" not in payload or "dimension" not in payload:
        return None
    dims = payload.get("id") or list(payload["dimension"].keys())
    if "time" not in dims:
        return None
    sizes = payload.get("size") or [
        len(payload["dimension"][d]["category"]["index"]) for d in dims
    ]

    # strides du cube (row-major)
    strides = [1] * len(sizes)
    for i in range(len(sizes) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]
    t_idx = dims.index("time")
    t_stride, t_size = strides[t_idx], sizes[t_idx]
    pos2time = {pos: lab for lab, pos
                in payload["dimension"]["time"]["category"]["index"].items()}

    # position fixée pour chaque dimension hors-temps
    select = {k.lower(): v for k, v in (select or {}).items()}
    base = 0
    for i, d in enumerate(dims):
        if d == "time":
            continue
        cat = payload["dimension"][d]["category"]["index"]  # {code: position}
        if d.lower() in select and select[d.lower()] in cat:
            base += cat[select[d.lower()]] * strides[i]
        elif sizes[i] == 1:
            base += next(iter(cat.values())) * strides[i]
        # sinon : dimension multi-positions non sélectionnée -> position 0 (agrégat usuel)

    values = payload["value"]
    if isinstance(values, dict):
        get = lambda k: values.get(str(k))          # noqa: E731
    else:
        get = lambda k: values[k] if 0 <= k < len(values) else None  # noqa: E731

    out = {}
    for pos, lab in pos2time.items():
        v = get(base + pos * t_stride)
        if v is not None:
            out[lab] = v
    if not out:
        return None

    s = pd.Series(out)
    s.index = pd.to_datetime(_normalize_periods(s.index), errors="coerce")
    s = pd.to_numeric(s, errors="coerce")
    s = s[~s.index.isna()].dropna().sort_index()
    return s if len(s) else None


def _normalize_periods(idx):
    """
    Convertit les codes de période Eurostat en dates parsables.
    Gère : 2024-M03 (mensuel), 2024-Q1 (trimestriel), 2024-03, 2024 (annuel).
    """
    out = []
    for x in idx:
        x = str(x)
        if "Q" in x:                                  # 2024-Q1 / 2024Q1
            y, q = x.replace("-", "").split("Q")
            out.append(f"{y}-{(int(q) - 1) * 3 + 1:02d}-01")
        elif "-M" in x:                               # 2024-M03  (mensuel Eurostat)
            y, m = x.split("-M")
            out.append(f"{y}-{int(m):02d}-01")
        elif "W" in x and "-" in x:                   # 2024-W05  (hebdo, rare)
            y, w = x.split("-W")
            out.append(f"{y}-{int(w):02d}-1-1" if False else f"{y}-01-01")
        elif len(x) == 7 and "-" in x:                # 2024-03
            out.append(f"{x}-01")
        elif len(x) == 4 and x.isdigit():             # 2024 (annuel)
            out.append(f"{x}-12-31")
        else:
            out.append(x)
    return out


def _fetch_eurostat(dataset, filters, start=START):
    """
    Récupère une série Eurostat -> pd.Series indexée par date.

    Stratégie : on envoie TOUS les filtres dans l'URL pour obtenir une réponse
    compacte (les gros datasets comme une_rt_m renvoient sinon un 413 ou un JSON
    d'erreur sans champ `value`). Repli geo-seul + sélection de cellule si jamais
    l'API n'honore pas un filtre. Le parseur sélectionne de toute façon la bonne
    cellule à partir de la structure réelle de la réponse.
    """
    def _request(params):
        url = (f"{EUROSTAT_BASE}{dataset}?format=JSON&lang=EN"
               f"&sinceTimePeriod={start[:4]}{params}")
        r = requests.get(url, timeout=45, headers={"Accept": "application/json"})
        r.raise_for_status()
        return r.json()

    # 1) tous les filtres -> réponse compacte
    all_params = "".join(f"&{k}={v}" for k, v in filters.items())
    s = None
    try:
        s = _parse_jsonstat(_request(all_params), select=filters)
        if s is not None and len(s) >= 10:
            return s
    except Exception:  # noqa: BLE001 — on tentera le repli
        s = None

    # 2) repli : geo seul, borné dans le temps (lastTimePeriod) pour garantir une
    #    réponse exploitable même sur un gros dataset -> sélection de cellule.
    geo = filters.get("geo")
    for params in (f"&geo={geo}&lastTimePeriod=480" if geo else "&lastTimePeriod=480",
                   f"&geo={geo}" if geo else ""):
        try:
            s2 = _parse_jsonstat(_request(params), select=filters)
            if s2 is not None and len(s2) >= 10:
                return s2
        except Exception:  # noqa: BLE001
            continue
    return s


def _normalized_day(value=None):
    """Retourne un Timestamp UTC sans timezone, normalisé au jour."""
    ts = pd.Timestamp.now(tz="UTC") if value is None else pd.Timestamp(value)
    if ts.tzinfo is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    return ts.normalize()


def _freshness_error(series, meta, as_of=None):
    """Décrit une série périmée, ou renvoie None si elle est assez récente."""
    if series is None or len(series) == 0:
        return "réponse vide"
    last = _normalized_day(series.index[-1])
    today = _normalized_day(as_of)
    age = max(0, (today - last).days)
    limit = int(meta.get("max_age_days", FRESHNESS_DAYS.get(meta.get("freq", "M"), 105)))
    if age > limit:
        return (f"périmée : dernière observation {last.date().isoformat()} "
                f"({age} jours, limite {limit})")
    return None


def fetch_all_series(progress=None, as_of=None):
    """
    Récupère toutes les séries du catalogue.
    Retourne dict {code: pd.Series}. Les séries en erreur sont ignorées
    (et listées dans le dict `errors`).
    """
    raw, errors = {}, {}
    items = [(f, c, m) for f, fam in SERIES_CATALOG.items()
             for c, m in fam.items()]
    n = len(items)

    for i, (family, code, meta) in enumerate(items):
        if progress:
            progress(i / n, f"{code} — {meta['name']}")
        if meta.get("source") == "computed":
            continue  # calculées après coup
        try:
            if meta["source"] == "ecb":
                s = _fetch_ecb(meta["key"])
            elif meta["source"] == "eurostat_sdmx":
                s = _fetch_eurostat_sdmx(meta["dataset"], meta["key"])
            else:
                s = _fetch_eurostat(meta["dataset"], meta["filters"])
            if s is not None and len(s) >= 10:
                if meta.get("yoy"):
                    s = _to_yoy(s, meta.get("freq", "M"))
                if s is not None and len(s) >= 10:
                    stale = _freshness_error(s, meta, as_of=as_of)
                    if stale:
                        errors[code] = stale
                    else:
                        raw[code] = s
                else:
                    errors[code] = "trop court après calcul YoY"
            elif s is not None:
                errors[code] = f"seulement {len(s)} obs (filtres/clé à vérifier)"
            else:
                errors[code] = meta.get(
                    "empty_message", "réponse vide — vérifier dimensions (geo/unit/s_adj)"
                )
        except Exception as e:  # noqa: BLE001 — robustesse: on saute la série
            errors[code] = str(e)[:140]

    # Séries calculées (spreads, pente, M1 réel...) avec échelle paramétrable
    for family, fam in SERIES_CATALOG.items():
        for code, meta in fam.items():
            if meta.get("source") == "computed":
                a, b = meta["compute"]
                scale = meta.get("scale", 1.0)
                if a in raw and b in raw:
                    aligned = ((raw[a] - raw[b]) * scale).dropna()
                    if len(aligned) >= 10:
                        stale = _freshness_error(aligned, meta, as_of=as_of)
                        if stale:
                            errors[code] = stale
                        else:
                            raw[code] = aligned
                    else:
                        errors[code] = "trop court après calcul des composantes"
                else:
                    missing = ", ".join(c for c in (a, b) if c not in raw)
                    errors[code] = f"composante indisponible : {missing}"

    if progress:
        progress(1.0, "terminé")
    return raw, errors


def _to_yoy(s, freq="M"):
    """Variation YoY d'une série de niveaux selon la fréquence (M->12, Q->4, A->1)."""
    periods = {"M": 12, "Q": 4, "A": 1, "W": 52, "D": 252, "B": 252}.get(freq, 12)
    return (s.pct_change(periods) * 100).dropna()


# ============================================================
# MÉTRIQUES PAR SÉRIE
# ============================================================

def _calendar_change(data, target_date, mode="delta"):
    """Variation vers la dernière observation connue à la date cible ou avant."""
    past = data.loc[:target_date]
    if len(past) == 0:
        return np.nan
    current = float(data.iloc[-1])
    previous = float(past.iloc[-1])
    if mode == "relative":
        return ((current - previous) / abs(previous) * 100) if previous else np.nan
    return current - previous


def _momentum_unit(unit, mode):
    if mode == "relative":
        return "%"
    return {"%": "pp", "idx": "pt", "pts": "pt", "bal": "pt"}.get(unit, unit or "pt")


def compute_metrics(data, direction="up", with_momentum=True,
                    momentum_mode="delta", unit=""):
    """Calcule current / baseline / z-score / drift / momentum / statut."""
    if data is None or len(data) < 10:
        return None

    current = float(data.iloc[-1])
    current_date = data.index[-1]

    precovid = data.loc[PRE_COVID_START:PRE_COVID_END]
    baseline = float(precovid.mean()) if len(precovid) else np.nan

    cutoff = current_date - pd.DateOffset(years=ZSCORE_WINDOW_YEARS)
    window = data.loc[cutoff:]
    if len(window) > 5 and window.std() > 0:
        zscore = (current - window.mean()) / window.std()
    else:
        zscore = np.nan

    signed_z = zscore if direction == "up" else -zscore

    if np.isnan(signed_z):
        status = "unknown"
    elif signed_z >= ZSCORE_DANGER:
        status = "danger"
    elif signed_z >= ZSCORE_WARNING:
        status = "warning"
    else:
        status = "ok"

    mom_3m = (_calendar_change(data, current_date - pd.DateOffset(months=3), momentum_mode)
              if with_momentum else np.nan)
    mom_1y = (_calendar_change(data, current_date - pd.DateOffset(years=1), momentum_mode)
              if with_momentum else np.nan)

    return {
        "current": current,
        "date": current_date,
        "baseline": baseline,
        "zscore": float(zscore) if not np.isnan(zscore) else np.nan,
        "signed_z": float(signed_z) if not np.isnan(signed_z) else np.nan,
        "drift": (current - baseline) if not np.isnan(baseline) else np.nan,
        "mom_3m": mom_3m,
        "mom_1y": mom_1y,
        "mom_unit": _momentum_unit(unit, momentum_mode),
        "status": status,
        "history": data,
    }


def compute_dashboard(raw):
    """Calcule les métriques pour toutes les séries récupérées."""
    out = {}
    for family, fam in SERIES_CATALOG.items():
        for code, meta in fam.items():
            if code not in raw or meta.get("hidden"):
                continue
            out[code] = compute_metrics(
                raw[code],
                direction=meta.get("direction", "up"),
                with_momentum=code not in NO_MOMENTUM_SERIES
                and code not in REGIME_CHANGE_SERIES,
                momentum_mode=meta.get("momentum", "delta"),
                unit=meta.get("unit", ""),
            )
            out[code]["family"] = family
            out[code]["meta"] = meta
    return out


# ============================================================
# POUVOIR PRÉDICTIF & PONDÉRATION (backtest CEPR)
# ============================================================

def _recession_dummy(index):
    """Série 0/1 alignée sur `index` : 1 pendant les récessions CEPR."""
    d = pd.Series(0, index=index, dtype=float)
    for start, end in EURO_RECESSION_PERIODS:
        d.loc[start:end] = 1.0
    return d


def compute_predictive_power(raw):
    """
    Pour chaque série, |corrélation| entre son z-score glissant mensuel (orienté
    risque) et l'état de récession CEPR six mois plus tard. Il s'agit d'une
    heuristique descriptive sur échantillon complet, pas d'une validation prospective.
    Renvoie dict {code: power in [0,1]}.
    """
    power = {}
    for family, fam in SERIES_CATALOG.items():
        for code, meta in fam.items():
            if code not in raw:
                continue
            # Toutes les séries passent sur une grille mensuelle avant le
            # backtest : 60 observations = 5 ans et le lead = 6 mois, quelle
            # que soit leur fréquence native.
            s = raw[code].resample("MS").last().dropna()
            # z-score glissant 5 ans
            roll = s.rolling(60, min_periods=12)
            z = (s - roll.mean()) / roll.std()
            if meta.get("direction", "up") == "down":
                z = -z
            z = z.dropna()
            if len(z) < 24:
                power[code] = 0.3
                continue
            rec = _recession_dummy(z.index).shift(-6).fillna(0)  # récession dans 6 mois
            try:
                with np.errstate(invalid="ignore", divide="ignore"):
                    c = np.corrcoef(z.values, rec.loc[z.index].values)[0, 1]
                power[code] = float(abs(c)) if not np.isnan(c) else 0.3
            except Exception:
                power[code] = 0.3
    return power


def power_to_weight(power):
    """Mappe la corrélation historique vers un poids heuristique à 3 paliers."""
    if power >= 0.5:
        return 3.0   # signal fort -> tier 1
    if power >= 0.3:
        return 2.0   # signal moyen -> tier 2
    return 1.0       # signal faible -> tier 3


def apply_weights(dashboard, power):
    """Attribue à chaque série un poids basé sur la corrélation historique."""
    for code, d in dashboard.items():
        d["power"] = power.get(code, 0.3)
        d["weight"] = power_to_weight(d["power"])
    return dashboard


# ============================================================
# SCORES (famille + global)
# ============================================================

def _status_score(d):
    """Convertit le z-score signé en contribution 0-100."""
    z = d.get("signed_z", np.nan)
    if np.isnan(z):
        return None
    # -2 -> 0, 0 -> 33, +2 -> 100 (clamp)
    return float(np.clip((z + 2) / 4 * 100, 0, 100))


def family_scores(dashboard):
    """Score 0-100 par famille (moyenne pondérée des contributions)."""
    fam = {}
    for code, d in dashboard.items():
        sc = _status_score(d)
        if sc is None:
            continue
        f = d["family"]
        fam.setdefault(f, {"num": 0.0, "den": 0.0, "n": 0})
        w = d.get("weight", 1.0)
        fam[f]["num"] += sc * w
        fam[f]["den"] += w
        fam[f]["n"] += 1
    return {f: (v["num"] / v["den"] if v["den"] else np.nan, v["n"])
            for f, v in fam.items()}


def global_score(dashboard):
    """Score de risque global 0-100 (pondération heuristique documentée)."""
    num = den = 0.0
    for code, d in dashboard.items():
        sc = _status_score(d)
        if sc is None:
            continue
        w = d.get("weight", 1.0)
        num += sc * w
        den += w
    return round(num / den, 1) if den else np.nan


def reconstruct_historical_score(raw, power):
    """
    Reconstruit le score de risque composite mois par mois (1990->today si dispo).
    Permet de superposer le score aux récessions CEPR pour validation visuelle.
    """
    # grille mensuelle commune
    if not raw:
        return pd.Series(dtype=float)
    starts = min(s.index.min() for s in raw.values())
    idx = pd.date_range(starts, datetime.today(), freq="MS")

    contrib = pd.DataFrame(index=idx)
    weights = {}
    for family, fam in SERIES_CATALOG.items():
        for code, meta in fam.items():
            if code not in raw or meta.get("hidden"):
                continue
            s = raw[code].reindex(idx, method="ffill")
            roll = s.rolling(60, min_periods=12)
            z = (s - roll.mean()) / roll.std()
            if meta.get("direction", "up") == "down":
                z = -z
            contrib[code] = np.clip((z + 2) / 4 * 100, 0, 100)
            weights[code] = power_to_weight(power.get(code, 0.3))

    if contrib.empty:
        return pd.Series(dtype=float)
    w = pd.Series(weights)
    num = (contrib * w).sum(axis=1, skipna=True)
    den = contrib.notna().mul(w, axis=1).sum(axis=1)
    score = (num / den).replace([np.inf, -np.inf], np.nan)
    return score.dropna()


# ============================================================
# HELPERS UI
# ============================================================

STATUS_EMOJI = {"ok": "🟢", "warning": "🟡", "danger": "🔴", "unknown": "⚪"}
STATUS_COLOR = {"ok": "#26a269", "warning": "#ffaa00", "danger": "#e01b24", "unknown": "#666"}


def status_emoji(status):
    return STATUS_EMOJI.get(status, "⚪")


def status_color(status):
    return STATUS_COLOR.get(status, "#666")


def regime_from_score(score):
    """Libellé de régime macro à partir du score global."""
    if np.isnan(score):
        return "Indéterminé", "#666"
    if score >= 70:
        return "Risk-Off / Stress élevé", "#e01b24"
    if score >= 55:
        return "Prudence / Récession Watch", "#ffaa00"
    if score >= 45:
        return "Neutre", "#c0c000"
    return "Risk-On / Expansion", "#26a269"
