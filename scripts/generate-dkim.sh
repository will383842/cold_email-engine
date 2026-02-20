#!/bin/bash
# ============================================================
# Generate DKIM keys for all email domains
# Run once during setup, then when adding new domains
# ============================================================

set -e

DKIM_DIR="/etc/pmta/dkim"
mkdir -p "$DKIM_DIR"

DOMAINS=(
    "hub-travelers.com"
    "emilia-mullerd.com"
    "plane-liberty.com"
    "planevilain.com"
    # Ajouter ici les nouveaux domaines d'envoi configurés via la console admin
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
