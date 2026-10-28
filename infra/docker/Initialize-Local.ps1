[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$destination = Join-Path $root '.env.docker'
if (Test-Path -LiteralPath $destination) {
    throw '.env.docker already exists. Preserve its credentials for the existing Docker volumes.'
}

function New-LocalSecret {
    $bytes = New-Object byte[] 32
    $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $random.GetBytes($bytes)
    }
    finally {
        $random.Dispose()
    }
    return [BitConverter]::ToString($bytes).Replace('-', '').ToLowerInvariant()
}

$bootstrap = New-LocalSecret
$migration = New-LocalSecret
$runtime = New-LocalSecret
$web = New-LocalSecret
$admin = New-LocalSecret
$client = New-LocalSecret
$accountAdminClient = New-LocalSecret
$synthetic = New-LocalSecret

@"
# Generated local-only credentials. Never commit or share this file.
POSTGRES_DB=quezo
POSTGRES_USER=quezo
POSTGRES_PASSWORD=$bootstrap
QUEZO_MIGRATION_PASSWORD=$migration
QUEZO_RUNTIME_PASSWORD=$runtime
QUEZO_WEB_PASSWORD=$web
QUEZO_MIGRATION_URL=postgresql://quezo_migrator:${migration}@127.0.0.1:5432/quezo
QUEZO_DATABASE_URL=postgresql://quezo_runtime:${runtime}@127.0.0.1:5432/quezo
QUEZO_WEB_DATABASE_URL=postgresql://quezo_web:${web}@127.0.0.1:5432/quezo
KEYCLOAK_ADMIN=quezo-admin
KEYCLOAK_ADMIN_PASSWORD=$admin
QUEZO_OIDC_CLIENT_SECRET=$client
QUEZO_ACCOUNT_ADMIN_CLIENT_ID=quezo-account-admin
QUEZO_ACCOUNT_ADMIN_CLIENT_SECRET=$accountAdminClient
QUEZO_SYNTHETIC_PASSWORD=$synthetic
"@ | Set-Content -LiteralPath $destination -Encoding ascii

Write-Host 'Created .env.docker with distinct random local credentials. No containers have been started.'
