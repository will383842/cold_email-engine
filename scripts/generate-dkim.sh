#!/bin/bash
# ============================================================
# Generate DKIM keys for all email domains
# Run once during setup, then when adding new domains
# ============================================================

set -e

DKIM_DIR="/etc/pmta/dkim"
mkdir -p "$DKIM_DIR"

DOMAINS=(
    "trans.mail-ulixai.com"
    "news.sos-expat.com"
    "cold-outreach-1.com"
    "cold-outreach-2.com"
    "cold-outreach-3.com"
)

echo "=== Generating DKIM keys ==="

for domain in "${DOMAINS[@]}"; do
    keyfile="$DKIM_DIR/${domain//./-}.pem"

    if [ -f "$keyfile" ]; then
        echo "SKIP: $domain (key already exists)"
        continue
    fi

    # Generate 2048-bit RSA key
    openssl genrsa -out "$keyfile" 2048 2>/dev/null
    chown pmta:pmta "$keyfile" 2>/dev/null || true
    chmod 600 "$keyfile"

    # Extract public key for DNS
    pubkey=$(openssl rsa -in "$keyfile" -pubout 2>/dev/null | grep -v "^-" | tr -d '\n')

    echo ""
    echo "OK: $domain"
    echo "   Key: $keyfile"
    echo "   DNS TXT record to create:"
    echo "   Name:  default._domainkey.$domain"
    echo "   Value: v=DKIM1; k=rsa; p=$pubkey"
    echo ""
done

echo "=== Done. Add the DNS TXT records above, then restart PowerMTA ==="
