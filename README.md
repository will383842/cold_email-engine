# Email Engine

Systeme d'envoi email massif professionnel.
PowerMTA + MailWizz + Rotation IP + Monitoring.

## Architecture

```
VDS Contabo S (5 IPs dediees)
├── PowerMTA (envoi SMTP)
└── Config: /etc/pmta/config

VPS Contabo M
├── MailWizz (dashboard + API)
├── MySQL (MailWizz DB)
└── Nginx + SSL
```

## Structure

```
email-engine/
├── powermta/           # Config PowerMTA
│   ├── config          # Config principale
│   └── dkim/           # Cles DKIM
├── mailwizz/           # Notes installation MailWizz
├── scripts/            # Scripts operationnels
├── monitoring/         # Config Grafana + alertes
├── dns/                # Templates DNS
└── backups/            # Scripts backup
```

## Deploiement

Voir `DEPLOY.md` pour le guide etape par etape.
