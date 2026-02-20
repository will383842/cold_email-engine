# 🔐 Instructions - Installation des Licences

## 📍 Fichiers à modifier

### 1. Clés API MailWizz
**Fichier** : `.env` (racine du projet)

Modifiez ces lignes :
```env
# API MailWizz générale (lignes 55-56)
MAILWIZZ_API_PUBLIC_KEY=votre_cle_publique_ici
MAILWIZZ_API_PRIVATE_KEY=votre_cle_privee_ici

# Tenant Client 1 (ligne 70)
MAILWIZZ_CLIENT1_API_KEY=votre_cle_api_client1

# Tenant Client 2 (ligne 75)
MAILWIZZ_CLIENT2_API_KEY=votre_cle_api_client2
```

### 2. Licence PowerMTA
**Emplacement** : `powermta/license`

Copiez votre fichier de licence PMTA :
```powershell
# Depuis Windows PowerShell
Copy-Item "chemin\vers\votre\pmta-license" "powermta\license"
```

Ou manuellement :
- Ouvrez le dossier `powermta/`
- Collez votre fichier de licence
- Renommez-le en `license` (sans extension)

---

## 🔍 Comment obtenir vos clés MailWizz API

1. Connectez-vous à votre panel MailWizz
2. Allez dans **Settings** → **API Keys**
3. Créez une nouvelle clé API si nécessaire
4. Copiez la **Public Key** et **Private Key**

---

## ✅ Vérification

Après avoir ajouté vos licences :

```bash
# Démarrer email-engine
docker-compose up -d

# Vérifier que l'API démarre correctement
curl http://localhost:8000/health

# Vérifier les logs
docker-compose logs api
```

Si vous voyez des erreurs liées à MailWizz ou PMTA, vérifiez que :
- Les clés API sont correctes (pas d'espaces avant/après)
- Le fichier de licence PMTA existe bien dans `powermta/license`
- Les URLs MailWizz sont correctes (https://mail.client1-domain.com/api)

---

**Créé le** : 2026-02-16
