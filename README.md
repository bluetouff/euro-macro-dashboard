<!-- README.md -->
# 🇪🇺 Euro Macro Risk Dashboard

**Un tableau de bord qui résume, en un coup d'œil, le niveau de risque économique de la zone euro, à partir de données 100% officielles et gratuites (BCE + Eurostat).**

*A dashboard that summarises, at a glance, the economic risk level of the euro area — built entirely on official, free data (ECB + Eurostat).*

🔗 **Démo en ligne / Live demo : [euro.l0g.fr](https://euro.l0g.fr)**

---

## 🇫🇷 Version française

### C'est quoi, en deux phrases ?

Ce projet récupère une trentaine d'indicateurs économiques de la zone euro (taux d'intérêt, inflation, chômage, crédit, marchés, faillites…), les compare à leur propre histoire, et en tire **un score de risque global de 0 à 100** ainsi qu'une liste de **signaux d'alerte**. Le périmètre est la composition courante de la zone euro, soit **EA21 depuis le 1er janvier 2026**. Une série sans valeur EA21 ou trop ancienne est exclue du score et signalée dans le diagnostic.

### Ce que vous voyez à l'écran

- **Score de risque global (0-100)** : plus il est élevé, plus le contexte est tendu.
  🟩 moins de 45 = expansion · ⬜ 45-55 = neutre · 🟧 55-70 = prudence · 🟥 plus de 70 = stress.
- **Couleur de chaque indicateur** : verte (normal), jaune (tension), rouge (alerte). La couleur ne dépend pas d'un seuil absolu mais de **l'écart de l'indicateur par rapport à son comportement des 5 dernières années**, dans le sens du risque.
- **⏰ Signaux avancés** : les indicateurs qui *précèdent* le cycle (pente des taux, monnaie, anticipations d'emploi). Ce sont les premiers à bouger avant un retournement.
- **Historique** : le score reconstruit depuis 2008, superposé à la datation CEPR des récessions. Cette lecture rétrospective est descriptive et ne constitue pas une validation hors échantillon.

### Comment lire une tuile

`z` = écart à la moyenne 5 ans (en écarts-types). `1A` = variation calendaire sur un an. Elle est exprimée en points pour les taux, soldes et indices macro, et en pourcentage pour les niveaux de marché. Chaque tuile indique la date de sa dernière observation et donne un lien vers la série primaire exacte.

### D'où viennent les données ?

Uniquement des **sources officielles publiques, sans clé d'accès** :
- **BCE** (ECB Data Portal) : taux directeurs, €STR, CISS (indice de stress de la BCE), rendements souverains, monnaie, crédit, chômage…
- **Eurostat** : inflation HICP, production industrielle, ventes de détail, confiance, sentiment économique (ESI), faillites d'entreprises…

> Le PMI (propriétaire) est remplacé par l'**ESI** de la Commission européenne, l'équivalent officiel et gratuit.

**Lacune connue au 3 août 2026.** Le jeu Eurostat `sts_rb_q` déclare la modalité
EA21 mais ne renvoie encore aucune observation de faillites pour cette combinaison.
`BANKRUPT` reste donc au catalogue mais est exclu du score, avec un diagnostic public,
jusqu'à ce qu'Eurostat publie les valeurs EA21. Le builder reteste la série à chaque mise à jour.

### Deux façons de l'utiliser

**A) Version web statique (recommandée, la plus simple et la plus sûre)**
Un script Python génère un « instantané » des données, et une simple page HTML l'affiche. Aucun serveur, aucune clé, aucun appel réseau depuis le navigateur.

