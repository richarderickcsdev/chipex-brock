param(
  [Parameter(Mandatory = $true)]
  [string]$Config,
  [switch]$PreviewOnly
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
$priceIn = $settings['BEDROCK_INPUT_PRICE_PER_MILLION']
$priceOut = $settings['BEDROCK_OUTPUT_PRICE_PER_MILLION']

if ([string]::IsNullOrWhiteSpace($email)) {
  $budgetName = if ($settings.ContainsKey('ALERT_EMAIL_BUDGET_NAME')) {
    $settings['ALERT_EMAIL_BUDGET_NAME']
  } else { 'Presupuesto chipa' }
  $notificationJson = aws budgets describe-subscribers-for-notification `
    --account-id (aws sts get-caller-identity --profile $profile --query Account --output text) `
    --budget-name $budgetName `
    --notification NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=50 `
    --profile $profile --region $region --output json
  if ($LASTEXITCODE -ne 0) { throw 'No se pudo obtener el correo de alertas del presupuesto existente.' }
  $notification = $notificationJson | ConvertFrom-Json
  $email = ($notification.Subscribers | Where-Object { $_.SubscriptionType -eq 'EMAIL' } |
    Select-Object -First 1).Address
  if ([string]::IsNullOrWhiteSpace($email)) {
    throw 'Configura ALERT_EMAIL en dev.env o añade un correo al presupuesto existente.'
  }
}

& "$PSScriptRoot\aws-check.ps1" -Config $Config
if ($LASTEXITCODE -ne 0) { throw 'Falló la validación de AWS.' }

sam build --config-env $stage
if ($LASTEXITCODE -ne 0) { throw 'sam build falló.' }
$deployArgs = @(
  'deploy', '--config-env', $stage, '--region', $region, '--profile', $profile,
  '--parameter-overrides', "Stage=$stage", "BedrockModelId=$model", "AlertEmail=$email",
  "CupoDiario=$quota", "MonthlyBudgetUsd=$budget",
  "BedrockInputPricePerMillion=$priceIn", "BedrockOutputPricePerMillion=$priceOut",
  'CreateStackBudget=false'
)
if ($PreviewOnly) {
  $deployArgs += @('--no-execute-changeset', '--no-confirm-changeset')
  Write-Output 'Modo previsualización: SAM creará un change set, pero no lo ejecutará.'
}
& sam @deployArgs
if ($LASTEXITCODE -ne 0) { throw 'sam deploy falló.' }

if ($PreviewOnly) {
  Write-Output "Change set preparado para $stage. Inspecciónalo antes de volver a ejecutar deploy.ps1 sin -PreviewOnly."
} else {
  Write-Output "Despliegue completado. Exporta los outputs con export-frontend-config.ps1."
}
