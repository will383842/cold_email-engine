# ================================================================
# BACKUP MANUEL - EMAIL-ENGINE
# ================================================================
# Description: Sauvegarde complète d'email-engine (PostgreSQL + configs + licences)
# Usage: .\scripts\backup-email-engine.ps1
# Durée: 2-5 minutes selon la taille de la base
# ================================================================

param(
    [string]$BackupDir = "backups",
    [switch]$IncludeVolumes = $false
)

$ErrorActionPreference = "Stop"
$Date = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupName = "email-engine-backup-$Date"
$BackupPath = Join-Path $BackupDir $BackupName

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "     BACKUP EMAIL-ENGINE - $Date" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Créer le dossier de backup
if (!(Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
    Write-Host "✅ Dossier $BackupDir créé" -ForegroundColor Green
}

New-Item -ItemType Directory -Path $BackupPath | Out-Null
Write-Host "📁 Backup: $BackupPath" -ForegroundColor Yellow
Write-Host ""

# ================================================================
# 1. VÉRIFIER QUE DOCKER EST DÉMARRÉ
# ================================================================
Write-Host "[1/6] Vérification Docker..." -ForegroundColor Cyan

try {
    docker ps | Out-Null
    Write-Host "✅ Docker est actif" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker n'est pas démarré ou inaccessible" -ForegroundColor Red
    exit 1
}

# ================================================================
# 2. BACKUP BASE DE DONNÉES POSTGRESQL
# ================================================================
Write-Host ""
Write-Host "[2/6] Backup PostgreSQL..." -ForegroundColor Cyan

$DbBackupFile = Join-Path $BackupPath "email_engine_db_$Date.sql.gz"

try {
    docker-compose exec -T postgres pg_dump -U email_engine email_engine | gzip > $DbBackupFile

    $DbSize = (Get-Item $DbBackupFile).Length / 1MB
    Write-Host "✅ Base PostgreSQL sauvegardée: $([math]::Round($DbSize, 2)) MB" -ForegroundColor Green
} catch {
    Write-Host "❌ Erreur backup PostgreSQL: $_" -ForegroundColor Red
    exit 1
}

# ================================================================
# 3. BACKUP CONFIGURATION .env
# ================================================================
Write-Host ""
Write-Host "[3/6] Backup configuration .env..." -ForegroundColor Cyan

if (Test-Path ".env") {
    Copy-Item ".env" (Join-Path $BackupPath "env-backup-$Date.txt")
    Write-Host "✅ Fichier .env sauvegardé" -ForegroundColor Green
} else {
    Write-Host "⚠️  Fichier .env introuvable" -ForegroundColor Yellow
}

# ================================================================
# 4. BACKUP LICENCE ET CONFIG PMTA
# ================================================================
Write-Host ""
Write-Host "[4/6] Backup PowerMTA (licence + config)..." -ForegroundColor Cyan

$PmtaBackupDir = Join-Path $BackupPath "powermta"
New-Item -ItemType Directory -Path $PmtaBackupDir | Out-Null

# Licence PMTA
if (Test-Path "powermta\license") {
    Copy-Item "powermta\license" (Join-Path $PmtaBackupDir "pmta-license-$Date")
    Write-Host "✅ Licence PMTA sauvegardée" -ForegroundColor Green
} else {
    Write-Host "⚠️  Licence PMTA introuvable dans powermta/license" -ForegroundColor Yellow
}

# Config PMTA
if (Test-Path "powermta\config") {
    Copy-Item "powermta\config" (Join-Path $PmtaBackupDir "pmta-config-$Date")
    Write-Host "✅ Config PMTA sauvegardée" -ForegroundColor Green
}

# DKIM keys
if (Test-Path "powermta\dkim") {
    Copy-Item "powermta\dkim" (Join-Path $PmtaBackupDir "dkim") -Recurse
    Write-Host "✅ Clés DKIM sauvegardées" -ForegroundColor Green
}

# ================================================================
# 5. BACKUP VOLUMES DOCKER (optionnel)
# ================================================================
Write-Host ""
Write-Host "[5/6] Backup volumes Docker..." -ForegroundColor Cyan

if ($IncludeVolumes) {
    $VolumesBackup = Join-Path $BackupPath "docker-volumes.tar.gz"

    try {
        docker run --rm `
            -v email-engine_postgres_data:/volume `
            -v ${PWD}:/backup `
            alpine tar czf "/backup/$VolumesBackup" -C /volume .

        Write-Host "✅ Volumes Docker sauvegardés" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Erreur backup volumes: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "⏭️  Volumes Docker ignorés (utiliser -IncludeVolumes pour les inclure)" -ForegroundColor Gray
}

# ================================================================
# 6. CRÉER UNE ARCHIVE COMPLÈTE
# ================================================================
Write-Host ""
Write-Host "[6/6] Création archive finale..." -ForegroundColor Cyan

$ArchivePath = "$BackupPath.tar.gz"

try {
    tar -czf $ArchivePath -C $BackupDir $BackupName

    $ArchiveSize = (Get-Item $ArchivePath).Length / 1MB
    Write-Host "✅ Archive créée: $([math]::Round($ArchiveSize, 2)) MB" -ForegroundColor Green

    # Supprimer le dossier temporaire
    Remove-Item $BackupPath -Recurse -Force

} catch {
    Write-Host "⚠️  Erreur création archive: $_" -ForegroundColor Yellow
}

# ================================================================
# RÉSUMÉ
# ================================================================
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "✅ BACKUP TERMINÉ AVEC SUCCÈS" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "📦 Archive: $ArchivePath" -ForegroundColor Yellow
Write-Host "📊 Taille: $([math]::Round($ArchiveSize, 2)) MB" -ForegroundColor Yellow
Write-Host ""

# Lister tous les backups disponibles
Write-Host "📁 Backups disponibles:" -ForegroundColor Cyan
Get-ChildItem $BackupDir -Filter "*.tar.gz" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 5 |
    ForEach-Object {
        $Size = $_.Length / 1MB
        Write-Host "   - $($_.Name) ($([math]::Round($Size, 2)) MB) - $($_.LastWriteTime)" -ForegroundColor Gray
    }

Write-Host ""
Write-Host "💡 Pour restaurer ce backup, consultez: GUIDE-RESTORATION.md" -ForegroundColor Cyan
Write-Host ""
