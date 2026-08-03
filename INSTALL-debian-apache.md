# Déploiement sur Debian + Apache

Tutoriel pas-à-pas pour héberger la **version web statique** d'Euro Macro Risk sur
un serveur Debian 12 (« bookworm ») avec Apache, rafraîchissement automatique et HTTPS.

Architecture retenue (la plus sûre) :

```
/opt/euromacro/         ← code + venv Python   (JAMAIS servi par Apache)
   catalog.py  data.py  build_snapshot.py  validate_snapshot.py
   snapshot_contract.py  requirements-prod.txt  index.html  DEPLOYED_SHA
   deploy/...            (confs systemd/apache, refresh.sh)
   .venv/

/var/www/html/euromacro/     ← web root statique    (servi par Apache, lecture seule)
   index.html
   snapshot.js  snapshot.json
```

- Le **constructeur d'instantané** (Python) tourne via un *timer systemd* sous un
  utilisateur dédié non privilégié `euromacro`. Il contacte BCE/Eurostat en **sortie**
  HTTPS uniquement, n'ouvre aucun port.
- Apache ne sert que des fichiers **statiques en lecture seule**. Aucun code exécuté
  côté serveur, aucun secret. Surface d'attaque minimale.

---

## 0. Prérequis

Un serveur Debian 12, un accès `sudo`, et (pour HTTPS) un nom de domaine pointant
vers l'IP du serveur (enregistrement DNS `A`/`AAAA`).

```bash
sudo apt update
sudo apt install -y apache2 python3 python3-venv python3-pip git rsync
```

---

## 1. Utilisateur dédié + arborescence

```bash
# Utilisateur système sans login ni shell interactif
sudo useradd --system --home /opt/euromacro --shell /usr/sbin/nologin euromacro

sudo mkdir -p /opt/euromacro /var/www/html/euromacro
```

---

## 2. Déposer le code

Copiez le contenu du projet dans `/opt/euromacro` (via `scp`, `git clone`, `rsync`…).
Vous devez y retrouver `catalog.py`, `data.py`, `build_snapshot.py`,
`snapshot_contract.py`, `validate_snapshot.py`, `requirements-prod.txt`, `index.html`
et le dossier `deploy/`. Écrivez ensuite le SHA Git exact du code copié.

```bash
# exemple depuis votre poste :
# rsync -av euro_macro_dashboard/ user@serveur:/tmp/euromacro/
sudo rsync -a /tmp/euromacro/ /opt/euromacro/
printf '%s\n' 'REMPLACER_PAR_LE_SHA_GIT_40_CARACTERES' | sudo tee /opt/euromacro/DEPLOYED_SHA
sudo chown -R euromacro:euromacro /opt/euromacro
```

---

## 3. Environnement Python (venv)

```bash
sudo -u euromacro python3 -m venv /opt/euromacro/.venv
sudo -u euromacro /opt/euromacro/.venv/bin/pip install --upgrade pip
sudo -u euromacro /opt/euromacro/.venv/bin/pip install -r /opt/euromacro/requirements-prod.txt
```

> La version web n'a besoin que de `pandas`, `numpy`, `requests` (présents dans
> `requirements-prod.txt`). Streamlit/plotly ne servent qu'à l'app interactive locale.

---

## 4. Web root statique

```bash
# Droits : propriété euromacro, lecture pour Apache (www-data via "others")
sudo chown -R euromacro:www-data /var/www/html/euromacro
sudo find /var/www/html/euromacro -type d -exec chmod 755 {} \;
sudo find /var/www/html/euromacro -type f -exec chmod 644 {} \;
```

---

## 5. Premier instantané

```bash
sudo chmod +x /opt/euromacro/deploy/refresh.sh
sudo -u euromacro /opt/euromacro/deploy/refresh.sh
```

Vous devez voir la validation du contrat, puis `Publié dans /var/www/html/euromacro` avec
le SHA attendu. Le script publie `index.html`, `snapshot.js` et `snapshot.json`. Si le build
ou la promotion échoue, il ne remplace pas le lot public valide.

> **Pare-feu / proxy** : la machine doit pouvoir joindre en sortie HTTPS (443)
> `data-api.ecb.europa.eu` et `ec.europa.eu`. Aucun port entrant n'est requis pour le build.

---

## 6. Rafraîchissement automatique (timer systemd)

