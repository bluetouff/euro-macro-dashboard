"""
Euro Macro Risk Dashboard - tableau de bord style moderne/compact pour la zone euro.
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
    EURO_RECESSION_PERIODS, EURO_AREA_SCOPE, all_series_count,
    visible_series_count,
)
from data import (
    fetch_all_series, compute_dashboard, compute_predictive_power,
    apply_weights, family_scores, global_score, reconstruct_historical_score,
    status_emoji, regime_from_score,
)

# ============================================================
# CONFIG + DESIGN (compact / moderne)
# ============================================================

st.set_page_config(page_title="Euro Macro Risk", page_icon="🇪🇺",
                   layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
  :root{
    --bg:#1a1a1a; --panel:#202020; --panel2:#171717;
    --line:rgba(0,240,208,.16); --line-soft:rgba(255,255,255,.10);
    --txt:#b8fff5; --paper:#e7e9ee; --bright:#f5f6f8;
    --mut:#6f9b94; --faint:#456b65; --accent:#00f0d0; --teal:#5eead4;
    --yen:#ff6b9d; --rose:#ff4d87; --gold:#f5b13d; --orange:#ff8a3d;
    --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
  }
  .stApp{background:radial-gradient(1100px 520px at 50% -8%,rgba(94,234,212,.05),transparent 62%),var(--bg);
    color:var(--txt);font-family:var(--mono);}
  .stApp::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:9999;
    background:repeating-linear-gradient(0deg,rgba(0,0,0,0) 0,rgba(0,0,0,0) 2px,rgba(0,0,0,.08) 3px);
    mix-blend-mode:multiply;opacity:.42;}
  .block-container{padding-top:1.2rem; padding-bottom:2rem; max-width:1220px;}
  #MainMenu,footer{visibility:hidden;}
  h1,h2,h3{color:var(--bright);font-family:var(--mono);letter-spacing:0;}
  .stProgress > div > div{background:var(--accent);}
  hr{border-color:var(--line);}
  .tape{display:flex;flex-wrap:wrap;align-items:baseline;gap:12px 22px;border-bottom:1px solid var(--line);
    padding-bottom:14px;margin-bottom:20px;}
  .brand{color:var(--bright);font-size:1.15rem;font-weight:800;}
  .brand b{color:var(--yen);}
  .tagline{color:var(--mut);font-size:.72rem;letter-spacing:.03em;}
  .top-nav{display:flex;flex-wrap:wrap;gap:8px;margin-left:auto;align-items:center;}
  .nav-link{color:var(--mut) !important;border:1px solid var(--line);border-radius:999px;padding:4px 10px;
    font-size:.7rem;text-decoration:none !important;}
  .nav-link:hover,.nav-link.active{color:var(--bright) !important;border-color:rgba(94,234,212,.65);
    background:rgba(94,234,212,.06);}
  .status-pill{color:var(--mut);border:1px solid var(--line);border-radius:999px;padding:4px 10px;
    font-size:.7rem;display:flex;gap:8px;align-items:center;}
  .status-dot{width:7px;height:7px;border-radius:50%;background:var(--accent);}

  /* ---- hero ---- */
  .title{font-size:24px;font-weight:800;margin:0;color:var(--bright);border-bottom:1px solid var(--line);
    padding-bottom:8px;text-shadow:0 0 30px rgba(94,234,212,.18);}
  .sub{color:var(--mut);font-size:12px;margin-top:9px;line-height:1.5;}
  .hero{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--line);
    border:1px solid var(--line);border-radius:10px;overflow:hidden;margin:18px 0 16px;}
  .stat{background:var(--panel);border:0;border-left:3px solid var(--accent);border-radius:0;padding:15px 16px;min-height:112px;}
  .stat .lab{font-size:10px;color:var(--mut);text-transform:uppercase;letter-spacing:.08em;}
  .stat .big{font-size:34px;font-weight:800;font-family:'SF Mono',ui-monospace,monospace;line-height:1.1;margin-top:2px;}
  .stat .big small{font-size:14px;color:var(--mut);font-weight:600;}
  .pill{display:inline-block;padding:4px 12px;border-radius:999px;font-size:13px;font-weight:700;margin-top:6px;}
  .dots{font-size:13px;font-family:'SF Mono',ui-monospace,monospace;margin-top:10px;color:var(--mut);}

  /* ---- section header ---- */
  .sec{display:flex;align-items:center;gap:10px;margin:20px 0 10px;}
  .sec .ic{font-size:13px;color:var(--yen);}
  .sec .nm{font-size:13px;font-weight:700;color:var(--mut);text-transform:uppercase;letter-spacing:.06em;}
  .sec .ln{flex:1;height:1px;background:var(--line);}
  .sec .bd{font-family:'SF Mono',ui-monospace,monospace;font-size:12px;font-weight:700;
    padding:2px 9px;border-radius:999px;}

  /* ---- tiles grid ---- */
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(168px,1fr));gap:9px;}
  .tile{background:var(--panel);border:1px solid var(--line);border-radius:8px;
    padding:11px 13px 10px;position:relative;overflow:hidden;transition:.15s;}
  .tile:hover{border-color:rgba(94,234,212,.65);background:var(--panel2);}
  .tile::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--c);}
  .tile .nm{font-size:10px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em;
    line-height:1.25;min-height:25px;display:flex;align-items:flex-start;gap:5px;}
  .tile .nm .d{width:7px;height:7px;border-radius:50%;background:var(--c);flex:none;margin-top:3px;}
  .tile .vl{font-size:21px;font-weight:700;font-family:'SF Mono',ui-monospace,monospace;
    color:var(--bright);line-height:1.1;margin-top:5px;}
  .tile .vl u{font-size:11px;color:var(--mut);font-weight:600;text-decoration:none;margin-left:3px;}
  .tile .mt{font-size:10px;font-family:'SF Mono',ui-monospace,monospace;color:var(--mut);margin-top:4px;}
  .tile .mt b{color:var(--c);font-weight:700;}

  /* ---- alerts strip ---- */
  .alerts{display:flex;flex-wrap:wrap;gap:7px;}
  .al{display:flex;align-items:center;gap:8px;background:var(--panel);border:1px solid var(--line);
    border-left:3px solid var(--c);border-radius:8px;padding:7px 11px;}
  .al .an{font-size:11px;color:var(--paper);font-weight:600;}
  .al .av{font-family:'SF Mono',ui-monospace,monospace;font-size:12px;color:var(--c);font-weight:700;}
  .muted{color:var(--mut);font-size:11px;}
  .help-card{background:rgba(255,255,255,.018);border:1px solid var(--line);border-left:2px solid var(--teal);
    border-radius:8px;padding:13px 15px;color:var(--mut);font-size:.82rem;line-height:1.55;margin:8px 0 14px;}
  .help-card strong{color:var(--paper);}
  .faq-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:10px 0 18px;}
  .faq-card{background:rgba(255,255,255,.018);border:1px solid var(--line);border-radius:8px;
    padding:14px 15px;min-height:128px;color:var(--mut);font-size:.82rem;line-height:1.52;}
  .faq-card strong{color:var(--paper);display:block;margin-bottom:6px;}
  .site-footer{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px;
    margin-top:34px;padding:18px 0 6px;border-top:1px solid var(--line);color:var(--faint);font-size:.72rem;}
  .l0g-logo{display:inline-flex;align-items:baseline;gap:2px;color:var(--bright) !important;font-weight:800;text-decoration:none !important;letter-spacing:0;}
  .l0g-logo .slash{color:var(--teal);}
  .l0g-logo:hover{color:var(--teal) !important;}
  .stExpander{border-color:var(--line) !important;}
  @media (max-width:1180px){
    .hero,.faq-grid{grid-template-columns:repeat(2,minmax(0,1fr));}
  }
  @media (max-width:720px){
    .hero,.faq-grid{grid-template-columns:1fr;}
    .top-nav{margin-left:0;}
  }
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


THEME_STATUS_COLORS = {
    "ok": "#5eead4",
    "warning": "#f5b13d",
    "danger": "#ff4d87",
    "unknown": "#456b65",
}
THEME_REGIME_COLORS = {
    "Risk-On / Expansion": "#5eead4",
    "Neutre": "#6f9b94",
    "Prudence / Récession Watch": "#f5b13d",
    "Risk-Off / Stress élevé": "#ff4d87",
    "Indéterminé": "#456b65",
}


def query_value(name: str, default: str = "") -> str:
    value = st.query_params.get(name, default)
    if isinstance(value, list):
        return str(value[0]) if value else default
    return str(value)


def current_view() -> str:
    view = query_value("view", "radar").lower()
    return "faq" if view in {"faq", "help", "aide"} else "radar"


def themed_status_color(status: str) -> str:
    return THEME_STATUS_COLORS.get(status, THEME_STATUS_COLORS["unknown"])


def themed_regime(score: float) -> tuple[str, str]:
    label, _ = regime_from_score(score)
    return label, THEME_REGIME_COLORS.get(label, THEME_STATUS_COLORS["unknown"])


def render_header(view: str, timestamp: str | None = None) -> None:
    radar_active = "active" if view == "radar" else ""
    faq_active = "active" if view == "faq" else ""
    status = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M")
    st.markdown(
        f"""
        <header class="tape">
            <div class="brand"><b>Euro</b> Macro <b>Risk</b></div>
            <div class="tagline">{EURO_AREA_SCOPE} · BCE · Eurostat</div>
            <nav class="top-nav" aria-label="Navigation">
                <a class="nav-link {radar_active}" href="?">Radar</a>
                <a class="nav-link {faq_active}" href="?view=faq">Aide / FAQ</a>
            </nav>
            <div class="status-pill"><span class="status-dot"></span>{status}</div>
        </header>
        """,
        unsafe_allow_html=True,
    )


def render_site_footer() -> None:
    st.markdown(
        """
        <div class="site-footer">
          <a class="l0g-logo" href="https://l0g.fr" target="_blank" rel="noopener" aria-label="l0g.fr">
            <span class="slash">//</span><span>l0g.fr</span>
          </a>
          <span>Euro Macro Risk · MIT License</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_faq_page() -> None:
    st.markdown("<div class='title'>Aide / FAQ</div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="help-card">
          <strong>Objectif.</strong> Euro Macro Risk agrège des séries publiques BCE et Eurostat
          pour surveiller le régime macro de la zone euro. L'outil ne prédit pas une récession
          et ne donne pas de conseil d'investissement : il aide à savoir quels canaux lire en premier.
        </div>
        <div class="faq-grid">
          <div class="faq-card"><strong>Périmètre</strong> Le dashboard suit la composition courante de la zone euro, soit EA21 depuis le 1er janvier 2026. L'agrégat Eurostat évolutif EA n'est utilisé que lorsque le jeu de données le définit ainsi.</div>
          <div class="faq-card"><strong>Score 0-100</strong> Le score combine les indicateurs disponibles avec une pondération heuristique fondée sur leur corrélation historique avec l'état de récession CEPR six mois plus tard. Ce n'est pas une validation prospective.</div>
          <div class="faq-card"><strong>Sources</strong> Les données viennent de sources publiques et gratuites : ECB Data Portal, Eurostat et datation CEPR-EABCN pour les récessions de la zone euro.</div>
          <div class="faq-card"><strong>Lecture</strong> Le score global compte moins que sa composition : il faut regarder si la tension vient des taux, du souverain, du crédit, de l'activité réelle ou du stress systémique.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("Que mesure exactement le radar ?", expanded=True):
        st.markdown(
            """
            Chaque série est comparée à son régime récent via un z-score orienté risque.
            Une valeur élevée n'est pas toujours un risque : certaines séries deviennent risquées
            quand elles baissent, comme la pente de courbe ou la monnaie réelle.
            """
        )
    with st.expander("Pourquoi remplacer le PMI ?"):
        st.markdown(
            """
            Le PMI est propriétaire. Le dashboard utilise donc l'ESI et d'autres séries Eurostat
            ou BCE qui sont publiques, vérifiables et réutilisables sans clé.
            """
        )
    with st.expander("Comment lire les couleurs ?"):
        st.markdown(
            """
            Vert signifie zone normale, jaune tension et rouge alerte, selon l'écart à la moyenne
            mobile 5 ans dans le sens du risque. La couleur est un signal de tri, pas une conclusion
            macro définitive.
            """
        )
    with st.expander("Quelles limites garder en tête ?"):
        st.markdown(
            """
            Certaines séries sont révisées, publiées avec retard ou indisponibles temporairement.
            Le diagnostic liste les séries ignorées afin de garder une lecture transparente.
            """
        )


view = current_view()
render_header(view)
if view == "faq":
    render_faq_page()
    render_site_footer()
    st.stop()


with st.spinner("Connexion BCE & Eurostat…"):
    raw, errors, dashboard, power, hist = load_everything()

g_score = global_score(dashboard)
regime_label, regime_col = themed_regime(g_score)
fam = family_scores(dashboard)
n_ok = sum(1 for d in dashboard.values() if d["status"] == "ok")
n_warn = sum(1 for d in dashboard.values() if d["status"] == "warning")
n_dang = sum(1 for d in dashboard.values() if d["status"] == "danger")
ciss = dashboard.get("CISS")

if errors:
    st.warning(
        f"Données dégradées : {len(dashboard)}/{visible_series_count()} indicateurs actifs. "
        "Les séries absentes ou périmées sont exclues du score et détaillées dans le diagnostic."
    )


# ============================================================
# HERO (titre + stats clés sur une bande compacte)
# ============================================================

st.markdown(
    f"<div class='title'>Euro Macro Risk</div>"
    f"<div class='sub'>BCE + Eurostat · {len(dashboard)} indicateurs · "
    f"MAJ {datetime.now():%d %b %Y %H:%M} · backtest récessions CEPR</div>",
    unsafe_allow_html=True)

ciss_html = ""
if ciss:
    ciss_html = (f"<div class='big' style='color:{themed_status_color(ciss['status'])}'>"
                 f"{ciss['current']:.3f} {status_emoji(ciss['status'])}</div>")
st.markdown(
    f"<div class='hero'>"
    f"<div class='stat' style='border-left-color:{regime_col}'><div class='lab'>Score de risque global</div>"
    f"<div class='big' style='color:{regime_col}'>{g_score:g}<small>/100</small></div></div>"
    f"<div class='stat' style='border-left-color:{regime_col}'><div class='lab'>Régime macro</div>"
    f"<span class='pill' style='background:{regime_col}22;color:{regime_col};"
    f"border:1px solid {regime_col}55'>{regime_label}</span></div>"
    f"<div class='stat' style='border-left-color:{themed_status_color(ciss['status']) if ciss else '#456b65'}'><div class='lab'>New CISS · stress systémique BCE</div>{ciss_html}</div>"
    f"<div class='stat' style='border-left-color:#5eead4'><div class='lab'>État des {len(dashboard)} indicateurs</div>"
    f"<div class='dots'>🟢 {n_ok}&nbsp;&nbsp;🟡 {n_warn}&nbsp;&nbsp;🔴 {n_dang}</div></div>"
    f"</div>", unsafe_allow_html=True)

cc1, cc2 = st.columns([3, 1])
with cc2:
    details = st.toggle("Graphiques détaillés", value=False,
                        help="Affiche les cartes + courbes par indicateur (plus long à scroller).")
with cc1:
    with st.expander("ℹ️  Comment lire ce tableau de bord"):
        st.markdown("""
**Score global 0-100** : agrégation à pondération heuristique (corrélation historique avec
l'état de récession **CEPR** à +6 mois, sans validation hors échantillon). 🟩 <45 Risk-On ·
⬜ 45-55 Neutre · 🟧 55-70 Prudence · 🟥 >70 Stress.

**Couleur d'un indicateur** = *z-score signé* (écart à sa moyenne 5 ans, orienté risque) :
🟢 normal · 🟡 tension (|z|≥1) · 🔴 alerte (|z|≥2). `z` = z-score · `1A` = variation
calendaire sur 1 an, en points pour les taux et en % pour les niveaux de marché.

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
        ccol = themed_status_color(d["status"])
        z = d.get("signed_z", float("nan"))
        chips += (f"<div class='al' style='--c:{ccol}'>{status_emoji(d['status'])}"
                  f"<span class='an'>{d['meta']['name']}</span>"
                  f"<span class='av'>{d['current']:,.2f} · z{z:+.1f}</span></div>")
    st.markdown(f"<div class='alerts'>{chips}</div>", unsafe_allow_html=True)
else:
    st.markdown("<span class='muted'>✓ Aucun signal d'alerte : tous les indicateurs "
                "sont dans leur zone normale.</span>", unsafe_allow_html=True)


# ============================================================
# HISTORIQUE (compact, repliable)
# ============================================================

with st.expander("📈  Score composite historique vs récessions (CEPR)", expanded=False):
    if len(hist) > 12:
        fig = go.Figure()
        for s0, s1 in EURO_RECESSION_PERIODS:
            fig.add_vrect(x0=s0, x1=s1, fillcolor="#ff4d87", opacity=0.15, line_width=0)
        fig.add_trace(go.Scatter(x=hist.index, y=hist.values, mode="lines",
                                 line=dict(color="#5eead4", width=2)))
        fig.add_hline(y=55, line=dict(color="#666", width=1, dash="dot"))
        fig.update_layout(height=240, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font=dict(color="#9a9aa2", family="SF Mono"),
                          margin=dict(l=8, r=8, t=8, b=8),
                          xaxis=dict(gridcolor="#1c1c22"),
                          yaxis=dict(gridcolor="#1c1c22", range=[0, 100]))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("<span class='muted'>Zones rouges = récessions CEPR. Un score >55 "
                    "avant/pendant ces zones fournit une lecture rétrospective, pas une "
                    "validation prospective.</span>",
                    unsafe_allow_html=True)
    else:
        st.info("Historique insuffisant pour reconstruire le score.")


# ============================================================
# MUR D'INDICATEURS - grille dense (vue par défaut)
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
        _, bcol = themed_regime(sc)
        html += (f"<div class='sec'><span class='ic'>{FAMILY_ICONS.get(family,'•')}</span>"
                 f"<span class='nm'>{FAMILY_LABELS.get(family,family)}</span>"
                 f"<span class='ln'></span>"
                 f"<span class='bd' style='background:{bcol}22;color:{bcol}'>{sc:.0f}</span></div>")
        tiles = ""
        for code, meta in active:
            d = dashboard[code]
            ccol = themed_status_color(d["status"])
            unit = meta.get("unit", "")
            z = d.get("signed_z", np.nan)
            m1 = d.get("mom_1y", np.nan)
            mt = f"<b>z {z:+.2f}</b>" if not np.isnan(z) else ""
            if not np.isnan(m1):
                mt += f" · 1A {m1:+.1f}{d.get('mom_unit', '')}"
            tiles += (f"<div class='tile' style='--c:{ccol}'>"
                      f"<div class='nm'><span class='d'></span>{meta['name']}</div>"
                      f"<div class='vl'>{fmt(d['current'], unit)}</div>"
                      f"<div class='mt'>{mt} · au {d['date']:%Y-%m-%d}</div></div>")
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
            ccol = themed_status_color(d["status"])
            with cols[i % len(cols)]:
                unit = meta.get("unit", "")
                sub = []
                if not np.isnan(d.get("signed_z", np.nan)):
                    sub.append(f"z {d['signed_z']:+.2f}")
                if not np.isnan(d.get("mom_1y", np.nan)):
                    sub.append(f"1A {d['mom_1y']:+.1f}{d.get('mom_unit', '')}")
                sub.append(f"au {d['date']:%Y-%m-%d}")
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
                f"sur {visible_series_count()} attendus ({all_series_count()} entrées au catalogue)")
    st.markdown(f"**Périmètre :** {EURO_AREA_SCOPE}")
    if errors:
        for code, msg in errors.items():
            st.markdown(f"- `{code}` : {msg}")
        st.caption("Ajuste la clé/les filtres dans `catalog.py` si besoin.")
    else:
        st.success("Toutes les séries du catalogue ont été récupérées.")
    st.caption("© European Central Bank (ECB Data Portal) & Eurostat · CISS © ECB · "
               "récessions CEPR-EABCN.")

render_site_footer()
