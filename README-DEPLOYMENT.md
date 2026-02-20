# 🚀 Déploiement Email-Engine - Multi-Serveurs

## 📋 Vue d'ensemble

**Architecture** : 2 VPS indépendants + 1 API orchestration

```
VPS 1 : MailWizz (sos-holidays.com)
VPS 2 : PowerMTA (5 IPs + 5 domaines)
Local : Email-Engine API (orchestration)
```

---

## 🎯 DÉPLOIEMENT RAPIDE

### 1. VPS 1 : MailWizz (sos-holidays.com)

```bash
# Se connecter au VPS1
ssh root@sos-holidays.com

# Télécharger script d'installation
cd /root
git clone https://github.com/[user]/email-engine.git
cd email-engine/deploy/vps1-mailwizz

# Copier archives depuis backup-source
scp backup-source/mailwizz-prod-20260216.tar.gz root@sos-holidays.com:/root/
scp backup-source/mailapp-prod-20260216.sql.gz root@sos-holidays.com:/root/

# Installer
./install-mailwizz.sh
```

### 2. VPS 2 : PowerMTA (5 IPs)

```bash
# Se connecter au VPS2
ssh root@[VPS2_IP]

# Télécharger script
cd /root
git clone https://github.com/[user]/email-engine.git
cd email-engine/deploy/vps2-pmta

# Copier config PowerMTA
scp backup-source/pmta-config-20260216 root@[VPS2_IP]:/root/
scp backup-source/pmta-license-20260216 root@[VPS2_IP]:/root/

# Installer
./install-pmta.sh
```

### 3. Local : Email-Engine API

```bash
# Depuis Windows
cd C:\Users\willi\Documents\Projets\VS_CODE\email-engine

# Configurer .env
cp .env.example .env.production
nano .env.production

# Remplir :
# MAILWIZZ_URL=https://sos-holidays.com/api
# MAILWIZZ_API_KEY=xxx
# PMTA_SSH_HOST=[VPS2_IP]
# PMTA_SSH_USER=root
# PMTA_SSH_KEY=/path/to/ssh/key

# Démarrer
docker-compose -f docker-compose.prod.yml up -d
```

---

## 📦 FICHIERS NÉCESSAIRES

### backup-source/ (copié de backup-cold)
```
✅ mailwizz-prod-20260216.tar.gz  (111 MB)
✅ mailapp-prod-20260216.sql.gz   (810 KB)
✅ pmta-config-20260216           (9 KB)
✅ pmta-license-20260216          (391 B)
```

---

## 🔧 CONFIGURATION DÉTAILLÉE

### VPS 1 : Variables d'environnement

```bash
# /var/www/html/mailwizz/.env

DB_HOST=localhost
DB_NAME=mailwizz
DB_USER=mailwizz
DB_PASS=[STRONG_PASSWORD]

DELIVERY_SERVER_HOST=[VPS2_IP]
DELIVERY_SERVER_PORT=2525
DELIVERY_SERVER_USER=mailwizz
DELIVERY_SERVER_PASS=[SMTP_PASSWORD]
```

### VPS 2 : Configuration PowerMTA

```ini
# /etc/pmta/config

# SMTP Relay (depuis MailWizz)
smtp-listener 0.0.0.0:2525 {
    listen-on-tcp yes
    process-x-virtual-mta yes
}

# Virtual MTAs (5 domaines)
virtual-mta vmta-1 {
    smtp-source-host mail1.domain1.com [IP1]
    domain-key domain1.com,*,/etc/pmta/dkim/domain1.pem
}

virtual-mta vmta-2 {
    smtp-source-host mail2.domain2.com [IP2]
    domain-key domain2.com,*,/etc/pmta/dkim/domain2.pem
}

virtual-mta vmta-3 {
    smtp-source-host mail3.domain3.com [IP3]
    domain-key domain3.com,*,/etc/pmta/dkim/domain3.pem
}

virtual-mta vmta-4 {
    smtp-source-host mail4.domain4.com [IP4]
    domain-key domain4.com,*,/etc/pmta/dkim/domain4.pem
}

virtual-mta vmta-5 {
    smtp-source-host mail5.domain5.com [IP5]
    domain-key domain5.com,*,/etc/pmta/dkim/domain5.pem
}

# Bounce handling
<acct-file /var/log/pmta/acct.csv>
    records all
</acct-file>
```

---

## 🌐 DNS À CONFIGURER

### Pour chaque domaine (domain1.com à domain5.com)

