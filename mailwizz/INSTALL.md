# Installation MailWizz - Guide

## Pre-requis (VPS)

```bash
apt update && apt upgrade -y
apt install -y apache2 mysql-server php8.1 php8.1-{cli,mysql,mbstring,xml,curl,zip,gd,intl}
```

## Installation

```bash
# Telecharger MailWizz (depuis votre compte)
cd /var/www/html
wget https://www.mailwizz.com/downloads/mailwizz-latest.zip
unzip mailwizz-latest.zip
chown -R www-data:www-data /var/www/html/

# SSL
apt install -y certbot python3-certbot-apache
certbot --apache -d mail.sos-expat.com
```

## Configuration MySQL

```sql
CREATE DATABASE mailwizz;
CREATE USER 'mailwizz'@'localhost' IDENTIFIED BY 'STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON mailwizz.* TO 'mailwizz'@'localhost';
FLUSH PRIVILEGES;
```

## Post-installation

1. Acceder https://mail.sos-expat.com/install
2. Suivre wizard d'installation
3. Configurer Delivery Servers (voir ci-dessous)

## Delivery Servers a creer

### Server 1: Transactionnel
- Name: SMTP Trans (IP1)
- Hostname: VDS_IP_ADDRESS
- Port: 587
- Username: mailwizz
- Password: (meme que dans PowerMTA config)
- Additional headers: X-Virtual-MTA: pool-trans
- Daily quota: 20 (warm-up start)

### Server 2: Marketing
- Name: SMTP Marketing (IP2)
- Hostname: VDS_IP_ADDRESS
- Port: 587
- Username: mailwizz
- Password: (meme)
- Additional headers: X-Virtual-MTA: pool-marketing
- Daily quota: 50 (warm-up start)

### Server 3: Cold
- Name: SMTP Cold (IP3)
- Hostname: VDS_IP_ADDRESS
- Port: 587
- Username: mailwizz
- Password: (meme)
- Additional headers: X-Virtual-MTA: pool-cold
- Daily quota: 100 (warm-up start)

## Listes a creer

### Pour SOS-Expat:
1. Avocats Internationaux
2. Assureurs Expatries
3. Notaires Internationaux
4. Medecins Francophones
5. Contacts Divers

### Pour Ulixai:
1. Blogueurs Voyage
2. Influenceurs Reseaux Sociaux
3. Admins Groupes Facebook
4. YouTubeurs Voyage
5. Contacts Divers

## API Keys

Backend > Settings > API keys:
- Creer cle pour SOS-Expat (note: MAILWIZZ_SOS_EXPAT_API_KEY)
- Creer cle pour Ulixai (note: MAILWIZZ_ULIXAI_API_KEY)
