# ================================================================
# BACKUP AUTOMATIQUE HEBDOMADAIRE - EMAIL-ENGINE
# ================================================================
# Description: Script pour Task Scheduler Windows (backup hebdomadaire)
# Fréquence: Chaque dimanche à 2h00 du matin
# Rotation: Garde les 4 derniers backups (1 mois)
# ================================================================

param(
    [string]$LogFile = "logs\backup-hebdo.log"
)

$ErrorActionPreference = "Continue"
$Date = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupDir = "backups-auto"

# ================================================================
# FONCTION DE LOGGING
# ================================================================
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")

    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"

    # Créer le dossier logs si nécessaire
    $LogDir = Split-Path $LogFile -Parent
    if ($LogDir -and !(Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    }

    # Écrire dans le fichier log
    Add-Content -Path $LogFile -Value $LogMessage

    # Afficher dans la console
    switch ($Level) {
        "ERROR" { Write-Host $LogMessage -ForegroundColor Red }
        "SUCCESS" { Write-Host $LogMessage -ForegroundColor Green }
        "WARNING" { Write-Host $LogMessage -ForegroundColor Yellow }
        default { Write-Host $LogMessage -ForegroundColor White }
    }
}

# ================================================================
# DÉBUT DU BACKUP
# ================================================================
Write-Log "================================================================"
Write-Log "DÉBUT BACKUP AUTOMATIQUE - EMAIL-ENGINE"
Write-Log "================================================================"

# Créer le dossier de backup
if (!(Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
    Write-Log "Dossier $BackupDir créé" "SUCCESS"
}

$BackupName = "email-engine-auto-$Date"
$BackupPath = Join-Path $BackupDir $BackupName
New-Item -ItemType Directory -Path $BackupPath | Out-Null

# ================================================================
# 1. VÉRIFIER DOCKER
# ================================================================
Write-Log "Vérification Docker..."

try {
    docker ps | Out-Null
    Write-Log "Docker est actif" "SUCCESS"
} catch {
    Write-Log "Docker inaccessible - abandon du backup" "ERROR"
    exit 1
}

# ================================================================
# 2. BACKUP POSTGRESQL
# ================================================================
Write-Log "Backup PostgreSQL en cours..."

$DbBackupFile = Join-Path $BackupPath "email_engine_db.sql.gz"

try {
    docker-compose exec -T postgres pg_dump -U email_engine email_engine | gzip > $DbBackupFile

    if (Test-Path $DbBackupFile) {
        $DbSize = (Get-Item $DbBackupFile).Length / 1MB
        Write-Log "PostgreSQL sauvegardé: $([math]::Round($DbSize, 2)) MB" "SUCCESS"
    } else {
        Write-Log "Fichier backup PostgreSQL introuvable" "ERROR"
    }
} catch {
    Write-Log "Erreur backup PostgreSQL: $_" "ERROR"
}

# ================================================================
# 3. BACKUP CONFIGURATION
# ================================================================
Write-Log "Backup configuration..."

if (Test-Path ".env") {
    Copy-Item ".env" (Join-Path $BackupPath "env-backup.txt")
    Write-Log "Fichier .env sauvegardé" "SUCCESS"
} else {
    Write-Log "Fichier .env introuvable" "WARNING"
}

# ================================================================
# 4. BACKUP POWERMTA
# ================================================================
Write-Log "Backup PowerMTA..."

$PmtaBackupDir = Join-Path $BackupPath "powermta"
New-Item -ItemType Directory -Path $PmtaBackupDir | Out-Null

if (Test-Path "powermta\license") {
    Copy-Item "powermta\license" (Join-Path $PmtaBackupDir "license")
    Write-Log "Licence PMTA sauvegardée" "SUCCESS"
}

if (Test-Path "powermta\config") {
    Copy-Item "powermta\config" (Join-Path $PmtaBackupDir "config")
    Write-Log "Config PMTA sauvegardée" "SUCCESS"
}

if (Test-Path "powermta\dkim") {
    Copy-Item "powermta\dkim" (Join-Path $PmtaBackupDir "dkim") -Recurse
    Write-Log "Clés DKIM sauvegardées" "SUCCESS"
}

# ================================================================
# 5. CRÉER ARCHIVE
# ================================================================
Write-Log "Création archive finale..."

$ArchivePath = "$BackupPath.tar.gz"

try {
    tar -czf $ArchivePath -C $BackupDir $BackupName

    if (Test-Path $ArchivePath) {
        $ArchiveSize = (Get-Item $ArchivePath).Length / 1MB
        Write-Log "Archive créée: $([math]::Round($ArchiveSize, 2)) MB" "SUCCESS"

        # Supprimer le dossier temporaire
        Remove-Item $BackupPath -Recurse -Force
    }
} catch {
    Write-Log "Erreur création archive: $_" "ERROR"
}

# ================================================================
# 6. ROTATION DES BACKUPS (garder 4 derniers)
# ================================================================
Write-Log "Rotation des backups..."

$AllBackups = Get-ChildItem $BackupDir -Filter "email-engine-auto-*.tar.gz" |
              Sort-Object LastWriteTime -Descending

$BackupsToKeep = 4
$BackupsToDelete = $AllBackups | Select-Object -Skip $BackupsToKeep

if ($BackupsToDelete) {
    foreach ($Backup in $BackupsToDelete) {
        Remove-Item $Backup.FullName -Force
        Write-Log "Backup supprimé (rotation): $($Backup.Name)" "INFO"
    }
}

$RemainingCount = ($AllBackups | Select-Object -First $BackupsToKeep).Count
Write-Log "Backups conservés: $RemainingCount / $BackupsToKeep" "SUCCESS"

# ================================================================
# RÉSUMÉ FINAL
# ================================================================
Write-Log "================================================================"
Write-Log "BACKUP AUTOMATIQUE TERMINÉ AVEC SUCCÈS"
Write-Log "================================================================"
Write-Log "Archive: $ArchivePath"
Write-Log "Taille: $([math]::Round($ArchiveSize, 2)) MB"
Write-Log "Backups disponibles: $RemainingCount"
Write-Log ""

# Envoyer une notification (optionnel)
# TODO: Intégrer notification Telegram/Email si besoin
