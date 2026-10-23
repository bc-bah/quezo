[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$destination = Join-Path $root '.env.docker.ca.pem'
$certificates = Get-ChildItem Cert:\LocalMachine\Root, Cert:\CurrentUser\Root |
    Sort-Object -Property Thumbprint -Unique
if (-not $certificates) {
    throw 'No trusted Windows root certificates were found.'
}

$pem = foreach ($certificate in $certificates) {
    '-----BEGIN CERTIFICATE-----'
    [Convert]::ToBase64String($certificate.RawData, [Base64FormattingOptions]::InsertLineBreaks)
    '-----END CERTIFICATE-----'
}
$pem | Set-Content -LiteralPath $destination -Encoding ascii
Write-Host 'Exported trusted public Windows roots to .env.docker.ca.pem. No private keys were exported.'
