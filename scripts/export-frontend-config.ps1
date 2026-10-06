param(
  [Parameter(Mandatory = $true)]
  [string]$Config
)

$ErrorActionPreference = 'Stop'
$settings = & "$PSScriptRoot\aws-config.ps1" -Config $Config
$profile = $settings['AWS_PROFILE']
$region = $settings['AWS_REGION']
$stage = $settings['STAGE']
$stack = "brock-$stage"
$parent = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $parent 'frontend'
if (-not (Test-Path -LiteralPath $frontend -PathType Container)) { throw 'No existe frontend/' }

$json = aws cloudformation describe-stacks --stack-name $stack --profile $profile --region $region | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "No se pudo leer la pila $stack." }
$outputs = @{}
foreach ($output in $json.Stacks[0].Outputs) { $outputs[$output.OutputKey] = $output.OutputValue }
foreach ($required in @('ApiUrl', 'Region', 'UserPoolId', 'UserPoolClientId')) {
  if (-not $outputs.ContainsKey($required)) { throw "Falta output $required en $stack." }
}

$content = @(
  "VITE_API_URL=$($outputs['ApiUrl'])"
  "VITE_AWS_REGION=$($outputs['Region'])"
  "VITE_COGNITO_USER_POOL_ID=$($outputs['UserPoolId'])"
  "VITE_COGNITO_CLIENT_ID=$($outputs['UserPoolClientId'])"
)
$destination = Join-Path $frontend '.env.local'
Set-Content -LiteralPath $destination -Value $content -Encoding UTF8
Write-Output "Configuración frontend escrita en $destination"
