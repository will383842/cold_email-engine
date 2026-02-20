# 🏗️ Architecture Production Email-Engine

**Date** : 16 février 2026
**Type** : Multi-serveurs (MailWizz + PowerMTA séparés)

---

## 📍 INFRASTRUCTURE

### VPS 1 : MailWizz
```
Domaine : sos-holidays.com
IP : [À définir]
Services :
  - MailWizz (PHP 8.1 + Nginx)
  - MySQL 8.0
  - Certbot SSL

Rôle :
  - Interface web campagnes
  - Gestion templates (106 templates)
  - Gestion listes/segments
  - Autoresponders (77 campagnes)
  - Tracking opens/clicks
  - API REST (pour Email-Engine)
```

### VPS 2 : PowerMTA
```
Domaines (5 actuellement, extensible) :
  - mail1.domain1.com
  - mail2.domain2.com
  - mail3.domain3.com
  - mail4.domain4.com
  - mail5.domain5.com

IPs (5 actuellement, extensible 100+) :
  - IP1
  - IP2
  - IP3
  - IP4
  - IP5

Services :
  - PowerMTA 5.0+
  - DKIM signing (5 domaines)
  - Virtual MTAs (1 par domaine)

Rôle :
  - Envoi physique emails
  - Rotation IPs
  - Queue management
  - Bounce handling
```

### VPS 3 : Email-Engine API (optionnel)
```
Services :
  - FastAPI (API REST)
  - PostgreSQL 15 (IPs, warmup, monitoring)
  - Redis 7 (cache)
  - Celery (workers)
  - Prometheus + Grafana

Rôle :
  - Orchestration générale
  - Gestion 5 IPs (extensible 100+)
  - Warmup automatique
  - Monitoring
  - Blacklist checks
  - DNS validation
  - Configuration PowerMTA
```

---

## 🔗 COMMUNICATION

```
┌────────────────┐
│ Email-Engine   │
│ (VPS 3)        │
└───────┬────────┘
        │
        ├─────► API HTTP ────► ┌────────────────┐
        │                       │ MailWizz       │
        │                       │ (VPS 1)        │
        │                       │ sos-holidays   │
        │                       └────────┬───────┘
        │                                │
        │                                │ SMTP :2525
        │                                ↓
        │                       ┌────────────────┐
        │                       │ PowerMTA       │
        └─────► Config SSH ───►│ (VPS 2)        │
                                │ 5 IPs/domaines │
                                └────────┬───────┘
                                         │
                                         │ SMTP :25
                                         ↓
                                    Internet
```

---

## 📊 CONFIGURATION ACTUELLE

### Phase 1 (Actuelle) : 5 IPs + 5 Domaines

```ini
# PowerMTA Config (5 Virtual MTAs)

virtual-mta vmta-domain1 {
    smtp-source-host mail1.domain1.com IP1
    domain-key domain1.com,*,/etc/pmta/dkim/domain1.pem
}

virtual-mta vmta-domain2 {
    smtp-source-host mail2.domain2.com IP2
    domain-key domain2.com,*,/etc/pmta/dkim/domain2.pem
}

virtual-mta vmta-domain3 {
    smtp-source-host mail3.domain3.com IP3
    domain-key domain3.com,*,/etc/pmta/dkim/domain3.pem
}

virtual-mta vmta-domain4 {
    smtp-source-host mail4.domain4.com IP4
    domain-key domain4.com,*,/etc/pmta/dkim/domain4.pem
}

virtual-mta vmta-domain5 {
    smtp-source-host mail5.domain5.com IP5
    domain-key domain5.com,*,/etc/pmta/dkim/domain5.pem
}
```

### Phase 2 (Future) : 100+ IPs + Domaines

**Extensible facilement** : Ajouter IPs dans PostgreSQL → Email-Engine génère config automatiquement

---

## 🚀 DÉPLOIEMENT

### VPS 1 : MailWizz (sos-holidays.com)
```bash
# 1. Installer stack LAMP
apt update && apt install -y apache2 mysql-server php8.1 php8.1-{cli,mysql,mbstring,xml,curl,zip,gd,intl}

# 2. Extraire MailWizz
cd /var/www/html
tar -xzf mailwizz-prod-20260216.tar.gz
chown -R www-data:www-data .

# 3. Importer base MySQL
gunzip -c mailapp-prod-20260216.sql.gz | mysql -u root mailwizz

# 4. SSL
certbot --apache -d sos-holidays.com

# 5. Configurer Delivery Server
# Dans MailWizz UI : Server SMTP → VPS2:2525
```

