param(
  [Parameter(Mandatory = $true)]
  [string]$Config
)

$ErrorActionPreference = 'Stop'
$settings = & "$PSScriptRoot\aws-config.ps1" -Config $Config
$profile = $settings['AWS_PROFILE']
$region = $settings['AWS_REGION']
$stack = "brock-$($settings['STAGE'])"
$repo = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $repo 'frontend'
$dist = Join-Path $frontend 'dist'

aws sts get-caller-identity --profile $profile --region $region | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Renueva la sesión del perfil AWS antes de publicar.' }

$json = aws cloudformation describe-stacks --stack-name $stack --profile $profile --region $region --output json
if ($LASTEXITCODE -ne 0) { throw "No se pudo consultar $stack." }
$outputs = @{}
foreach ($output in ($json | ConvertFrom-Json).Stacks[0].Outputs) {
  $outputs[$output.OutputKey] = $output.OutputValue
}
foreach ($key in @('FrontendBucketName', 'DistributionId', 'FrontendUrl')) {
  if (-not $outputs.ContainsKey($key)) { throw "Falta output $key." }
}

& "$PSScriptRoot\export-frontend-config.ps1" -Config $Config
& npm.cmd --prefix $frontend run build
if ($LASTEXITCODE -ne 0) { throw 'Falló el build del frontend.' }
if (-not (Test-Path -LiteralPath $dist -PathType Container)) { throw 'No existe el build frontend.' }

$bucket = "s3://$($outputs['FrontendBucketName'])"
# Los chunks con hash se publican antes del HTML y se conservan para las pestañas antiguas.
aws s3 sync "$dist/assets/" "$bucket/assets/" --cache-control 'public,max-age=31536000,immutable' --profile $profile --region $region
if ($LASTEXITCODE -ne 0) { throw 'Falló la publicación de assets.' }
aws s3 sync "$dist/" "$bucket/" --exclude 'assets/*' --delete --cache-control 'no-cache' --profile $profile --region $region
if ($LASTEXITCODE -ne 0) { throw 'Falló la publicación del HTML/PWA.' }

$distribution = $outputs['DistributionId']
$invalidation = aws cloudfront create-invalidation --distribution-id $distribution --paths '/*' --profile $profile --query 'Invalidation.Id' --output text
if ($LASTEXITCODE -ne 0) { throw 'No se pudo invalidar CloudFront.' }
aws cloudfront wait invalidation-completed --distribution-id $distribution --id $invalidation --profile $profile
if ($LASTEXITCODE -ne 0) { throw "Revisa la invalidación $invalidation en CloudFront." }
Write-Output "Frontend publicado: $($outputs['FrontendUrl'])"
