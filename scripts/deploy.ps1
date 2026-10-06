param(
  [Parameter(Mandatory = $true)]
  [string]$Config
)

$ErrorActionPreference = 'Stop'
$settings = & "$PSScriptRoot\aws-config.ps1" -Config $Config
$profile = $settings['AWS_PROFILE']
$region = $settings['AWS_REGION']
$stage = $settings['STAGE']
$model = $settings['BEDROCK_MODEL_ID']
$email = $settings['ALERT_EMAIL']
$quota = $settings['CUPO_DIARIO']
$budget = $settings['MONTHLY_BUDGET_USD']

& "$PSScriptRoot\aws-check.ps1" -Config $Config
if ($LASTEXITCODE -ne 0) { throw 'Falló la validación de AWS.' }

sam build --config-env $stage
if ($LASTEXITCODE -ne 0) { throw 'sam build falló.' }
sam deploy --config-env $stage --region $region --profile $profile `
  --parameter-overrides "Stage=$stage" "BedrockModelId=$model" "AlertEmail=$email" `
  "CupoDiario=$quota" "MonthlyBudgetUsd=$budget"
if ($LASTEXITCODE -ne 0) { throw 'sam deploy falló.' }

Write-Output "Despliegue completado. Exporta los outputs con export-frontend-config.ps1."