### VPS 2 : PowerMTA
```bash
# 1. Installer PowerMTA
rpm -ivh pmta-5.0-*.rpm

# 2. Copier config
cp pmta-config-20260216 /etc/pmta/config

# 3. Copier licence
cp pmta-license-20260216 /etc/pmta/license

# 4. Générer clés DKIM (5 domaines)
for domain in domain1 domain2 domain3 domain4 domain5; do
  openssl genrsa -out /etc/pmta/dkim/$domain.pem 2048
done

# 5. Démarrer
systemctl start pmta
```

### VPS 3 : Email-Engine (optionnel)
```bash
# 1. Cloner repo
git clone https://github.com/[user]/email-engine.git
cd email-engine

# 2. Config .env
cp .env.example .env
nano .env
# MAILWIZZ_URL=https://sos-holidays.com/api
# PMTA_SSH_HOST=vps2.ip.address
# IPS_COUNT=5

# 3. Démarrer
docker-compose up -d
```

---

## 📈 SCALABILITÉ

### Ajouter une IP (Phase 2)
```bash
# 1. Ajouter IP dans Email-Engine
curl -X POST http://email-engine:8000/api/v1/ips \
  -H "X-API-KEY: xxx" \
  -d '{"ip": "NEW_IP", "domain": "mail6.domain6.com"}'

# 2. Email-Engine génère automatiquement :
#    - Config PowerMTA (nouveau virtual-mta)
#    - Clé DKIM
#    - Warmup plan 6 semaines

# 3. Deploy sur VPS2
ssh vps2 "systemctl reload pmta"
```

---

## 🔐 SÉCURITÉ

### DNS Records (à configurer pour chaque domaine)

```dns
# SPF
domain1.com.  TXT  "v=spf1 ip4:IP1 ~all"

# DKIM
mail._domainkey.domain1.com.  TXT  "v=DKIM1; k=rsa; p=[PUBLIC_KEY]"

# DMARC
_dmarc.domain1.com.  TXT  "v=DMARC1; p=none; rua=mailto:dmarc@domain1.com"

# PTR (reverse DNS)
IP1  PTR  mail1.domain1.com.
```

---

## 📊 MONITORING

### Prometheus Metrics
```
# Email-Engine expose :
http://email-engine:8000/metrics

# Métriques :
- email_engine_ips_total{status="active"} 5
- email_engine_warmup_quota{ip="IP1"} 5000
- email_engine_blacklist_status{ip="IP1",dnsbl="spamhaus"} 0
```

### Grafana Dashboard
- URL : http://email-engine:3000
- Dashboards :
  - IPs Status
  - Warmup Progress
  - Blacklist Checks
  - Sending Volume

---

## ✅ CHECKLIST DÉPLOIEMENT

### VPS 1 (MailWizz)
- [ ] Installer LAMP
- [ ] Extraire MailWizz
- [ ] Importer MySQL
- [ ] Configurer SSL
- [ ] Tester API MailWizz
- [ ] Configurer Delivery Server (vers VPS2)

### VPS 2 (PowerMTA)
- [ ] Installer PowerMTA
- [ ] Copier config (5 Virtual MTAs)
- [ ] Copier licence
- [ ] Générer 5 clés DKIM
- [ ] Configurer DNS (5 domaines : SPF/DKIM/DMARC/PTR)
- [ ] Tester envoi SMTP

### VPS 3 (Email-Engine)
- [ ] Cloner repo
- [ ] Configurer .env
- [ ] Démarrer docker-compose
- [ ] Ajouter 5 IPs dans PostgreSQL
- [ ] Activer warmup plans
- [ ] Configurer monitoring

### Tests E2E
- [ ] Email-Engine → MailWizz API (ajouter contact)
- [ ] MailWizz → PowerMTA SMTP (envoyer email)
- [ ] PowerMTA → Internet (réception Gmail)
- [ ] Tracking opens/clicks
- [ ] Bounce handling

---

## 📞 CONTACT

**Support** : [email]
**Documentation** : /docs/
**Monitoring** : http://monitoring.domain.com:3000

---

**Document créé le** : 16 février 2026
**Version** : 1.0.0
**Auteur** : Claude Code