```bash
pip install -r requirements.txt
python build_snapshot.py            # génère snapshot.js
python validate_snapshot.py         # valide couverture, dates et traçabilité
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
- Le générateur refuse un snapshot trop incomplet ou sans révision source identifiable.
- La publication serveur conserve le dernier lot valide et promeut les fichiers préparés atomiquement.
- Pour un déploiement serveur durci (Apache/Debian, utilisateur dédié, HTTPS, rafraîchissement automatique), voir **[INSTALL-debian-apache.md](INSTALL-debian-apache.md)**.

### Avertissement

Outil d'information uniquement. **Ce n'est pas un conseil en investissement.** Les données peuvent comporter des erreurs ou des retards ; vérifiez toujours auprès des sources primaires.

---

## 🇬🇧 English version

### What is it, in two sentences?

This project pulls ~30 euro-area economic indicators (interest rates, inflation, unemployment, credit, markets, bankruptcies…), compares each to its own history, and derives **a global risk score from 0 to 100** plus a list of **alert signals**. Its scope is the euro area's current composition, **EA21 since 1 January 2026**. A series without EA21 observations or with an outdated latest observation is excluded from the score and disclosed in diagnostics.

### What you see on screen

- **Global risk score (0-100)**: the higher, the more stressed the environment.
  🟩 below 45 = expansion · ⬜ 45-55 = neutral · 🟧 55-70 = caution · 🟥 above 70 = stress.
- **Colour of each indicator**: green (normal), yellow (tension), red (alert). The colour reflects **how far the indicator deviates from its own 5-year behaviour**, in the direction of risk — not an absolute threshold.
- **⏰ Leading signals**: indicators that *lead* the cycle (yield-curve slope, money growth, employment expectations). They move first.
- **History**: the score reconstructed since 2008 and overlaid with CEPR recession dating. This retrospective view is descriptive, not an out-of-sample validation.

### Reading a tile

`z` = deviation from the 5-year mean (in standard deviations). `1A` = calendar one-year change, in points for rates and macro indices and in percent for market levels. Each tile displays its latest observation date and links to the exact primary series.

### Where does the data come from?

Only **official, public, key-free sources**:
- **ECB** (ECB Data Portal): policy rates, €STR, CISS (the ECB's own systemic-stress index), sovereign yields, money, credit, unemployment…
- **Eurostat**: HICP inflation, industrial production, retail sales, confidence, Economic Sentiment Indicator (ESI), corporate bankruptcies…

> PMI (proprietary) is replaced by the European Commission's **ESI**, the free official equivalent.

**Known gap as of 3 August 2026.** Eurostat dataset `sts_rb_q` exposes the EA21
category but currently returns no bankruptcy observation for this combination.
`BANKRUPT` remains in the catalogue but is excluded from the score, with a public
diagnostic, until Eurostat publishes EA21 values. Every refresh retries the series.

### Two ways to run it

**A) Static web version (recommended — simplest and safest)**
A Python script builds a data "snapshot"; a plain HTML page renders it. No server, no key, no network calls from the browser.

```bash
pip install -r requirements.txt
python build_snapshot.py            # generates snapshot.js
python validate_snapshot.py         # validates coverage, dates and traceability
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
- The builder rejects snapshots with insufficient coverage or no identifiable source revision.
- Server publication keeps the last valid set and promotes staged files atomically.
- For a hardened server deployment (Apache/Debian, dedicated user, HTTPS, auto-refresh), see **[INSTALL-debian-apache.md](INSTALL-debian-apache.md)** (French).

### Disclaimer

Informational tool only. **This is not investment advice.** Data may contain errors or delays; always verify against primary sources.

---

## 🛠️ Méthodologie / Methodology (résumé)

1. **Baseline** : moyenne pré-Covid (2015-2019) de chaque série. / Pre-Covid mean as a "normality" anchor.
2. **Z-score glissant 5 ans**, orienté risque. / Rolling 5-year z-score, risk-oriented.
3. **Pondération heuristique** : corrélation historique de chaque série, ramenée sur une grille mensuelle, avec l'état de récession CEPR six mois plus tard. Cette corrélation n'est ni causale ni une validation prospective. / **Heuristic weighting**: historical correlation on a common monthly grid with the CEPR recession state six months later; it is neither causal nor an out-of-sample validation.
4. **Score global 0-100** + reconstruction historique. / Global 0-100 score + historical reconstruction.

## 📁 Fichiers / Files

```
index.html                Page web statique / static web page
build_snapshot.py         Génère snapshot.js / builds the snapshot
snapshot_contract.py      Contrat de publication / publication contract
validate_snapshot.py      Validation avant publication / pre-publication validation
app.py                    App interactive Streamlit / interactive app
catalog.py                Séries + règles de scoring / series + scoring rules
data.py                   Récupération + moteur de scoring / fetch + scoring engine
requirements-prod.txt     Dépendances du constructeur statique / static builder dependencies
deploy/                   Confs Apache + systemd / Apache + systemd configs
INSTALL-debian-apache.md  Tuto serveur / server tutorial
```

## 📜 Licence / License

MIT — voir [LICENSE](LICENSE).

## 🙏 Crédits / Credits

Données / Data: © European Central Bank (ECB Data Portal) · © Eurostat · CISS © ECB ·
Datation des récessions / recession dating: CEPR-EABCN.
