"""
catalog.py — Catalogue de séries et règles de scoring du Euro Macro Risk Dashboard.

Pendant européen de la version US (FRED). Ici deux sources publiques et SANS CLÉ :
  - ECB Data Portal (ex-SDW) via le package `ecbdata`  -> monétaire / financier / souverain
  - API REST Eurostat (JSON-stat)                       -> économie réelle / emploi / immobilier

Chaque série porte :
  - name      : libellé affiché
  - source    : 'ecb' ou 'eurostat'
  - key       : clé de série ECB  (si source == 'ecb')
  - dataset   : code dataset Eurostat (si source == 'eurostat')
  - filters   : dict de dimensions Eurostat (geo, unit, ...)
  - freq      : 'D' | 'B' | 'W' | 'M' | 'Q' (fréquence native, indicatif)
  - direction : 'up'   -> une valeur HAUTE = plus de risque
                'down' -> une valeur BASSE = plus de risque
  - unit      : libellé d'unité court
  - yoy       : True -> on calcule la variation YoY au lieu d'utiliser le niveau brut

NOTE DE FIABILITÉ : les clés ECB sont vérifiées sur data.ecb.europa.eu. Les codes
Eurostat suivent la nomenclature standard mais leurs dimensions bougent parfois
(EA20 -> EA21, libellés s_adj...). Le `catalog.py` est le SEUL endroit à ajuster :
toute série qui renvoie une erreur est ignorée proprement et signalée dans l'UI.
"""

# ============================================================
# FENÊTRES & SEUILS (identiques à la version US)
# ============================================================

PRE_COVID_START = "2015-01-01"
PRE_COVID_END   = "2019-12-31"

ZSCORE_WINDOW_YEARS = 5          # fenêtre glissante pour le z-score
ZSCORE_WARNING      = 1.0        # |z| signé >= 1.0  -> 🟡
ZSCORE_DANGER       = 2.0        # |z| signé >= 2.0  -> 🔴

# Périmètre public du dashboard. L'agrégat Eurostat `EA` est utilisé uniquement
# lorsque le jeu de données représente explicitement la composition évolutive.
EURO_AREA_SCOPE = "Zone euro · composition courante (EA21 depuis 2026)"
EURO_AREA_CODE = "EA21"

# Une série hors de ces délais est exclue du score au lieu d'être affichée comme
# courante. Les dates mensuelles/trimestrielles sont les débuts de période.
FRESHNESS_DAYS = {"D": 14, "B": 14, "W": 28, "M": 105, "Q": 320, "A": 550}

# Récessions zone euro (datation CEPR / Euro Area Business Cycle Dating Committee)
# Utilisées pour valider/pondérer le score composite par backtest.
EURO_RECESSION_PERIODS = [
    ("1992-02-01", "1993-09-30"),   # crise du SME
    ("2008-02-01", "2009-06-30"),   # crise financière mondiale
    ("2011-08-01", "2013-03-31"),   # crise de la dette souveraine (double dip)
    ("2019-11-01", "2020-06-30"),   # choc Covid
]

# Séries de "régime" : pas de momentum, on regarde le niveau/changement de régime
# (taux directeurs, taux courts -> piloter par changement, pas par momentum).
REGIME_CHANGE_SERIES = {"DFR", "MRO", "ESTR", "EURIBOR3M"}

# Séries pour lesquelles le momentum n'a pas de sens (indices de stress déjà normalisés).
NO_MOMENTUM_SERIES = {"CISS", "CISS_SOV", "CISS_BM", "CONS_CONF"}

# ============================================================
# LIBELLÉS & ICÔNES DES FAMILLES
# ============================================================

FAMILY_LABELS = {
    "taux_monetaire":    "Taux & Politique BCE",
    "avances":           "Signaux avancés (alerte précoce)",
    "stress_systemique": "Stress systémique & liquidité",
    "souverain":         "Souverain & spreads",
    "inflation":         "Inflation",
    "emploi":            "Marché du travail",
    "credit_banques":    "Crédit & banques",
    "activite_reelle":   "Activité réelle & conso",
    "corporate_marches": "Corporate & marchés",
    "immobilier":        "Immobilier",
}

FAMILY_ICONS = {
    "taux_monetaire":    "🏛️",
    "avances":           "⏰",
    "stress_systemique": "🌡️",
    "souverain":         "🪙",
    "inflation":         "🔥",
    "emploi":            "👷",
    "credit_banques":    "🏦",
    "activite_reelle":   "🛒",
    "corporate_marches": "📉",
    "immobilier":        "🏠",
}

# ============================================================
# CATALOGUE DES SÉRIES
# ============================================================

