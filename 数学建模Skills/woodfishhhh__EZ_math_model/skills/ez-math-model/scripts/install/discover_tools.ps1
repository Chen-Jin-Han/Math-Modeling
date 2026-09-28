[CmdletBinding()]
<#
.SYNOPSIS
  扫描外部工具配置状态。检查每个 EZMM_ env var 是否设置 + 命令行工具可用性。
  纯只读；不写任何标记，也不下载任何东西。
.NOTES
  与 references/external-tools-catalog.md 保持一致。新增工具时同步更新此处。
#>
param(
  [string]$Out
)

$ErrorActionPreference = 'Continue'

function Has-Cmd { param([string]$n) [bool](Get-Command $n -ErrorAction SilentlyContinue) }
function Has-Env { param([string]$n) -not [string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable($n)) -or -not [string]::IsNullOrEmpty((Get-Item env:$n -ErrorAction SilentlyContinue).Value) }

# Domain 1: PDF 解析
$pdf = [ordered]@{}
$pdf['mineru_cli'] = Has-Cmd 'mineru'
$pdf['mineru_token'] = Has-Env 'EZMM_MINERU_TOKEN'
$pdf['pdfplumber'] = $null  # 留给 Python 检测
$pdf['pdftoppm'] = Has-Cmd 'pdftoppm'

# Domain 2: 学术搜索
$scholar = [ordered]@{}
$scholar['openalex_email'] = Has-Env 'EZMM_OPENALEX_EMAIL'
$scholar['s2_api_key'] = Has-Env 'EZMM_S2_API_KEY'
$scholar['serpapi_key'] = Has-Env 'EZMM_SERPAPI_KEY'

# Domain 3: 数据集
$homeDir = if ($env:USERPROFILE) { $env:USERPROFILE } else { $HOME }
$kaggleJson = if ($homeDir) { Join-Path $homeDir '.kaggle\kaggle.json' } else { $null }
$dataset = [ordered]@{}
$dataset['kaggle_cli'] = Has-Cmd 'kaggle'
$dataset['kaggle_credentials'] = if ($kaggleJson) { Test-Path $kaggleJson } else { $false }
$dataset['hf_token'] = Has-Env 'EZMM_HF_TOKEN'

# Domain 4: 网页抓取
$webcrawl = [ordered]@{}
$webcrawl['firecrawl_key'] = Has-Env 'EZMM_FIRECRAWL_KEY'
$webcrawl['tavily_key'] = Has-Env 'EZMM_TAVILY_KEY'
$webcrawl['exa_key'] = Has-Env 'EZMM_EXA_KEY'
$webcrawl['serpapi_key'] = Has-Env 'EZMM_SERPAPI_KEY'  # 复用，与 scholar 同一个

# Python 库可用性（pdfplumber / kaggle / requests / datasets）
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }
$libs = @{}
if ($python) {
  foreach ($lib in @('pdfplumber','kaggle','requests','datasets','huggingface_hub')) {
    & $python.Source -c "import importlib,sys; importlib.import_module('$lib'); sys.exit(0)" *> $null
    $libs[$lib] = ($LASTEXITCODE -eq 0)
  }
}
$pdf['pdfplumber'] = [bool]$libs['pdfplumber']

# Domain 5: 继承的辅助 skills（探测安装位置）
$inheritedNames = @(
  'humanizer','simplify','scientific-slides','systematic-debugging',
  'brainstorming','external-context','dispatching-parallel-agents',
  'subagent-driven-development','verification-before-completion'
)
$skillRoots = @()
if ($homeDir) {
  $skillRoots += (Join-Path $homeDir '.claude\skills')
  $skillRoots += (Join-Path $homeDir '.codex\skills')
}
$inherited = [ordered]@{}
foreach ($n in $inheritedNames) {
  $hit = $null
  foreach ($r in $skillRoots) {
    if (-not $r) { continue }
    $p = Join-Path $r $n
    if (Test-Path $p) { $hit = $p; break }
  }
  $inherited[$n] = $hit
}

# Domain 6: agent mode 当前决策（如有）
$toolsDir = Resolve-Path (Join-Path $PSScriptRoot '..\..\external\tools') -ErrorAction SilentlyContinue
$agentMode = $null
if ($toolsDir) {
  foreach ($m in @('single','multi','hybrid')) {
    if (Test-Path (Join-Path $toolsDir "agent_mode.$m")) { $agentMode = $m; break }
  }
}

$setupState = [ordered]@{
  exists          = $false
  setup_completed = $false
  schema_version  = $null
  path            = $null
}
if ($toolsDir) {
  $setupPath = Join-Path $toolsDir 'setup_state.json'
  $setupState['path'] = $setupPath
  if (Test-Path $setupPath) {
    $setupState['exists'] = $true
    try {
      $parsed = Get-Content -LiteralPath $setupPath -Raw | ConvertFrom-Json
      $setupState['schema_version'] = $parsed.schema_version
      $setupState['setup_completed'] = ($parsed.schema_version -eq '1.0' -and $parsed.setup_completed -eq $true)
    } catch {
      $setupState['setup_completed'] = $false
    }
  }
}

# 总览
$result = [ordered]@{
  pdf              = $pdf
  scholar          = $scholar
  dataset          = $dataset
  webcrawl         = $webcrawl
  inherited_skills = $inherited
  agent_mode       = $agentMode
  setup_state      = $setupState
  python_libraries = $libs
  catalog_ref      = 'references/external-tools-catalog.md'
  agent_mode_ref   = 'references/agent-mode.md'
  checked_at       = (Get-Date -Format 'o')
}

$json = $result | ConvertTo-Json -Depth 4
if ($Out) {
  $dir = Split-Path -Parent $Out
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  Set-Content -LiteralPath $Out -Value $json -Encoding UTF8
} else {
  Write-Output $json
}
exit 0
