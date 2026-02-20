# DNS Templates - Email Engine

Pour chaque domaine email, creer ces enregistrements DNS.

## hub-travelers.com (VPS2 — IP1)

```
Type: A
Name: mail.hub-travelers.com
Value: IP_VPS2_1

Type: MX
Name: mail.hub-travelers.com
Value: mail.hub-travelers.com (priority 10)

Type: TXT (SPF)
Name: hub-travelers.com
Value: v=spf1 ip4:IP_VPS2_1 -all

Type: TXT (DKIM)
Name: default._domainkey.hub-travelers.com
Value: v=DKIM1; k=rsa; p=DKIM_PUBLIC_KEY_HERE

Type: TXT (DMARC)
Name: _dmarc.hub-travelers.com
Value: v=DMARC1; p=quarantine; rua=mailto:dmarc@hub-travelers.com

PTR (chez Hetzner/Contabo): IP_VPS2_1 -> mail.hub-travelers.com
```

## emilia-mullerd.com (VPS2 — IP2)

```
Type: A
Name: mail.emilia-mullerd.com
Value: IP_VPS2_2

Type: MX
Name: mail.emilia-mullerd.com
Value: mail.emilia-mullerd.com (priority 10)

Type: TXT (SPF)
Name: emilia-mullerd.com
Value: v=spf1 ip4:IP_VPS2_2 -all

Type: TXT (DKIM)
Name: default._domainkey.emilia-mullerd.com
Value: v=DKIM1; k=rsa; p=DKIM_PUBLIC_KEY_HERE

Type: TXT (DMARC)
Name: _dmarc.emilia-mullerd.com
Value: v=DMARC1; p=quarantine; rua=mailto:dmarc@emilia-mullerd.com

PTR (chez Hetzner/Contabo): IP_VPS2_2 -> mail.emilia-mullerd.com
```

## plane-liberty.com (VPS3 — IP1)

```
Type: A
Name: mail.plane-liberty.com
Value: IP_VPS3_1

Type: MX
Name: mail.plane-liberty.com
Value: mail.plane-liberty.com (priority 10)

Type: TXT (SPF)
Name: plane-liberty.com
Value: v=spf1 ip4:IP_VPS3_1 -all

Type: TXT (DKIM)
Name: default._domainkey.plane-liberty.com
Value: v=DKIM1; k=rsa; p=DKIM_PUBLIC_KEY_HERE

Type: TXT (DMARC)
Name: _dmarc.plane-liberty.com
Value: v=DMARC1; p=quarantine; rua=mailto:dmarc@plane-liberty.com

PTR (chez Hetzner/Contabo): IP_VPS3_1 -> mail.plane-liberty.com
```

## planevilain.com (VPS3 — IP2)

```
Type: A
Name: mail.planevilain.com
Value: IP_VPS3_2

Type: MX
Name: mail.planevilain.com
Value: mail.planevilain.com (priority 10)

Type: TXT (SPF)
Name: planevilain.com
Value: v=spf1 ip4:IP_VPS3_2 -all

Type: TXT (DKIM)
Name: default._domainkey.planevilain.com
Value: v=DKIM1; k=rsa; p=DKIM_PUBLIC_KEY_HERE

Type: TXT (DMARC)
Name: _dmarc.planevilain.com
Value: v=DMARC1; p=none; rua=mailto:dmarc@planevilain.com

PTR (chez Hetzner/Contabo): IP_VPS3_2 -> mail.planevilain.com
```

---

## Template générique pour nouveaux domaines (VPS4/5/6)

Meme structure que ci-dessus avec les IPs du VPS concerné.

---

## Verification DNS

Apres configuration, verifier avec :

```bash
# SPF
dig TXT hub-travelers.com

# DKIM
dig TXT default._domainkey.hub-travelers.com

# DMARC
dig TXT _dmarc.hub-travelers.com

# PTR
host IP_VPS2_1

# MX
dig MX hub-travelers.com
```

Attendre 24-48h pour la propagation complete.