SERIES_CATALOG = {

    # ---- 1. Taux & politique monétaire BCE -------------------------------
    "taux_monetaire": {
        "DFR":       {"name": "Taux dépôt BCE (DFR)", "source": "ecb",
                      "key": "FM.B.U2.EUR.4F.KR.DFR.LEV",            "freq": "B", "direction": "up",   "unit": "%",
                      "max_age_days": 550},  # série événementielle : nouvelle obs seulement si changement
        "MRO":       {"name": "Taux refi principal (MRO)", "source": "ecb",
                      "key": "FM.B.U2.EUR.4F.KR.MRR_FR.LEV",         "freq": "B", "direction": "up",   "unit": "%",
                      "max_age_days": 550},  # série événementielle : nouvelle obs seulement si changement
        "ESTR":      {"name": "€STR (taux court)", "source": "ecb",
                      "key": "EST.B.EU000A2X2A25.WT",                "freq": "B", "direction": "up",   "unit": "%"},
        "EURIBOR3M": {"name": "Euribor 3M", "source": "ecb",
                      "key": "FM.M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA",   "freq": "M", "direction": "up",   "unit": "%"},
        "EURUSD":    {"name": "EUR/USD", "source": "ecb",
                      "key": "EXR.D.USD.EUR.SP00.A",                 "freq": "D", "direction": "down", "unit": "",
                      "momentum": "relative"},
    },

    # ---- 2. Signaux avancés (alerte précoce) ----------------------------
    "avances": {
        # M1 nominal (caché) — sert au calcul du M1 réel
        "M1G":       {"name": "Croissance M1 (nominal)", "source": "ecb",
                      "key": "BSI.M.U2.Y.V.M10.X.I.U2.2300.Z01.A", "freq": "M",
                      "direction": "down", "unit": "%", "hidden": True},
        "M1_REAL":   {"name": "M1 réel (M1 − inflation)", "source": "computed",
                      "compute": ("M1G", "HICP"), "scale": 1.0, "freq": "M",
                      "direction": "down", "unit": "pp"},
        "M3G":       {"name": "Croissance M3", "source": "ecb",
                      "key": "BSI.M.U2.Y.V.M30.X.I.U2.2300.Z01.A", "freq": "M",
                      "direction": "down", "unit": "%"},
        "SLOPE":     {"name": "Pente courbe 10Y−3M", "source": "computed",
                      "compute": ("DE10Y", "EURIBOR3M"), "scale": 100.0, "freq": "M",
                      "direction": "down", "unit": "pb"},
        "EEI":       {"name": "Anticipations d'emploi (EEI)", "source": "eurostat",
                      "dataset": "ei_bssi_m_r2",
                      "filters": {"geo": "EA21", "indic": "BS-EEI-I", "s_adj": "SA"},
                      "freq": "M", "direction": "down", "unit": "idx"},
    },

    # ---- 3. Stress systémique & liquidité --------------------------------
    "stress_systemique": {
        "CISS":      {"name": "New CISS (stress systémique)", "source": "ecb",
                      "key": "CISS.D.U2.Z0Z.4F.EC.SS_CIN.IDX",       "freq": "D", "direction": "up",   "unit": "idx"},
        "CISS_SOV":  {"name": "New SovCISS (stress souverain)", "source": "ecb",
                      "key": "CISS.D.U2.Z0Z.4F.EC.SOV_EWN.IDX",      "freq": "D", "direction": "up",   "unit": "idx"},
        "CISS_BM":   {"name": "CISS sous-indice obligataire", "source": "ecb",
                      "key": "CISS.D.U2.Z0Z.4F.EC.SS_BMN.CON",       "freq": "D", "direction": "up",   "unit": "idx"},
    },

    # ---- 3. Souverain & spreads (Maastricht 10Y) -------------------------
    # IRS = taux d'intérêt long terme à des fins de convergence (benchmark 10Y).
    "souverain": {
        "DE10Y": {"name": "Bund 10Y (DE)", "source": "ecb",
                  "key": "IRS.M.DE.L.L40.CI.0000.EUR.N.Z",           "freq": "M", "direction": "up", "unit": "%"},
        "FR10Y": {"name": "OAT 10Y (FR)", "source": "ecb",
                  "key": "IRS.M.FR.L.L40.CI.0000.EUR.N.Z",           "freq": "M", "direction": "up", "unit": "%"},
        "IT10Y": {"name": "BTP 10Y (IT)", "source": "ecb",
                  "key": "IRS.M.IT.L.L40.CI.0000.EUR.N.Z",           "freq": "M", "direction": "up", "unit": "%"},
        "ES10Y": {"name": "Bono 10Y (ES)", "source": "ecb",
                  "key": "IRS.M.ES.L.L40.CI.0000.EUR.N.Z",           "freq": "M", "direction": "up", "unit": "%"},
        # Spreads calculés dans data.py à partir des séries ci-dessus :
        "SPREAD_IT_DE": {"name": "Spread BTP-Bund", "source": "computed",
                         "compute": ("IT10Y", "DE10Y"), "scale": 100.0, "freq": "M", "direction": "up", "unit": "pb"},
        "SPREAD_FR_DE": {"name": "Spread OAT-Bund", "source": "computed",
                         "compute": ("FR10Y", "DE10Y"), "scale": 100.0, "freq": "M", "direction": "up", "unit": "pb"},
    },

    # ---- 4. Inflation ----------------------------------------------------
    "inflation": {
        "HICP":      {"name": "HICP YoY (zone euro)", "source": "eurostat",
                      "dataset": "prc_hicp_minr",
                      "filters": {"geo": "EA", "coicop18": "TOTAL", "unit": "RCH_A"},
                      "freq": "M", "direction": "up", "unit": "%"},
        "HICP_CORE": {"name": "HICP core YoY", "source": "eurostat",
                      "dataset": "prc_hicp_minr",
                      "filters": {"geo": "EA", "coicop18": "TOT_X_NRG_FOOD", "unit": "RCH_A"},
                      "freq": "M", "direction": "up", "unit": "%"},
        "PPI":       {"name": "Prix production industrielle YoY", "source": "eurostat",
                      "dataset": "sts_inppd_m",
                      "filters": {"geo": "EA21", "nace_r2": "B-D", "s_adj": "NSA",
                                  "unit": "I21"},
                      "freq": "M", "direction": "up", "unit": "%", "yoy": True},
    },

    # ---- 5. Marché du travail -------------------------------------------
    "emploi": {
        "UNEMP":      {"name": "Chômage zone euro", "source": "ecb",
                       "key": "LFSI.M.I9.S.UNEHRT.TOTAL0.15_74.T",
                       "freq": "M", "direction": "up", "unit": "%"},
        "UNEMP_YOUTH":{"name": "Chômage des jeunes (15-24)", "source": "ecb",
                       "key": "LFSI.M.I9.S.UNEHRT.TOTAL0.15_24.T",
                       "freq": "M", "direction": "up", "unit": "%"},
    },

    # ---- 6. Crédit & banques --------------------------------------------
    # BSI = bilans des IFM. Croissance du crédit -> direction 'down' (ralentissement = risque).
    "credit_banques": {
        "LOANS_HH":  {"name": "Crédit aux ménages (taux croissance an.)", "source": "ecb",
                      "key": "BSI.M.U2.N.A.A20T.A.I.U2.2250.Z01.A",     "freq": "M", "direction": "down", "unit": "%"},
        "LOANS_NFC": {"name": "Crédit aux entreprises (taux croissance an.)", "source": "ecb",
                      "key": "BSI.M.U2.N.A.A20T.A.I.U2.2240.Z01.A",     "freq": "M", "direction": "down", "unit": "%"},
    },

    # ---- 7. Activité réelle & consommation ------------------------------
    "activite_reelle": {
        "IP":        {"name": "Production industrielle YoY", "source": "eurostat",
                      "dataset": "sts_inpr_m",
                      "filters": {"geo": "EA21", "nace_r2": "B-D", "s_adj": "SCA",
                                  "unit": "I21"},
                      "freq": "M", "direction": "down", "unit": "%", "yoy": True},
        "RETAIL":    {"name": "Ventes de détail YoY", "source": "eurostat",
                      "dataset": "sts_trtu_m",
                      "filters": {"geo": "EA21", "nace_r2": "G47", "s_adj": "SCA",
                                  "indic_bt": "TOVV", "unit": "I21"},
                      "freq": "M", "direction": "down", "unit": "%", "yoy": True},
        "CONS_CONF": {"name": "Confiance des consommateurs", "source": "eurostat",
                      "dataset": "ei_bsco_m",
                      "filters": {"geo": "EA21", "indic": "BS-CSMCI", "s_adj": "SA",
                                  "unit": "BAL"},
                      "freq": "M", "direction": "down", "unit": "bal"},
        "ESI":       {"name": "Sentiment économique (ESI)", "source": "eurostat",
                      "dataset": "ei_bssi_m_r2",
                      "filters": {"geo": "EA21", "indic": "BS-ESI-I", "s_adj": "SA"},
                      "freq": "M", "direction": "down", "unit": "idx"},
    },

    # ---- 8. Corporate & marchés -----------------------------------------
    "corporate_marches": {
        "STOXX":     {"name": "EuroStoxx large (niveau)", "source": "ecb",
                      "key": "FM.M.U2.EUR.DS.EI.DJEURST.HSTA",       "freq": "M", "direction": "down", "unit": "idx",
                      "momentum": "relative"},
        "STOXX50":   {"name": "EURO STOXX 50 (niveau)", "source": "ecb",
                      "key": "FM.M.U2.EUR.DS.EI.DJES50I.HSTA",       "freq": "M", "direction": "down", "unit": "pts",
                      "momentum": "relative"},
    },

    # ---- 9. Immobilier ---------------------------------------------------
    "immobilier": {
        "HPI":       {"name": "Prix immobilier YoY", "source": "eurostat",
                      "dataset": "prc_hpi_q",
                      "filters": {"geo": "EA21", "purchase": "TOTAL", "unit": "I15_NSA"},
                      "freq": "Q", "direction": "down", "unit": "%", "yoy": True},
    },
}


def all_series_count():
    """Compte total d'entrées du catalogue, y compris calculées et cachées."""
    return sum(len(v) for v in SERIES_CATALOG.values())


def visible_series_count():
    """Compte les indicateurs attendus dans le dashboard public."""
    return sum(1 for _, _, meta in flat_series() if not meta.get("hidden"))


def flat_series():
    """Itère sur (famille, code, meta) pour toutes les séries du catalogue."""
    for family, series in SERIES_CATALOG.items():
        for code, meta in series.items():
            yield family, code, meta
