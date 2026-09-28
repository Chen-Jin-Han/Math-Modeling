# Requires -Version 5.1
<#
.SYNOPSIS
  Fetch the zhanwen/MathModel reference repo (sparse) into external/zhanwen-mathmodel/.
.NOTES
  - 失败时写入 .failed 标记而不是抛异常；上层 pipeline 会改走内置兜底。
  - 已有 .complete 标记则直接跳过。
  - .skip 标记永远不会被本脚本覆盖（用户主动写入的，靠 SKILL 流程维护）。
#>
[CmdletBinding()]
param(
  [string]$Repo = 'https://github.com/zhanwen/MathModel.git',
  [string]$Dest = (Join-Path $PSScriptRoot '..\..\external\zhanwen-mathmodel'),
  [string[]]$SparsePaths = @(
    '国赛论文/',
    '国赛试题/',
    '美赛论文/',
    '2024年数模悉知&论文模版/',
    '2025年数模悉知&论文模版/',
    '2024年最终获奖名单/',
    '数学建模Latex模版/',
    'README.md'
  ),
  [switch]$Force
)

$ErrorActionPreference = 'Stop'

function Write-Marker {
  param([string]$Dir, [string]$Name, [string]$Body = '')
  $path = Join-Path $Dir $Name
  $body = if ($Body) { $Body } else { (Get-Date -Format 'o') }
  Set-Content -Path $path -Value $body -Encoding UTF8 -NoNewline
}

function Remove-Marker {
  param([string]$Dir, [string]$Name)
  $path = Join-Path $Dir $Name
  if (Test-Path $path) { Remove-Item -Force $path }
}

$Dest = (Resolve-Path -LiteralPath $Dest -ErrorAction SilentlyContinue) ?? $Dest
if (-not (Test-Path $Dest)) {
  New-Item -ItemType Directory -Force -Path $Dest | Out-Null
}

if (Test-Path (Join-Path $Dest '.skip')) {
  Write-Host '[fetch_zhanwen] .skip marker present; user opted out permanently. Aborting.'
  exit 0
}

if ((Test-Path (Join-Path $Dest '.complete')) -and (-not $Force)) {
  Write-Host '[fetch_zhanwen] .complete marker present; sparse subset already fetched. Use -Force to refresh.'
  exit 0
}

# git available?
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
  Write-Warning '[fetch_zhanwen] git not found on PATH.'
  Write-Marker -Dir $Dest -Name '.failed' -Body "git not found at $(Get-Date -Format 'o')"
  exit 1
}

# Existing partial repo? clean it (but keep .gitkeep / README.md / .skip)
$keep = @('.gitkeep', 'README.md', '.skip')
Get-ChildItem -LiteralPath $Dest -Force | Where-Object { $keep -notcontains $_.Name } | ForEach-Object {
  if ($_.PSIsContainer) {
    Remove-Item -Recurse -Force -LiteralPath $_.FullName
  } else {
    Remove-Item -Force -LiteralPath $_.FullName
  }
}

# Move keep-files aside, clone, restore
$stash = New-Item -ItemType Directory -Force -Path (Join-Path $env:TEMP ("ezmm-stash-" + [guid]::NewGuid().ToString('N').Substring(0,8)))
foreach ($k in $keep) {
  $src = Join-Path $Dest $k
  if (Test-Path $src) { Move-Item -LiteralPath $src -Destination $stash -Force }
}

try {
  # git wants an empty directory, so step into it
  Push-Location $Dest
  Write-Host "[fetch_zhanwen] cloning $Repo (sparse, depth 1) ..."
  & git clone --depth 1 --filter=blob:none --sparse $Repo . 2>&1 | Tee-Object -Variable cloneLog | Out-Host
  if ($LASTEXITCODE -ne 0) {
    throw "git clone failed (exit=$LASTEXITCODE). Last lines:`n$($cloneLog | Select-Object -Last 5 | Out-String)"
  }

  Write-Host '[fetch_zhanwen] applying sparse-checkout subset ...'
  & git sparse-checkout init --no-cone 2>&1 | Out-Host
  $patternFile = Join-Path (Join-Path $Dest '.git') 'info\sparse-checkout'
  Set-Content -Path $patternFile -Value $SparsePaths -Encoding UTF8
  & git sparse-checkout reapply 2>&1 | Out-Host
  if ($LASTEXITCODE -ne 0) {
    throw "git sparse-checkout reapply failed (exit=$LASTEXITCODE)."
  }

  # Sanity: at least one expected dir present
  $hit = $false
  foreach ($p in $SparsePaths) {
    $clean = $p.TrimEnd('/')
    if (Test-Path (Join-Path $Dest $clean)) { $hit = $true; break }
  }
  if (-not $hit) {
    throw 'sparse-checkout completed but none of the expected paths exist; upstream layout may have changed.'
  }

  Remove-Marker -Dir $Dest -Name '.failed'
  Write-Marker -Dir $Dest -Name '.complete' -Body ("fetched_at={0}`nrepo={1}" -f (Get-Date -Format 'o'), $Repo)
  Write-Host '[fetch_zhanwen] done.'
}
catch {
  Write-Warning "[fetch_zhanwen] $_"
  Write-Marker -Dir $Dest -Name '.failed' -Body ("error_at={0}`nmessage={1}" -f (Get-Date -Format 'o'), $_)
  $code = 1
}
finally {
  Pop-Location
  # restore keep-files
  Get-ChildItem -LiteralPath $stash -Force -ErrorAction SilentlyContinue | ForEach-Object {
    Move-Item -LiteralPath $_.FullName -Destination $Dest -Force
  }
  Remove-Item -Recurse -Force -LiteralPath $stash -ErrorAction SilentlyContinue
}

exit ($code ?? 0)
