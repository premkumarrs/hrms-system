# PostgreSQL backup script for HRMS (Windows).
param(
    [string]$EnvFile = "$PSScriptRoot\..\backend\.env",
    [string]$BackupDir = "$PSScriptRoot\..\backups"
)

function Read-DotEnv($path) {
    $vars = @{}
    if (Test-Path $path) {
        Get-Content $path | ForEach-Object {
            if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
            $pair = $_ -split '=', 2
            $vars[$pair[0].Trim()] = $pair[1].Trim()
        }
    }
    return $vars
}

$env = Read-DotEnv $EnvFile
$dbHost = if ($env['DB_HOST']) { $env['DB_HOST'] } else { 'localhost' }
$dbPort = if ($env['DB_PORT']) { $env['DB_PORT'] } else { '5432' }
$dbUser = if ($env['DB_USER']) { $env['DB_USER'] } else { 'postgres' }
$dbName = if ($env['DB_NAME']) { $env['DB_NAME'] } else { 'hrms_db' }
$dbPassword = $env['DB_PASSWORD']

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$outfile = Join-Path $BackupDir "hrms_${dbName}_${stamp}.dump"

$env:PGPASSWORD = $dbPassword
pg_dump -h $dbHost -p $dbPort -U $dbUser -d $dbName -Fc -f $outfile
Write-Host "Backup written to $outfile"
