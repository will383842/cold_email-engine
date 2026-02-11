# DNS Templates - Email Engine

Pour chaque domaine email, creer ces enregistrements DNS.

## trans.mail-ulixai.com (Transactionnel)

```
Type: A
Name: trans.mail-ulixai.com
Value: IP1_ADDRESS

Type: MX
Name: trans.mail-ulixai.com
Value: trans.mail-ulixai.com (priority 10)

Type: TXT (SPF)
Name: trans.mail-ulixai.com
Value: v=spf1 ip4:IP1_ADDRESS -all

Type: TXT (DKIM)
Name: default._domainkey.trans.mail-ulixai.com
Value: v=DKIM1; k=rsa; p=DKIM_PUBLIC_KEY_HERE

Type: TXT (DMARC)
Name: _dmarc.trans.mail-ulixai.com
Value: v=DMARC1; p=reject; rua=mailto:dmarc@ulixai.com

PTR (chez Hetzner): IP1_ADDRESS -> trans.mail-ulixai.com
```

## news.sos-expat.com (Marketing)

```
Type: A
Name: news.sos-expat.com
Value: IP2_ADDRESS

Type: MX
Name: news.sos-expat.com
Value: news.sos-expat.com (priority 10)

Type: TXT (SPF)
Name: news.sos-expat.com
Value: v=spf1 ip4:IP2_ADDRESS -all

Type: TXT (DKIM)
Name: default._domainkey.news.sos-expat.com
Value: v=DKIM1; k=rsa; p=DKIM_PUBLIC_KEY_HERE

Type: TXT (DMARC)
Name: _dmarc.news.sos-expat.com
Value: v=DMARC1; p=quarantine; rua=mailto:dmarc@sos-expat.com

PTR (chez Hetzner): IP2_ADDRESS -> news.sos-expat.com
```

## cold-outreach-1.com (Cold - IP3)

```
Type: A
Name: @
Value: IP3_ADDRESS

Type: MX
Name: @
Value: cold-outreach-1.com (priority 10)

Type: TXT (SPF)
Name: @
Value: v=spf1 ip4:IP3_ADDRESS -all

Type: TXT (DKIM)
Name: default._domainkey
Value: v=DKIM1; k=rsa; p=DKIM_PUBLIC_KEY_HERE

Type: TXT (DMARC)
Name: _dmarc
Value: v=DMARC1; p=none; rua=mailto:dmarc@cold-outreach-1.com

PTR (chez Hetzner): IP3_ADDRESS -> cold-outreach-1.com
```

## cold-outreach-2.com (Standby - IP4)

Meme structure que cold-outreach-1.com avec IP4_ADDRESS.

## cold-outreach-3.com (Standby - IP5)

Meme structure que cold-outreach-1.com avec IP5_ADDRESS.

---

## Verification DNS

Apres configuration, verifier avec :

```bash
# SPF
dig TXT cold-outreach-1.com

# DKIM
dig TXT default._domainkey.cold-outreach-1.com

# DMARC
dig TXT _dmarc.cold-outreach-1.com

# PTR
host IP3_ADDRESS

# MX
dig MX cold-outreach-1.com
```

Attendre 24-48h pour la propagation complete.
