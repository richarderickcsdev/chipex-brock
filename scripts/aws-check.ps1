param(
  [Parameter(Mandatory = $true)]
  [string]$Config
)

$ErrorActionPreference = 'Stop'
$settings = & "$PSScriptRoot\aws-config.ps1" -Config $Config
$profile = $settings['AWS_PROFILE']
$region = $settings['AWS_REGION']

aws sts get-caller-identity --profile $profile --region $region
if ($LASTEXITCODE -ne 0) { throw 'No se pudo validar el perfil AWS.' }
aws bedrock list-foundation-models --by-provider Anthropic --profile $profile --region $region | Out-Null
if ($LASTEXITCODE -ne 0) { throw "No se pudo consultar Bedrock en $region." }
Write-Output "Configuración AWS válida para $($settings['STAGE']) en $region con perfil $profile."
