param(
  [Parameter(Mandatory = $true)]
  [string]$Config
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $Config -PathType Leaf)) {
  throw "No existe el archivo de configuración: $Config"
}

$values = @{}
foreach ($line in Get-Content -LiteralPath $Config) {
  $trimmed = $line.Trim()
  if (-not $trimmed -or $trimmed.StartsWith('#')) { continue }
  $parts = $trimmed -split '=', 2
  if ($parts.Count -ne 2) { throw "Línea inválida en configuración: $line" }
  $values[$parts[0].Trim()] = $parts[1].Trim()
}

foreach ($required in @('AWS_PROFILE', 'AWS_REGION', 'STAGE', 'BEDROCK_MODEL_ID', 'ALERT_EMAIL')) {
  if (-not $values.ContainsKey($required) -or [string]::IsNullOrWhiteSpace($values[$required])) {
    throw "Falta configurar $required en $Config"
  }
}
if ($values['STAGE'] -notin @('dev', 'prod')) { throw 'STAGE debe ser dev o prod' }
if ($values['AWS_REGION'] -notmatch '^[a-z0-9-]+$') { throw 'AWS_REGION no es válida' }
if ($values['ALERT_EMAIL'] -notmatch '^[^\s@]+@[^\s@]+\.[^\s@]+$') { throw 'ALERT_EMAIL no es válido' }

$values['CUPO_DIARIO'] = if ($values.ContainsKey('CUPO_DIARIO')) { $values['CUPO_DIARIO'] } else { '5' }
$values['MONTHLY_BUDGET_USD'] = if ($values.ContainsKey('MONTHLY_BUDGET_USD')) { $values['MONTHLY_BUDGET_USD'] } else { '10' }
if ([int]$values['CUPO_DIARIO'] -lt 1 -or [int]$values['CUPO_DIARIO'] -gt 100) { throw 'CUPO_DIARIO debe estar entre 1 y 100' }
if ([decimal]$values['MONTHLY_BUDGET_USD'] -lt 1) { throw 'MONTHLY_BUDGET_USD debe ser al menos 1' }

$values
