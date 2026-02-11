# Deploiement Email Engine - Guide 10 jours

## Jour 1-2 : Commander et preparer

### Commander
- [ ] VDS Contabo S (30EUR/mois, 5 IPs dediees)
- [ ] VPS Contabo M (10EUR/mois)
- [ ] 3 domaines cold-outreach-X.com (~10EUR/an chacun)
- [ ] Licence PowerMTA

### Configurer DNS (attendre propagation 24-48h)
- [ ] DNS pour trans.mail-ulixai.com (voir dns/dns-templates.md)
- [ ] DNS pour news.sos-expat.com
- [ ] DNS pour cold-outreach-1.com
- [ ] DNS pour cold-outreach-2.com
- [ ] DNS pour cold-outreach-3.com

## Jour 3-4 : Installer VDS (PowerMTA)

```bash
ssh root@VDS_IP

# Systeme
apt update && apt upgrade -y
apt install -y bc host curl wget

# Installer PowerMTA (suivre guide Port25)
# ...

# Copier config
scp powermta/config root@VDS_IP:/etc/pmta/config

# Generer DKIM
scp scripts/generate-dkim.sh root@VDS_IP:/root/scripts/
chmod +x /root/scripts/generate-dkim.sh
/root/scripts/generate-dkim.sh
# -> Noter les cles publiques, les ajouter en DNS

# Configurer PTR chez Contabo (panel admin)
# IP1 -> trans.mail-ulixai.com
# IP2 -> news.sos-expat.com
# IP3 -> cold-outreach-1.com
# IP4 -> cold-outreach-2.com
# IP5 -> cold-outreach-3.com

# Demarrer
systemctl start powermta
systemctl enable powermta
pmta show status
```

## Jour 5-6 : Installer VPS (MailWizz)

Suivre mailwizz/INSTALL.md

## Jour 7 : Connecter MailWizz -> PowerMTA

- [ ] Creer 3 Delivery Servers dans MailWizz
- [ ] Creer les listes (SOS-Expat + Ulixai)
- [ ] Creer les API keys
- [ ] Test envoi email

## Jour 8 : Scripts operationnels

```bash
# Copier scripts sur VDS
scp scripts/*.sh root@VDS_IP:/root/scripts/
ssh root@VDS_IP "chmod +x /root/scripts/*.sh"

# Configurer cron
ssh root@VDS_IP "crontab -e"
# Ajouter:
# 0 2 * * * /root/scripts/backup-all.sh
# 0 */4 * * * /root/scripts/check-blacklists.sh
# 0 0 * * * /root/scripts/warmup-daily-adjust.sh
# */5 * * * * /root/scripts/health-check.sh
# 0 3 1 * * /root/scripts/ip-rotation.sh
```

## Jour 9 : Monitoring

- [ ] Creer compte Grafana Cloud (gratuit)
- [ ] Installer Grafana Agent sur VDS + VPS
- [ ] Importer alertes (monitoring/grafana-alerts.yml)
- [ ] Configurer bot Telegram pour alertes
- [ ] Test alerte

## Jour 10 : Tests finaux

```bash
# Test 1: Mail-Tester (score > 9/10)
echo "Test" | mail -s "Test" test-xxx@mail-tester.com

# Test 2: DKIM (envoyer vers Gmail, verifier headers)
# DKIM=pass attendu

# Test 3: Blacklist check
/root/scripts/check-blacklists.sh
# 0 blacklists attendu

# Test 4: Monitoring
# Verifier Grafana affiche metriques

# Test 5: Health check
/root/scripts/health-check.sh
```

## Checklist GO/NO-GO

- [ ] DNS propages (24h+)
- [ ] PowerMTA running
- [ ] MailWizz accessible HTTPS
- [ ] Delivery Servers actifs
- [ ] Mail-Tester > 9/10
- [ ] 0 IP blacklistees
- [ ] Monitoring operationnel
- [ ] Alertes Telegram OK
- [ ] Backups configures
- [ ] Warm-up plan cree

**Si TOUS OK -> GO PRODUCTION**
