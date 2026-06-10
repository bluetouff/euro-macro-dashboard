<!-- README.md -->
# 🇪🇺 Euro Macro Risk Dashboard

**Un tableau de bord qui résume, en un coup d'œil, le niveau de risque économique de la zone euro — à partir de données 100% officielles et gratuites (BCE + Eurostat).**

*A dashboard that summarises, at a glance, the economic risk level of the euro area — built entirely on official, free data (ECB + Eurostat).*

🔗 **Démo en ligne / Live demo : [euro.l0g.fr](https://euro.l0g.fr)**

---

## 🇫🇷 Version française

### C'est quoi, en deux phrases ?

Ce projet récupère une trentaine d'indicateurs économiques de la zone euro (taux d'intérêt, inflation, chômage, crédit, marchés, faillites…), les compare à leur propre histoire, et en tire **un score de risque global de 0 à 100** ainsi qu'une liste de **signaux d'alerte**. Le but : repérer tôt la montée des risques, comme le ferait une salle de marché, mais avec des sources publiques et vérifiables.

### Ce que vous voyez à l'écran

- **Score de risque global (0-100)** : plus il est élevé, plus le contexte est tendu.
  🟩 moins de 45 = expansion · ⬜ 45-55 = neutre · 🟧 55-70 = prudence · 🟥 plus de 70 = stress.
- **Couleur de chaque indicateur** : verte (normal), jaune (tension), rouge (alerte). La couleur ne dépend pas d'un seuil absolu mais de **l'écart de l'indicateur par rapport à son comportement des 5 dernières années**, dans le sens du risque.
- **⏰ Signaux avancés** : les indicateurs qui *précèdent* le cycle (pente des taux, monnaie, anticipations d'emploi). Ce sont les premiers à bouger avant un retournement.
- **Historique** : le score reconstruit depuis 2008, superposé aux récessions officielles de la zone euro (datation CEPR), pour vérifier qu'il « voyait venir » les crises passées.

### Comment lire une tuile

`z` = écart à la moyenne 5 ans (en écarts-types). `1A` = variation sur un an. Une couleur rouge = l'indicateur est anormalement orienté vers le risque, pas seulement « haut ».

### D'où viennent les données ?

Uniquement des **sources officielles publiques, sans clé d'accès** :
- **BCE** (ECB Data Portal) : taux directeurs, €STR, CISS (indice de stress de la BCE), rendements souverains, monnaie, crédit, chômage…
- **Eurostat** : inflation HICP, production industrielle, ventes de détail, confiance, sentiment économique (ESI), faillites d'entreprises…

> Le PMI (propriétaire) est remplacé par l'**ESI** de la Commission européenne, l'équivalent officiel et gratuit.

### Deux façons de l'utiliser

**A) Version web statique (recommandée, la plus simple et la plus sûre)**
Un script Python génère un « instantané » des données, et une simple page HTML l'affiche. Aucun serveur, aucune clé, aucun appel réseau depuis le navigateur.

```bash
pip install -r requirements.txt
python build_snapshot.py            # génère snapshot.js
python -m http.server 8000          # puis ouvrez http://localhost:8000
```

**B) Version interactive (Streamlit)**

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Sécurité

- Aucune clé API, aucun secret (les sources sont publiques).
- En mode web, la page est **100% statique** : pas de code exécuté côté serveur, donc surface d'attaque minimale.
- La page embarque une Content-Security-Policy stricte.
- Pour un déploiement serveur durci (Apache/Debian, utilisateur dédié, HTTPS, rafraîchissement automatique), voir **[INSTALL-debian-apache.md](INSTALL-debian-apache.md)**.

### Avertissement

Outil d'information uniquement. **Ce n'est pas un conseil en investissement.** Les données peuvent comporter des erreurs ou des retards ; vérifiez toujours auprès des sources primaires.

---

## 🇬🇧 English version

### What is it, in two sentences?

This project pulls ~30 euro-area economic indicators (interest rates, inflation, unemployment, credit, markets, bankruptcies…), compares each to its own history, and derives **a global risk score from 0 to 100** plus a list of **alert signals**. The goal: spot rising risk early, like a trading desk would, but using public, verifiable sources.

### What you see on screen

- **Global risk score (0-100)**: the higher, the more stressed the environment.
  🟩 below 45 = expansion · ⬜ 45-55 = neutral · 🟧 55-70 = caution · 🟥 above 70 = stress.
- **Colour of each indicator**: green (normal), yellow (tension), red (alert). The colour reflects **how far the indicator deviates from its own 5-year behaviour**, in the direction of risk — not an absolute threshold.
- **⏰ Leading signals**: indicators that *lead* the cycle (yield-curve slope, money growth, employment expectations). They move first.
- **History**: the score reconstructed since 2008, overlaid with official euro-area recessions (CEPR dating), to check it "saw" past crises coming.

### Reading a tile

`z` = deviation from the 5-year mean (in standard deviations). `1A` = year-on-year change. A red tile means the indicator is abnormally tilted toward risk, not merely "high".

### Where does the data come from?

Only **official, public, key-free sources**:
- **ECB** (ECB Data Portal): policy rates, €STR, CISS (the ECB's own systemic-stress index), sovereign yields, money, credit, unemployment…
- **Eurostat**: HICP inflation, industrial production, retail sales, confidence, Economic Sentiment Indicator (ESI), corporate bankruptcies…

> PMI (proprietary) is replaced by the European Commission's **ESI**, the free official equivalent.

### Two ways to run it

**A) Static web version (recommended — simplest and safest)**
A Python script builds a data "snapshot"; a plain HTML page renders it. No server, no key, no network calls from the browser.

```bash
pip install -r requirements.txt
python build_snapshot.py            # generates snapshot.js
python -m http.server 8000          # then open http://localhost:8000
```

**B) Interactive version (Streamlit)**

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Security

- No API keys, no secrets (sources are public).
- In web mode the page is **fully static**: no server-side code, minimal attack surface.
- A strict Content-Security-Policy is embedded.
- For a hardened server deployment (Apache/Debian, dedicated user, HTTPS, auto-refresh), see **[INSTALL-debian-apache.md](INSTALL-debian-apache.md)** (French).

### Disclaimer

Informational tool only. **This is not investment advice.** Data may contain errors or delays; always verify against primary sources.

---

## 🛠️ Méthodologie / Methodology (résumé)

1. **Baseline** : moyenne pré-Covid (2015-2019) de chaque série. / Pre-Covid mean as a "normality" anchor.
2. **Z-score glissant 5 ans**, orienté risque. / Rolling 5-year z-score, risk-oriented.
3. **Pondération par pouvoir prédictif** : plus un indicateur a historiquement anticipé les récessions CEPR, plus il pèse. / Weighting by predictive power vs CEPR recessions.
4. **Score global 0-100** + reconstruction historique. / Global 0-100 score + historical reconstruction.

## 📁 Fichiers / Files

```
index.html                Page web statique / static web page
build_snapshot.py         Génère snapshot.js / builds the snapshot
app.py                    App interactive Streamlit / interactive app
catalog.py                Séries + règles de scoring / series + scoring rules
data.py                   Récupération + moteur de scoring / fetch + scoring engine
deploy/                   Confs Apache + systemd / Apache + systemd configs
INSTALL-debian-apache.md  Tuto serveur / server tutorial
```

## 📜 Licence / License

MIT — voir [LICENSE](LICENSE).

## 🙏 Crédits / Credits

Données / Data: © European Central Bank (ECB Data Portal) · © Eurostat · CISS © ECB ·
Datation des récessions / recession dating: CEPR-EABCN.
