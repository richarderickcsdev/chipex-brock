param(
  [Parameter(Mandatory = $true)]
  [string]$Config,
  [switch]$Force
)

$ErrorActionPreference = 'Stop'
$settings = & "$PSScriptRoot\aws-config.ps1" -Config $Config
$profile = $settings['AWS_PROFILE']
$region = $settings['AWS_REGION']
$stage = $settings['STAGE']
$stack = "brock-$stage"

if (-not $Force) {
  $confirm = Read-Host "Esto elimina $stack, usuarios, datos y recursos. Escribe DELETE para continuar"
  if ($confirm -cne 'DELETE') { throw 'Eliminación cancelada.' }
}

$bucket = aws cloudformation describe-stacks --stack-name $stack --profile $profile --region $region `
  --query "Stacks[0].Outputs[?OutputKey=='FrontendBucketName'].OutputValue" --output text
if ($LASTEXITCODE -ne 0) { throw "No se pudo leer $stack." }
if ($bucket -and $bucket -ne 'None') {
  aws s3 rm "s3://$bucket" --recursive --profile $profile --region $region
  if ($LASTEXITCODE -ne 0) { throw 'No se pudo vaciar el bucket frontend.' }
}
sam delete --stack-name $stack --profile $profile --region $region --no-prompts
if ($LASTEXITCODE -ne 0) { throw 'sam delete falló.' }
