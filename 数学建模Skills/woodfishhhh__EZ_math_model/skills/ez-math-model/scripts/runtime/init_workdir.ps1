[CmdletBinding()]
param(
  [string]$ProjectRoot = (Get-Location).Path,
  [string]$InputRoot,
  [string]$RuntimeRoot,
  [string]$OutputRoot,
  [string]$WorkdirRoot,
  [string]$Title = 'untitled',
  [string]$Language = 'zh',
  [string]$Contest = 'unknown',
  $Year,
  [string]$ProblemLetter
)

$ErrorActionPreference = 'Stop'

$projectPath = (Resolve-Path -LiteralPath $ProjectRoot).Path
$userInputDirName = -join ([char[]](0x7528,0x6237,0x8F93,0x5165))
$attachmentFolderName = -join ([char[]](0x9644,0x4EF6,0x6587,0x4EF6,0x5939))
if (-not $InputRoot) { $InputRoot = Join-Path $projectPath $userInputDirName }
if (-not $RuntimeRoot) { $RuntimeRoot = Join-Path $projectPath 'runtime' }
if (-not $OutputRoot) { $OutputRoot = Join-Path $projectPath 'output' }
if (-not $WorkdirRoot) { $WorkdirRoot = $RuntimeRoot }

$sourceOutput = Join-Path $OutputRoot 'source code'
$paperOutput = Join-Path $OutputRoot 'paper'
$attachmentsOutput = Join-Path $OutputRoot $attachmentFolderName

foreach ($dir in @($InputRoot, $RuntimeRoot, $OutputRoot, $sourceOutput, $paperOutput, $attachmentsOutput)) {
  if (-not (Test-Path $dir)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
  }
}

$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$seed = "$Title|$ts|$([guid]::NewGuid())"
$sha1 = [System.Security.Cryptography.SHA1]::Create()
$bytes = [System.Text.Encoding]::UTF8.GetBytes($seed)
$hash = ($sha1.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') }) -join ''
$shortHash = $hash.Substring(0,8)

$taskId = "$ts-$shortHash"
$taskDir = Join-Path $WorkdirRoot $taskId

foreach ($sub in @('attachments','src','results','figures','logs','tmp')) {
  New-Item -ItemType Directory -Force -Path (Join-Path $taskDir $sub) | Out-Null
}

# Render README from template
$tpl = Join-Path $PSScriptRoot '..\..\templates\readme_workdir.md'
if (-not (Test-Path $tpl)) { throw "template not found: $tpl" }
$readme = Get-Content -Raw -LiteralPath $tpl
$replacements = @{
  '{task_id}'         = $taskId
  '{created_at}'      = (Get-Date -Format 'o')
  '{title}'           = $Title
  '{contest}'         = $Contest
  '{year}'            = ($(if ($null -ne $Year) { "$Year" } else { 'null' }))
  '{problem_letter}'  = ($(if ($ProblemLetter) { $ProblemLetter } else { 'null' }))
  '{language}'        = $Language
  '{attachment_count}' = '0'
  '{stage_01_status}' = 'pending'
  '{stage_02_status}' = 'pending'
  '{stage_03_status}' = 'pending'
  '{stage_04_status}' = 'pending'
  '{stage_05_status}' = 'pending'
  '{stage_06_status}' = 'pending'
  '{match_level}'     = 'pending'
  '{thesis_dir}'      = 'pending'
  '{template_dir}'    = 'pending'
}
foreach ($kv in $replacements.GetEnumerator()) {
  $readme = $readme.Replace($kv.Key, $kv.Value)
}
Set-Content -LiteralPath (Join-Path $taskDir 'README.md') -Value $readme -Encoding UTF8

$projectPaths = [ordered]@{
  project_root       = $projectPath
  input_root         = (Resolve-Path -LiteralPath $InputRoot).Path
  runtime_root       = (Resolve-Path -LiteralPath $RuntimeRoot).Path
  task_dir           = (Resolve-Path -LiteralPath $taskDir).Path
  output_root        = (Resolve-Path -LiteralPath $OutputRoot).Path
  source_output      = (Resolve-Path -LiteralPath $sourceOutput).Path
  paper_output       = (Resolve-Path -LiteralPath $paperOutput).Path
  attachments_output = (Resolve-Path -LiteralPath $attachmentsOutput).Path
}
$projectPaths | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $taskDir 'project_paths.json') -Encoding UTF8

$runState = [ordered]@{
  task_id        = $taskId
  run_mode       = 'blocked'
  formal_result  = $false
  setup_status   = 'incomplete'
  required_inputs = @()
  missing_inputs = @()
  can_generate_paper = $false
  can_package = $false
  created_at = (Get-Date -Format 'o')
}
$runState | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskDir 'run_state.json') -Encoding UTF8

[pscustomobject]@{
  task_id            = $taskId
  task_dir           = (Resolve-Path -LiteralPath $taskDir).Path
  project_root       = $projectPath
  input_root         = (Resolve-Path -LiteralPath $InputRoot).Path
  runtime_root       = (Resolve-Path -LiteralPath $RuntimeRoot).Path
  output_root        = (Resolve-Path -LiteralPath $OutputRoot).Path
  source_output      = (Resolve-Path -LiteralPath $sourceOutput).Path
  paper_output       = (Resolve-Path -LiteralPath $paperOutput).Path
  attachments_output = (Resolve-Path -LiteralPath $attachmentsOutput).Path
} | ConvertTo-Json -Compress