```dns
# A Records (5 domaines)
mail1.domain1.com.  A  [IP1]
mail2.domain2.com.  A  [IP2]
mail3.domain3.com.  A  [IP3]
mail4.domain4.com.  A  [IP4]
mail5.domain5.com.  A  [IP5]

# SPF (5 domaines)
domain1.com.  TXT  "v=spf1 ip4:[IP1] ~all"
domain2.com.  TXT  "v=spf1 ip4:[IP2] ~all"
domain3.com.  TXT  "v=spf1 ip4:[IP3] ~all"
domain4.com.  TXT  "v=spf1 ip4:[IP4] ~all"
domain5.com.  TXT  "v=spf1 ip4:[IP5] ~all"

# DKIM (5 domaines)
mail._domainkey.domain1.com.  TXT  "v=DKIM1; k=rsa; p=[PUBLIC_KEY_1]"
mail._domainkey.domain2.com.  TXT  "v=DKIM1; k=rsa; p=[PUBLIC_KEY_2]"
mail._domainkey.domain3.com.  TXT  "v=DKIM1; k=rsa; p=[PUBLIC_KEY_3]"
mail._domainkey.domain4.com.  TXT  "v=DKIM1; k=rsa; p=[PUBLIC_KEY_4]"
mail._domainkey.domain5.com.  TXT  "v=DKIM1; k=rsa; p=[PUBLIC_KEY_5]"

# DMARC (5 domaines)
_dmarc.domain1.com.  TXT  "v=DMARC1; p=none; rua=mailto:dmarc@domain1.com"
_dmarc.domain2.com.  TXT  "v=DMARC1; p=none; rua=mailto:dmarc@domain2.com"
_dmarc.domain3.com.  TXT  "v=DMARC1; p=none; rua=mailto:dmarc@domain3.com"
_dmarc.domain4.com.  TXT  "v=DMARC1; p=none; rua=mailto:dmarc@domain4.com"
_dmarc.domain5.com.  TXT  "v=DMARC1; p=none; rua=mailto:dmarc@domain5.com"

# PTR (Reverse DNS - configurer chez provider)
[IP1]  PTR  mail1.domain1.com.
[IP2]  PTR  mail2.domain2.com.
[IP3]  PTR  mail3.domain3.com.
[IP4]  PTR  mail4.domain4.com.
[IP5]  PTR  mail5.domain5.com.
```

---

## ✅ TESTS POST-DÉPLOIEMENT

### Test 1 : MailWizz accessible
```bash
curl https://sos-holidays.com
# Doit afficher page MailWizz
```

### Test 2 : API MailWizz fonctionne
```bash
curl -X GET https://sos-holidays.com/api \
  -H "X-API-KEY: [API_KEY]"
# Doit retourner {"status": "success"}
```

### Test 3 : PowerMTA écoute
```bash
telnet [VPS2_IP] 2525
# Doit afficher "220 PowerMTA ready"
```

### Test 4 : Email E2E
```bash
# 1. Ajouter contact via API MailWizz
curl -X POST https://sos-holidays.com/api/lists/[LIST_UID]/subscribers \
  -H "X-API-KEY: [API_KEY]" \
  -d '{"EMAIL": "test@gmail.com", "FNAME": "Test"}'

# 2. Déclencher campagne (ou attendre autoresponder)

# 3. Vérifier réception Gmail
# 4. Vérifier headers email :
#    - From IP : [IP1-5]
#    - DKIM : PASS
#    - SPF : PASS
```

---

## 🔒 SÉCURITÉ

### VPS 1 (MailWizz)
```bash
# Firewall
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw enable

# Fail2ban
apt install -y fail2ban
systemctl enable fail2ban
```

### VPS 2 (PowerMTA)
```bash
# Firewall
ufw allow 2525/tcp  # Relay MailWizz
ufw allow 25/tcp    # SMTP sortant
ufw allow 22/tcp    # SSH admin
ufw enable

# Rate limiting (dans PowerMTA config)
<throttle-list default>
    max-messages 1000/h
    max-recipients 5000/h
</throttle-list>
```

---

## 📊 MONITORING

### Logs MailWizz
```bash
tail -f /var/www/html/mailwizz/apps/common/runtime/logs/*.log
```

### Logs PowerMTA
```bash
tail -f /var/log/pmta/acct.csv
tail -f /var/log/pmta/error.log
```

### Prometheus Metrics (Email-Engine)
```bash
curl http://localhost:8000/metrics
```

---

## 🚨 TROUBLESHOOTING

### Problème : MailWizz ne peut pas envoyer vers PowerMTA
```bash
# Sur VPS1
telnet [VPS2_IP] 2525
# Si timeout : vérifier firewall VPS2

# Sur VPS2
netstat -tulnp | grep 2525
# Doit afficher PowerMTA écoute :2525
```

### Problème : Emails n'arrivent pas
```bash
# Vérifier queue PowerMTA
/usr/sbin/pmta show queue

# Vérifier logs
tail -100 /var/log/pmta/acct.csv | grep FAILED

# Vérifier DNS
dig mail1.domain1.com
dig TXT mail._domainkey.domain1.com
```

---

## 📈 SCALABILITÉ

### Ajouter une IP (IP6, IP7, etc.)

**1. Configurer DNS** (A, SPF, DKIM, PTR)

**2. Générer clé DKIM**
```bash
ssh [VPS2_IP]
openssl genrsa -out /etc/pmta/dkim/domain6.pem 2048
openssl rsa -in /etc/pmta/dkim/domain6.pem -pubout
# Copier clé publique dans DNS
```

**3. Ajouter Virtual MTA**
```bash
# Éditer /etc/pmta/config
virtual-mta vmta-6 {
    smtp-source-host mail6.domain6.com [IP6]
    domain-key domain6.com,*,/etc/pmta/dkim/domain6.pem
}

# Reload
systemctl reload pmta
```

**4. Ajouter dans Email-Engine**
```bash
curl -X POST http://localhost:8000/api/v1/ips \
  -H "X-API-KEY: xxx" \
  -d '{
    "ip": "[IP6]",
    "domain": "mail6.domain6.com",
    "virtual_mta": "vmta-6"
  }'
```

---

## 📞 SUPPORT

**Documentation** : `/docs/`
**Issues** : GitHub Issues
**Monitoring** : http://monitoring.domain.com:3000

---

**Version** : 1.0.0
**Date** : 16 février 2026
