[CmdletBinding()]
param(
  [string]$Out
)

$ErrorActionPreference = 'Continue'

function Try-Cmd {
  param([string]$Name)
  $c = Get-Command $Name -ErrorAction SilentlyContinue
  if ($c) { $c.Source } else { $null }
}

$python = Try-Cmd python
if (-not $python) { $python = Try-Cmd python3 }
$pythonVersion = if ($python) { (& $python --version 2>&1) -replace 'Python\s+','' } else { $null }

$git = Try-Cmd git
$pandoc = Try-Cmd pandoc

$libs = @('numpy','pandas','matplotlib','seaborn','scipy','scikit-learn','statsmodels','xgboost','lightgbm','networkx')
$missing = @()
$present = @()
if ($python) {
  foreach ($lib in $libs) {
    & $python -c "import importlib,sys; importlib.import_module('$($lib -replace '-','_')'); sys.exit(0)" *> $null
    if ($LASTEXITCODE -eq 0) { $present += $lib } else { $missing += $lib }
  }
}

# Font detection (Windows + cross-platform best-effort)
$fontsAvail = @()
$candidates = @('SimHei','Microsoft YaHei','Noto Sans CJK SC','Noto Sans SC','Heiti SC','PingFang SC','Source Han Sans CN','WenQuanYi Zen Hei')
$registry = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'
if (Test-Path $registry) {
  $names = (Get-ItemProperty -Path $registry).PSObject.Properties.Name
  foreach ($cand in $candidates) {
    if ($names | Where-Object { $_ -match [regex]::Escape($cand) }) { $fontsAvail += $cand }
  }
}

$zhanwen = Resolve-Path (Join-Path $PSScriptRoot '..\..\external\zhanwen-mathmodel') -ErrorAction SilentlyContinue
$zhanwenStatus = 'absent'
if ($zhanwen) {
  if (Test-Path (Join-Path $zhanwen '.skip')) { $zhanwenStatus = 'skip' }
  elseif (Test-Path (Join-Path $zhanwen '.complete')) { $zhanwenStatus = 'complete' }
  elseif (Test-Path (Join-Path $zhanwen '.failed')) { $zhanwenStatus = 'failed' }
}

$skillRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$toolsDir = Join-Path $skillRoot 'external\tools'
$setupStatePath = Join-Path $toolsDir 'setup_state.json'
$setupCompleted = $false
if (Test-Path $setupStatePath) {
  try {
    $setupState = Get-Content -LiteralPath $setupStatePath -Raw | ConvertFrom-Json
    $setupCompleted = ($setupState.schema_version -eq '1.0' -and $setupState.setup_completed -eq $true)
  } catch {
    $setupCompleted = $false
  }
}

$result = [ordered]@{
  python                = $python
  python_version        = $pythonVersion
  python_min_required   = '3.10'
  git_available         = [bool]$git
  pandoc_available      = [bool]$pandoc
  libraries_present     = $present
  libraries_missing     = $missing
  fonts_available       = $fontsAvail
  zhanwen_status        = $zhanwenStatus
  setup_completed       = $setupCompleted
  setup_state_path      = $setupStatePath
  platform              = "$($PSVersionTable.OS) | $($PSVersionTable.Platform)"
  checked_at            = (Get-Date -Format 'o')
}

$json = ($result | ConvertTo-Json -Depth 4)
if ($Out) {
  $dir = Split-Path -Parent $Out
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  Set-Content -LiteralPath $Out -Value $json -Encoding UTF8
} else {
  Write-Output $json
}
exit 0
