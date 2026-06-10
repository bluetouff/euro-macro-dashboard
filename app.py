"""
Euro Macro Risk Dashboard — tableau de bord style moderne/compact pour la zone euro.
Pendant européen de la version US (FRED -> ECB Data Portal + Eurostat).

Lancement :  streamlit run app.py
Aucune clé API requise (sources publiques BCE & Eurostat).
"""

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

from catalog import (
    SERIES_CATALOG, FAMILY_LABELS, FAMILY_ICONS,
    EURO_RECESSION_PERIODS, all_series_count,
)
from data import (
    fetch_all_series, compute_dashboard, compute_predictive_power,
    apply_weights, family_scores, global_score, reconstruct_historical_score,
    status_emoji, status_color, regime_from_score,
)

# ============================================================
# CONFIG + DESIGN (compact / moderne)
# ============================================================

st.set_page_config(page_title="Euro Macro Risk", page_icon="🇪🇺",
                   layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
  :root{
    --bg:#0a0a0c; --panel:#131316; --panel2:#17171b; --line:#23232a;
    --txt:#e9e9ec; --mut:#7c7c86; --accent:#f5a623; --accent2:#3da8ff;
    --ok:#2fbf71; --warn:#f5a623; --dang:#ff4d4f;
  }
  .stApp{background:var(--bg); color:var(--txt);
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,sans-serif;}
  .block-container{padding-top:2.2rem; padding-bottom:2rem; max-width:1500px;}
  #MainMenu,footer,header{visibility:hidden;}
  h1,h2,h3{font-family:inherit; letter-spacing:-.01em;}
  .stProgress > div > div{background:var(--accent);}
  hr{border-color:var(--line);}

  /* ---- hero ---- */
  .title{font-size:24px;font-weight:800;margin:0;}
  .sub{color:var(--mut);font-size:12px;margin-top:2px;}
  .hero{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px;margin:16px 0 4px;}
  .stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;}
  .stat .lab{font-size:10px;color:var(--mut);text-transform:uppercase;letter-spacing:.08em;}
  .stat .big{font-size:34px;font-weight:800;font-family:'SF Mono',ui-monospace,monospace;line-height:1.1;margin-top:2px;}
  .stat .big small{font-size:14px;color:var(--mut);font-weight:600;}
  .pill{display:inline-block;padding:4px 12px;border-radius:999px;font-size:13px;font-weight:700;margin-top:6px;}
  .dots{font-size:13px;font-family:'SF Mono',ui-monospace,monospace;margin-top:10px;color:var(--mut);}

  /* ---- section header ---- */
  .sec{display:flex;align-items:center;gap:10px;margin:20px 0 10px;}
  .sec .ic{font-size:15px;}
  .sec .nm{font-size:13px;font-weight:700;color:#cfcfd6;text-transform:uppercase;letter-spacing:.06em;}
  .sec .ln{flex:1;height:1px;background:var(--line);}
  .sec .bd{font-family:'SF Mono',ui-monospace,monospace;font-size:12px;font-weight:700;
    padding:2px 9px;border-radius:999px;}

  /* ---- tiles grid ---- */
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(168px,1fr));gap:9px;}
  .tile{background:var(--panel);border:1px solid var(--line);border-radius:11px;
    padding:11px 13px 10px;position:relative;overflow:hidden;transition:.15s;}
  .tile:hover{border-color:#34343d;background:var(--panel2);}
  .tile::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--c);}
  .tile .nm{font-size:10px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em;
    line-height:1.25;min-height:25px;display:flex;align-items:flex-start;gap:5px;}
  .tile .nm .d{width:7px;height:7px;border-radius:50%;background:var(--c);flex:none;margin-top:3px;}
  .tile .vl{font-size:21px;font-weight:700;font-family:'SF Mono',ui-monospace,monospace;
    color:#fff;line-height:1.1;margin-top:5px;}
  .tile .vl u{font-size:11px;color:var(--mut);font-weight:600;text-decoration:none;margin-left:3px;}
  .tile .mt{font-size:10px;font-family:'SF Mono',ui-monospace,monospace;color:var(--mut);margin-top:4px;}
  .tile .mt b{color:var(--c);font-weight:700;}

  /* ---- alerts strip ---- */
  .alerts{display:flex;flex-wrap:wrap;gap:7px;}
  .al{display:flex;align-items:center;gap:8px;background:var(--panel);border:1px solid var(--line);
    border-left:3px solid var(--c);border-radius:9px;padding:7px 11px;}
  .al .an{font-size:11px;color:#d7d7dc;font-weight:600;}
  .al .av{font-family:'SF Mono',ui-monospace,monospace;font-size:12px;color:var(--c);font-weight:700;}
  .muted{color:var(--mut);font-size:11px;}
</style>
""", unsafe_allow_html=True)


# ============================================================
# DONNÉES (cache 6h)
# ============================================================

@st.cache_data(ttl=6 * 3600, show_spinner=False)
def load_everything():
    raw, errors = fetch_all_series()
    dashboard = compute_dashboard(raw)
    power = compute_predictive_power(raw)
    dashboard = apply_weights(dashboard, power)
    hist = reconstruct_historical_score(raw, power)
    return raw, errors, dashboard, power, hist


def fmt(v, unit=""):
    av = abs(v)
    s = f"{v:,.0f}" if av >= 1000 else (f"{v:,.2f}" if av >= 1 else f"{v:,.3f}")
    return f"{s}<u>{unit}</u>" if unit else s


with st.spinner("Connexion BCE & Eurostat…"):
    raw, errors, dashboard, power, hist = load_everything()

g_score = global_score(dashboard)
regime_label, regime_col = regime_from_score(g_score)
fam = family_scores(dashboard)
n_ok = sum(1 for d in dashboard.values() if d["status"] == "ok")
n_warn = sum(1 for d in dashboard.values() if d["status"] == "warning")
n_dang = sum(1 for d in dashboard.values() if d["status"] == "danger")
ciss = dashboard.get("CISS")


# ============================================================
# HERO (titre + stats clés sur une bande compacte)
# ============================================================

st.markdown(
    f"<div class='title'>🇪🇺 Euro Macro Risk</div>"
    f"<div class='sub'>BCE + Eurostat · {len(dashboard)} indicateurs · "
    f"MAJ {datetime.now():%d %b %Y %H:%M} · backtest récessions CEPR</div>",
    unsafe_allow_html=True)

ciss_html = ""
if ciss:
    ciss_html = (f"<div class='big' style='color:{status_color(ciss['status'])}'>"
                 f"{ciss['current']:.3f} {status_emoji(ciss['status'])}</div>")
st.markdown(
    f"<div class='hero'>"
    f"<div class='stat'><div class='lab'>Score de risque global</div>"
    f"<div class='big' style='color:{regime_col}'>{g_score:g}<small>/100</small></div></div>"
    f"<div class='stat'><div class='lab'>Régime macro</div>"
    f"<span class='pill' style='background:{regime_col}22;color:{regime_col};"
    f"border:1px solid {regime_col}55'>{regime_label}</span></div>"
    f"<div class='stat'><div class='lab'>CISS · stress systémique BCE</div>{ciss_html}</div>"
    f"<div class='stat'><div class='lab'>État des {len(dashboard)} indicateurs</div>"
    f"<div class='dots'>🟢 {n_ok}&nbsp;&nbsp;🟡 {n_warn}&nbsp;&nbsp;🔴 {n_dang}</div></div>"
    f"</div>", unsafe_allow_html=True)

cc1, cc2 = st.columns([3, 1])
with cc2:
    details = st.toggle("Graphiques détaillés", value=False,
                        help="Affiche les cartes + courbes par indicateur (plus long à scroller).")
with cc1:
    with st.expander("ℹ️  Comment lire ce tableau de bord"):
        st.markdown("""
**Score global 0-100** — agrégation pondérée par *pouvoir prédictif* (corrélation historique
aux récessions **CEPR**). 🟩 <45 Risk-On · ⬜ 45-55 Neutre · 🟧 55-70 Prudence · 🟥 >70 Stress.

**Couleur d'un indicateur** = *z-score signé* (écart à sa moyenne 5 ans, orienté risque) :
🟢 normal · 🟡 tension (|z|≥1) · 🔴 alerte (|z|≥2). `z` = z-score · `1A` = variation sur 1 an.

**⏰ Signaux avancés** = indicateurs qui *précèdent* le cycle (pente de courbe, M1 réel, M3,
anticipations d'emploi). Le PMI étant propriétaire, on utilise l'**ESI** (Commission/Eurostat).

*Sources publiques BCE + Eurostat · CISS © BCE · récessions CEPR-EABCN.*
""")


# ============================================================
# SIGNAUX D'ALERTE (bandeau compact)
# ============================================================

alerts = sorted([(c, d) for c, d in dashboard.items()
                 if d["status"] in ("warning", "danger")],
                key=lambda kv: kv[1].get("signed_z", 0), reverse=True)

st.markdown("<div class='sec'><span class='ic'>⚠️</span>"
            "<span class='nm'>Signaux d'alerte</span><span class='ln'></span></div>",
            unsafe_allow_html=True)
if alerts:
    chips = ""
    for code, d in alerts:
        ccol = status_color(d["status"])
        z = d.get("signed_z", float("nan"))
        chips += (f"<div class='al' style='--c:{ccol}'>{status_emoji(d['status'])}"
                  f"<span class='an'>{d['meta']['name']}</span>"
                  f"<span class='av'>{d['current']:,.2f} · z{z:+.1f}</span></div>")
    st.markdown(f"<div class='alerts'>{chips}</div>", unsafe_allow_html=True)
else:
    st.markdown("<span class='muted'>✓ Aucun signal d'alerte — tous les indicateurs "
                "sont dans leur zone normale.</span>", unsafe_allow_html=True)


# ============================================================
# HISTORIQUE (compact, repliable)
# ============================================================

with st.expander("📈  Score composite historique vs récessions (CEPR)", expanded=False):
    if len(hist) > 12:
        fig = go.Figure()
        for s0, s1 in EURO_RECESSION_PERIODS:
            fig.add_vrect(x0=s0, x1=s1, fillcolor="#ff4d4f", opacity=0.15, line_width=0)
        fig.add_trace(go.Scatter(x=hist.index, y=hist.values, mode="lines",
                                 line=dict(color="#f5a623", width=2)))
        fig.add_hline(y=55, line=dict(color="#666", width=1, dash="dot"))
        fig.update_layout(height=240, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font=dict(color="#9a9aa2", family="SF Mono"),
                          margin=dict(l=8, r=8, t=8, b=8),
                          xaxis=dict(gridcolor="#1c1c22"),
                          yaxis=dict(gridcolor="#1c1c22", range=[0, 100]))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("<span class='muted'>Zones rouges = récessions CEPR. Un score >55 "
                    "avant/pendant ces zones valide le pouvoir d'alerte du composite.</span>",
                    unsafe_allow_html=True)
    else:
        st.info("Historique insuffisant pour reconstruire le score.")


# ============================================================
# MUR D'INDICATEURS — grille dense (vue par défaut)
# ============================================================

def sparkline(series, color):
    s = series.tail(60)
    fig = go.Figure(go.Scatter(y=s.values, mode="lines",
                               line=dict(color=color, width=1.6)))
    fig.update_layout(height=44, margin=dict(l=0, r=0, t=0, b=0),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


if not details:
    # ---- vue compacte : tout en tuiles, une seule passe HTML ----
    html = ""
    for family, series in SERIES_CATALOG.items():
        active = [(c, m) for c, m in series.items()
                  if c in dashboard and not m.get("hidden")]
        if not active:
            continue
        sc, n = fam.get(family, (np.nan, 0))
        _, bcol = regime_from_score(sc)
        html += (f"<div class='sec'><span class='ic'>{FAMILY_ICONS.get(family,'•')}</span>"
                 f"<span class='nm'>{FAMILY_LABELS.get(family,family)}</span>"
                 f"<span class='ln'></span>"
                 f"<span class='bd' style='background:{bcol}22;color:{bcol}'>{sc:.0f}</span></div>")
        tiles = ""
        for code, meta in active:
            d = dashboard[code]
            ccol = status_color(d["status"])
            unit = meta.get("unit", "")
            z = d.get("signed_z", np.nan)
            m1 = d.get("mom_1y", np.nan)
            mt = f"<b>z {z:+.2f}</b>" if not np.isnan(z) else ""
            if not np.isnan(m1):
                mt += f" · 1A {m1:+.0f}%"
            tiles += (f"<div class='tile' style='--c:{ccol}'>"
                      f"<div class='nm'><span class='d'></span>{meta['name']}</div>"
                      f"<div class='vl'>{fmt(d['current'], unit)}</div>"
                      f"<div class='mt'>{mt}</div></div>")
        html += f"<div class='grid'>{tiles}</div>"
    st.markdown(html, unsafe_allow_html=True)

else:
    # ---- vue détaillée : cartes + sparklines ----
    for family, series in SERIES_CATALOG.items():
        active = [(c, m) for c, m in series.items()
                  if c in dashboard and not m.get("hidden")]
        if not active:
            continue
        sc, n = fam.get(family, (np.nan, 0))
        st.markdown(f"<div class='sec'><span class='ic'>{FAMILY_ICONS.get(family,'•')}</span>"
                    f"<span class='nm'>{FAMILY_LABELS.get(family,family)} · {sc:.0f}/100</span>"
                    f"<span class='ln'></span></div>", unsafe_allow_html=True)
        cols = st.columns(min(4, len(active)))
        for i, (code, meta) in enumerate(active):
            d = dashboard[code]
            ccol = status_color(d["status"])
            with cols[i % len(cols)]:
                unit = meta.get("unit", "")
                sub = []
                if not np.isnan(d.get("signed_z", np.nan)):
                    sub.append(f"z {d['signed_z']:+.2f}")
                if not np.isnan(d.get("mom_1y", np.nan)):
                    sub.append(f"1A {d['mom_1y']:+.1f}%")
                st.markdown(
                    f"<div class='tile' style='--c:{ccol};margin-bottom:4px'>"
                    f"<div class='nm'><span class='d'></span>{meta['name']}</div>"
                    f"<div class='vl'>{fmt(d['current'], unit)}</div>"
                    f"<div class='mt'>{' · '.join(sub)}</div></div>",
                    unsafe_allow_html=True)
                if d["history"] is not None and len(d["history"]) > 3:
                    st.plotly_chart(sparkline(d["history"], ccol),
                                    use_container_width=True,
                                    config={"displayModeBar": False}, key=f"sp_{code}")


# ============================================================
# DIAGNOSTIC
# ============================================================

with st.expander("⚙️  Diagnostic des sources"):
    st.markdown(f"**Indicateurs actifs :** {len(dashboard)} affichés "
                f"({all_series_count()} au catalogue)")
    if errors:
        for code, msg in errors.items():
            st.markdown(f"- `{code}` — {msg}")
        st.caption("Ajuste la clé/les filtres dans `catalog.py` si besoin.")
    else:
        st.success("Toutes les séries du catalogue ont été récupérées.")
    st.caption("© European Central Bank (ECB Data Portal) & Eurostat · CISS © ECB · "
               "récessions CEPR-EABCN.")
