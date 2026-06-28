# PostgreSQL restore script for HRMS (Windows).
param(
    [Parameter(Mandatory = $true)]
    [string]$DumpFile,
    [string]$EnvFile = "$PSScriptRoot\..\backend\.env"
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

$env:PGPASSWORD = $dbPassword
pg_restore -h $dbHost -p $dbPort -U $dbUser -d $dbName --no-owner --clean --if-exists $DumpFile
Write-Host "Restore completed into $dbName"