```bash
sudo cp /opt/euromacro/deploy/euromacro-snapshot.service /etc/systemd/system/
sudo cp /opt/euromacro/deploy/euromacro-snapshot.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now euromacro-snapshot.timer

# Vérifs
systemctl list-timers euromacro-snapshot.timer
sudo systemctl start euromacro-snapshot.service   # lancer un build à la demande
journalctl -u euromacro-snapshot.service --no-pager   # voir les logs
```

Le timer régénère l'instantané chaque jour à ~07h30 (avec délai aléatoire).

---

## 7. Vhost Apache

```bash
sudo a2enmod headers
sudo cp /opt/euromacro/deploy/euromacro-apache.conf /etc/apache2/sites-available/euromacro.conf

# Remplacez le nom de domaine
sudo sed -i 's/euromacro.example.com/VOTRE-DOMAINE.fr/' /etc/apache2/sites-available/euromacro.conf

sudo a2ensite euromacro.conf
sudo a2dissite 000-default.conf          # optionnel : retire le site par défaut
sudo apache2ctl configtest               # doit afficher "Syntax OK"
sudo systemctl reload apache2
```

Le site répond maintenant en HTTP sur votre domaine.

---

## 8. HTTPS (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-apache
sudo certbot --apache -d VOTRE-DOMAINE.fr
```

Certbot ajoute le vhost `:443`, configure le certificat et la redirection HTTP→HTTPS.
Le renouvellement est automatique (timer `certbot.timer`). Pour tester le renouvellement :

```bash
sudo certbot renew --dry-run
```

---

## 9. Vérifications de sécurité

```bash
# Le listing de répertoire est désactivé -> 403
curl -I https://VOTRE-DOMAINE.fr/

# Les fichiers sensibles ne sont pas servis -> 403/404
curl -I https://VOTRE-DOMAINE.fr/build_snapshot.py
curl -I https://VOTRE-DOMAINE.fr/snapshot.json    # 200 (donnée publique, OK)

# En-têtes de sécurité présents
curl -sI https://VOTRE-DOMAINE.fr/ | grep -iE 'content-security|x-content|x-frame|referrer'

# Le snapshot public expose le SHA exact et son état de qualité
curl -fsS https://VOTRE-DOMAINE.fr/snapshot.json | python3 -m json.tool | head -40
```

Bonnes pratiques complémentaires :
- Pare-feu : n'ouvrir que 80/443 entrants (`ufw allow 'WWW Full'`, `ufw enable`).
- Garder `/opt/euromacro` hors du `DocumentRoot` (déjà le cas ici).
- Mises à jour système régulières (`unattended-upgrades`).
- Le code Python (catalog/data/build) n'est jamais exposé : seul `index.html` +
  `snapshot.js/json` vivent dans le web root.

---

## Mettre à jour les données / le code sans casser la production

- **Données** : automatique via le timer, ou à la demande avec
  `sudo systemctl start euromacro-snapshot.service`.
- **Code** : préparez ailleurs un checkout propre du SHA à livrer, lancez les tests et un
  build complet, puis copiez ce checkout dans `/opt/euromacro` en excluant `.git` et `.venv`.
  Écrivez le même SHA dans `/opt/euromacro/DEPLOYED_SHA`, mettez à jour les dépendances de
  production et démarrez le service. Ne modifiez pas directement le web root.
- **Contrôle** : vérifiez le code HTTP, les en-têtes, `generated_at`, `source_sha`,
  `quality.status` et une série modifiée sur le site public.
- **Retour arrière** : le dernier lot statique reste dans `/opt/euromacro/.last-good/`.
  Restaurez aussi le checkout applicatif précédent avant de relancer le service si le code
  lui-même doit être annulé.

## Dépannage

| Symptôme | Piste |
|---|---|
| Page « Aucun instantané trouvé » | `snapshot.js` absent du web root → lancer `refresh.sh` |
| `refresh.sh` échoue sur le réseau | sortie HTTPS vers ECB/Eurostat bloquée (proxy/pare-feu) |
| 403 sur `index.html` | droits fichiers (`chmod 644`) / propriété (`chown euromacro:www-data`) |
| Série en erreur dans le diagnostic | ajuster sa clé/ses filtres dans `catalog.py`, rebuild |
| Timer ne se déclenche pas | `systemctl list-timers`, `journalctl -u euromacro-snapshot` |
