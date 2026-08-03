# Security Policy / Politique de sécurité

## 🇬🇧 English

**Design.** This project has no secrets and no API keys: all data comes from public
ECB and Eurostat endpoints. The recommended deployment serves a **fully static** page
(`index.html` + a generated `snapshot.js`); no server-side code runs to answer requests.

**Hardening (server deployment).**
- The data builder (`build_snapshot.py`) runs under a dedicated unprivileged user via a
  hardened systemd unit (`NoNewPrivileges`, `ProtectSystem=strict`, restricted write paths).
- Production snapshots must carry the exact deployed Git SHA. Coverage, critical indicators,
  source dates and source links are validated before publication.
- The refresh process stages all public files, keeps the last good set and restores it if
  promotion fails.
- It only makes **outbound** HTTPS calls to ECB/Eurostat; it opens no inbound port.
- The web root is read-only for the web server; application code lives outside it.
- The page ships a strict Content-Security-Policy (`default-src 'none'`).
- See `INSTALL-debian-apache.md` for the full hardened Apache/Debian setup.

**Reporting.** Please open a private security advisory or an issue (without sensitive
details) to report a vulnerability.

## 🇫🇷 Français

**Conception.** Aucun secret, aucune clé API : toutes les données proviennent d'endpoints
publics BCE et Eurostat. Le déploiement recommandé sert une page **100% statique**
(`index.html` + `snapshot.js` généré) ; aucun code n'est exécuté côté serveur pour
répondre aux requêtes.

**Durcissement (déploiement serveur).**
- Le générateur (`build_snapshot.py`) tourne sous un utilisateur dédié non privilégié
  via une unité systemd durcie (`NoNewPrivileges`, `ProtectSystem=strict`, écriture limitée).
- Les instantanés de production doivent porter le SHA Git exact déployé. La couverture, les
  indicateurs critiques, les dates et les liens sources sont validés avant publication.
- Le rafraîchissement prépare tous les fichiers, conserve le dernier lot valide et le restaure
  si la promotion échoue.
- Il ne fait que des appels HTTPS **sortants** vers BCE/Eurostat ; aucun port entrant.
- Le web root est en lecture seule pour le serveur web ; le code applicatif est en dehors.
- La page embarque une Content-Security-Policy stricte (`default-src 'none'`).
- Voir `INSTALL-debian-apache.md` pour l'installation Apache/Debian durcie complète.

**Signalement.** Merci d'ouvrir un avis de sécurité privé ou une issue (sans détails
sensibles) pour signaler une vulnérabilité.
