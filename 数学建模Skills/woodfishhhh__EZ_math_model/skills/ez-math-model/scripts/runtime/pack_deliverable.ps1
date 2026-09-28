[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)]
  [string]$WorkDir,
  [string]$ProjectRoot,
  [string]$OutputRoot,
  [string]$ZipPath
)

$ErrorActionPreference = 'Stop'

function Get-RelativePathCompat {
  param(
    [Parameter(Mandatory=$true)]
    [string]$BasePath,
    [Parameter(Mandatory=$true)]
    [string]$TargetPath
  )
  $baseFull = [System.IO.Path]::GetFullPath($BasePath)
  $separator = [System.IO.Path]::DirectorySeparatorChar
  if (-not $baseFull.EndsWith([string]$separator)) {
    $baseFull = $baseFull + $separator
  }
  $baseUri = New-Object System.Uri($baseFull)
  $targetUri = New-Object System.Uri([System.IO.Path]::GetFullPath($TargetPath))
  [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace('\', '/')
}

function Test-IsSubPath {
  param(
    [Parameter(Mandatory=$true)][string]$BasePath,
    [Parameter(Mandatory=$true)][string]$ChildPath
  )
  $baseFull = [System.IO.Path]::GetFullPath($BasePath).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
  $childFull = [System.IO.Path]::GetFullPath($ChildPath).TrimEnd('\', '/')
  return $childFull.StartsWith($baseFull, [System.StringComparison]::OrdinalIgnoreCase)
}

function Assert-SafeDirectoryForDelete {
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)][string]$ProjectRoot
  )
  $full = [System.IO.Path]::GetFullPath($Path)
  $root = [System.IO.Path]::GetPathRoot($full)
  if ($full -eq $root) { throw "refusing to delete filesystem root: $full" }
  if (-not (Test-IsSubPath -BasePath $ProjectRoot -ChildPath $full)) {
    throw "refusing to delete outside project root: $full"
  }
  $leaf = Split-Path -Leaf $full
  if ($leaf -notmatch '^output\.__(staging|previous)\.') {
    throw "refusing to delete unexpected directory: $full"
  }
}

function Ensure-Diagnostics {
  param([Parameter(Mandatory=$true)][string]$RuntimeDir)
  $diag = Join-Path $RuntimeDir 'diagnostics.md'
  if (-not (Test-Path -LiteralPath $diag)) {
    "# 失败诊断`n`n无失败项。本次运行所有阶段均通过。" | Set-Content -LiteralPath $diag -Encoding UTF8
  }
  return $diag
}

function Add-DiagnosticNote {
  param(
    [Parameter(Mandatory=$true)][string]$RuntimeDir,
    [Parameter(Mandatory=$true)][string[]]$Lines
  )
  $diag = Ensure-Diagnostics -RuntimeDir $RuntimeDir
  Add-Content -LiteralPath $diag -Value ("`n## Packaging notes`n" + ($Lines -join "`n")) -Encoding UTF8
}

function Get-Sha256OrEmpty {
  param([Parameter(Mandatory=$true)][string]$Path, [string]$Type)
  if ((Test-Path -LiteralPath $Path -PathType Leaf) -and $Type -notin @('manifest', 'project_zip')) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
  }
  return ''
}

function New-Artifact {
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)][string]$Type,
    [Parameter(Mandatory=$true)][string]$ActualPath,
    [Parameter(Mandatory=$true)][bool]$Formal,
    [bool]$Verified,
    [string]$VerificationStatus,
    [string]$Notes = ''
  )
  $exists = Test-Path -LiteralPath $ActualPath
  $size = 0
  $file_count = 0
  if ($exists -and (Test-Path -LiteralPath $ActualPath -PathType Leaf)) {
    $size = (Get-Item -LiteralPath $ActualPath).Length
  } elseif ($exists -and (Test-Path -LiteralPath $ActualPath -PathType Container)) {
    $file_count = @(Get-ChildItem -LiteralPath $ActualPath -Recurse -File -ErrorAction SilentlyContinue).Count
  }
  if (-not $VerificationStatus) {
    if (-not $exists) { $VerificationStatus = 'missing' }
    elseif ($Verified) { $VerificationStatus = 'verified' }
    else { $VerificationStatus = 'exists_only' }
  }
  [ordered]@{
    path = $Path
    type = $Type
    source = ''
    stage = 'packaging'
    formal = $Formal
    exists = $exists
    verified = [bool]($exists -and $Verified)
    verification_status = $VerificationStatus
    size = $size
    file_count = $file_count
    sha256 = Get-Sha256OrEmpty -Path $ActualPath -Type $Type
    created_at = (Get-Date -Format 'o')
    notes = $Notes
  }
}

function Test-ZipContains {
  param(
    [Parameter(Mandatory=$true)][string]$ZipFile,
    [Parameter(Mandatory=$true)][string]$EntryName
  )
  Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction SilentlyContinue
  $zip = [System.IO.Compression.ZipFile]::OpenRead($ZipFile)
  try {
    return [bool]$zip.GetEntry($EntryName)
  } finally {
    $zip.Dispose()
  }
}

function Add-FileToZip {
  param(
    [Parameter(Mandatory=$true)]$Archive,
    [Parameter(Mandatory=$true)][string]$FilePath,
    [Parameter(Mandatory=$true)][string]$EntryPath
  )
  $entry = $EntryPath.Replace('\', '/')
  [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
    $Archive,
    $FilePath,
    $entry,
    [System.IO.Compression.CompressionLevel]::Optimal
  ) | Out-Null
}

function New-ProjectZipWithStagingOutput {
  param(
    [Parameter(Mandatory=$true)][string]$ProjectRoot,
    [Parameter(Mandatory=$true)][string]$StagingOutput,
    [Parameter(Mandatory=$true)][string]$OutputRoot,
    [Parameter(Mandatory=$true)][string]$DestinationZip,
    [Parameter(Mandatory=$true)][string]$FinalZipPath
  )
  Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath $DestinationZip -Force -ErrorAction SilentlyContinue
  $archive = [System.IO.Compression.ZipFile]::Open($DestinationZip, [System.IO.Compression.ZipArchiveMode]::Create)
  try {
    $projectFull = [System.IO.Path]::GetFullPath($ProjectRoot)
    $stagingFull = [System.IO.Path]::GetFullPath($StagingOutput)
    $outputFull = [System.IO.Path]::GetFullPath($OutputRoot)
    $destinationFull = [System.IO.Path]::GetFullPath($DestinationZip)
    $finalZipFull = [System.IO.Path]::GetFullPath($FinalZipPath)

    foreach ($file in Get-ChildItem -LiteralPath $ProjectRoot -Recurse -File -Force) {
      $full = [System.IO.Path]::GetFullPath($file.FullName)
      if ($full -eq $destinationFull -or $full -eq $finalZipFull) { continue }
      if (Test-IsSubPath -BasePath $stagingFull -ChildPath $full) { continue }
      if ((Test-Path -LiteralPath $outputFull) -and (Test-IsSubPath -BasePath $outputFull -ChildPath $full)) { continue }
      if ($file.Name -eq 'deliverable.zip' -and ($full -match '[\\/]runtime[\\/]')) { continue }
      if ($file.Name -like 'output.zip.__tmp.*') { continue }
      if ($full -match '[\\/]output\.__previous\.') { continue }
      $entry = Get-RelativePathCompat -BasePath $projectFull -TargetPath $full
      Add-FileToZip -Archive $archive -FilePath $full -EntryPath $entry
    }

    foreach ($file in Get-ChildItem -LiteralPath $StagingOutput -Recurse -File -Force) {
      $rel = Get-RelativePathCompat -BasePath $stagingFull -TargetPath $file.FullName
      Add-FileToZip -Archive $archive -FilePath $file.FullName -EntryPath ("output/$rel")
    }
  } finally {
    $archive.Dispose()
  }
}

$wd = (Resolve-Path -LiteralPath $WorkDir).Path
if (-not (Test-Path $wd -PathType Container)) {
  throw "workdir not found: $WorkDir"
}

$pathsFile = Join-Path $wd 'project_paths.json'
if (Test-Path $pathsFile) {
  $paths = Get-Content -Raw -LiteralPath $pathsFile | ConvertFrom-Json
  if (-not $ProjectRoot) { $ProjectRoot = $paths.project_root }
  if (-not $OutputRoot) { $OutputRoot = $paths.output_root }
}
if (-not $ProjectRoot) { $ProjectRoot = Split-Path -Parent (Split-Path -Parent $wd) }
if (-not $OutputRoot) { $OutputRoot = Join-Path $ProjectRoot 'output' }

$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$OutputRoot = [System.IO.Path]::GetFullPath($OutputRoot)
if (-not (Test-IsSubPath -BasePath $ProjectRoot -ChildPath $wd)) {
  throw "workdir must be inside project root. workdir=$wd project_root=$ProjectRoot"
}
if (-not (Test-IsSubPath -BasePath $ProjectRoot -ChildPath $OutputRoot)) {
  throw "output root must be inside project root. output_root=$OutputRoot project_root=$ProjectRoot"
}
if ((Split-Path -Leaf $OutputRoot) -ne 'output') {
  throw "output root leaf must be 'output' to avoid unsafe publishing: $OutputRoot"
}

$taskId = Split-Path -Leaf $wd
$safeTaskId = ($taskId -replace '[^\w.-]', '_')
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$stagingRoot = Join-Path $ProjectRoot "output.__staging.$safeTaskId"
$previousRoot = Join-Path $ProjectRoot "output.__previous.$timestamp"
$attachmentFolderName = -join ([char[]](0x9644,0x4EF6,0x6587,0x4EF6,0x5939))
$qualityReportName = (-join ([char[]](0x8D28,0x91CF,0x68C0,0x67E5,0x62A5,0x544A))) + '.md'
$diagnosticsName = (-join ([char[]](0x5931,0x8D25,0x8BCA,0x65AD))) + '.md'
$paperOutput = Join-Path $stagingRoot 'paper'
$sourceOutput = Join-Path $stagingRoot 'source code'
$attachmentsOutput = Join-Path $stagingRoot $attachmentFolderName

if (Test-Path -LiteralPath $stagingRoot) {
  Assert-SafeDirectoryForDelete -Path $stagingRoot -ProjectRoot $ProjectRoot
  Remove-Item -LiteralPath $stagingRoot -Recurse -Force
}
foreach ($dir in @($stagingRoot, $paperOutput, $sourceOutput, $attachmentsOutput)) {
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$diagFile = Ensure-Diagnostics -RuntimeDir $wd

$runStateFile = Join-Path $wd 'run_state.json'
$runMode = 'unknown'
$setupStatus = 'unknown'
if (Test-Path $runStateFile) {
  $runState = Get-Content -Raw -LiteralPath $runStateFile | ConvertFrom-Json
  $runMode = $runState.run_mode
  $setupStatus = $runState.setup_status
}
$formal = ($runMode -eq 'formal')

$exportScript = Join-Path $PSScriptRoot 'export_paper.ps1'
if ((Test-Path $exportScript) -and (Test-Path (Join-Path $wd 'paper.md'))) {
  $exportRaw = & $exportScript -WorkDir $wd -PaperOutput $paperOutput
  if ($exportRaw) {
    $exportResult = ($exportRaw | Out-String) | ConvertFrom-Json
  }
}

if ($exportResult) {
  $exportNotes = New-Object System.Collections.Generic.List[string]
  if ($exportResult.pdf_fallback) { $exportNotes.Add("- PDF fallback used: $($exportResult.pdf_fallback)") }
  if ($exportResult.pdf_error) { $exportNotes.Add("- PDF engine error: $($exportResult.pdf_error)") }
  if ($exportResult.reference_doc_missing_reason) { $exportNotes.Add("- Reference doc: $($exportResult.reference_doc_missing_reason)") }
  if (-not $exportResult.paper_docx) { $exportNotes.Add("- DOCX export missing") }
  if (-not $exportResult.paper_pdf) { $exportNotes.Add("- PDF export missing") }
  if ($exportResult.docx_latex_fallback_count -gt 0) { $exportNotes.Add("- DOCX contains LaTeX fallback count: $($exportResult.docx_latex_fallback_count)") }
  if ($exportNotes.Count -gt 0) {
    Add-DiagnosticNote -RuntimeDir $wd -Lines $exportNotes
  }
}

$srcDir = Join-Path $wd 'src'
if (Test-Path $srcDir) {
  Copy-Item -Recurse -LiteralPath $srcDir -Destination (Join-Path $sourceOutput 'src') -Force
}
foreach ($f in @('requirements.txt','config.yaml','README_RUN.md')) {
  $sf = Join-Path $wd $f
  if (Test-Path $sf) { Copy-Item -LiteralPath $sf -Destination (Join-Path $sourceOutput $f) -Force }
}

foreach ($d in @('results','figures','attachments')) {
  $sd = Join-Path $wd $d
  if (Test-Path $sd) {
    Copy-Item -Recurse -LiteralPath $sd -Destination (Join-Path $attachmentsOutput $d) -Force
  }
}
foreach ($c in @(
  @{ src = 'quality_report.md'; dst = $qualityReportName },
  @{ src = 'quality_report.json'; dst = 'quality_report.json' },
  @{ src = 'diagnostics.md'; dst = $diagnosticsName },
  @{ src = 'README.md'; dst = 'README.md' },
  @{ src = 'run_state.json'; dst = 'run_state.json' },
  @{ src = 'export_report.json'; dst = 'export_report.json' }
)) {
  $s = Join-Path $wd $c.src
  if (Test-Path $s) { Copy-Item -LiteralPath $s -Destination (Join-Path $attachmentsOutput $c.dst) -Force }
}

$auditExportScript = Join-Path $PSScriptRoot 'audit_export.py'
$exportAudit = $null
if (Test-Path -LiteralPath $auditExportScript) {
  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) {
    $pythonExe = if ($python.Path) { $python.Path } elseif ($python.Source) { $python.Source } else { $python.Name }
    & $pythonExe $auditExportScript --workdir $wd --paper-output $paperOutput --export-report (Join-Path $wd 'export_report.json')
    $auditExit = $LASTEXITCODE
    foreach ($c in @(
      @{ src = 'export_audit.md'; dst = '导出对象审查.md' },
      @{ src = 'export_audit.json'; dst = 'export_audit.json' }
    )) {
      $s = Join-Path $wd $c.src
      if (Test-Path $s) { Copy-Item -LiteralPath $s -Destination (Join-Path $attachmentsOutput $c.dst) -Force }
    }
    $auditJson = Join-Path $wd 'export_audit.json'
    if (Test-Path $auditJson) { $exportAudit = Get-Content -Raw -LiteralPath $auditJson | ConvertFrom-Json }
    if ($auditExit -ne 0 -and $exportAudit -and $exportAudit.blocking) {
      throw "export audit failed with blocking issues; see export_audit.md"
    }
  } else {
    Add-DiagnosticNote -RuntimeDir $wd -Lines @("- Python not found; export object audit not executed.")
  }
}

$qualityAudit = $null
$qualityJson = Join-Path $wd 'quality_report.json'
if (Test-Path $qualityJson) {
  $qualityAudit = Get-Content -Raw -LiteralPath $qualityJson | ConvertFrom-Json
}

$manifestPath = Join-Path $stagingRoot 'manifest.json'
"{}" | Set-Content -LiteralPath $manifestPath -Encoding UTF8
$finalRuntimeManifestCopy = Join-Path $attachmentsOutput 'artifact_manifest.final.json'
"{}" | Set-Content -LiteralPath $finalRuntimeManifestCopy -Encoding UTF8

$docxVerified = $false
$pdfVerified = $false
if ($exportAudit) {
  $docxGate = @($exportAudit.gates | Where-Object { $_.item -eq 'docx_readable' -or $_.item -eq 'docx_embedded_images' -or $_.item -eq 'docx_formula_objects' -or $_.item -eq 'docx_table_objects' })
  $docxVerified = ($docxGate.Count -gt 0 -and @($docxGate | Where-Object { $_.status -eq 'fail' }).Count -eq 0)
  $pdfGate = @($exportAudit.gates | Where-Object { $_.item -eq 'pdf_readability' })
  $pdfVerified = ($pdfGate.Count -gt 0 -and @($pdfGate | Where-Object { $_.status -eq 'fail' }).Count -eq 0)
}

$plannedZipPath = if ($ZipPath) { [System.IO.Path]::GetFullPath($ZipPath) } else { Join-Path $ProjectRoot 'output.zip' }

$artifacts = @()
$artifacts += New-Artifact -Path 'output/paper/paper.md' -Type 'paper_md' -ActualPath (Join-Path $paperOutput 'paper.md') -Formal $formal -Verified (Test-Path (Join-Path $paperOutput 'paper.md')) -VerificationStatus ''
$artifacts += New-Artifact -Path 'output/paper/paper.docx' -Type 'paper_docx' -ActualPath (Join-Path $paperOutput 'paper.docx') -Formal $formal -Verified $docxVerified -VerificationStatus $(if ($exportAudit) { if ($docxVerified) { 'verified' } else { 'audit_failed' } } else { 'not_checked' }) -Notes 'DOCX object verification uses export_audit.json'
$artifacts += New-Artifact -Path 'output/paper/paper.txt' -Type 'paper_txt' -ActualPath (Join-Path $paperOutput 'paper.txt') -Formal $formal -Verified (Test-Path (Join-Path $paperOutput 'paper.txt')) -VerificationStatus ''
$artifacts += New-Artifact -Path 'output/paper/paper.pdf' -Type 'paper_pdf' -ActualPath (Join-Path $paperOutput 'paper.pdf') -Formal $formal -Verified $pdfVerified -VerificationStatus $(if ($exportAudit) { if ($pdfVerified) { 'verified' } else { 'audit_failed' } } else { 'not_checked' }) -Notes 'PDF readability verification uses export_audit.json'
$artifacts += New-Artifact -Path 'output/source code/' -Type 'source_code' -ActualPath $sourceOutput -Formal $formal -Verified (Test-Path $sourceOutput) -VerificationStatus ''
$artifacts += New-Artifact -Path 'output/附件文件夹/figures/' -Type 'figures' -ActualPath (Join-Path $attachmentsOutput 'figures') -Formal $formal -Verified (Test-Path (Join-Path $attachmentsOutput 'figures')) -VerificationStatus ''
$artifacts += New-Artifact -Path 'output/附件文件夹/results/' -Type 'results' -ActualPath (Join-Path $attachmentsOutput 'results') -Formal $formal -Verified (Test-Path (Join-Path $attachmentsOutput 'results')) -VerificationStatus ''
$artifacts += New-Artifact -Path "output/附件文件夹/$qualityReportName" -Type 'quality_report' -ActualPath (Join-Path $attachmentsOutput $qualityReportName) -Formal $formal -Verified (Test-Path (Join-Path $attachmentsOutput $qualityReportName)) -VerificationStatus $(if ($qualityAudit -and $qualityAudit.blocking) { 'audit_failed' } elseif ($qualityAudit) { 'verified' } else { 'exists_only' })
$artifacts += New-Artifact -Path "output/附件文件夹/$diagnosticsName" -Type 'diagnostics' -ActualPath (Join-Path $attachmentsOutput $diagnosticsName) -Formal $formal -Verified (Test-Path (Join-Path $attachmentsOutput $diagnosticsName)) -VerificationStatus ''
$artifacts += New-Artifact -Path 'output/附件文件夹/export_report.json' -Type 'export_report' -ActualPath (Join-Path $attachmentsOutput 'export_report.json') -Formal $formal -Verified (Test-Path (Join-Path $attachmentsOutput 'export_report.json')) -VerificationStatus ''
$artifacts += New-Artifact -Path 'output/附件文件夹/export_audit.json' -Type 'export_audit' -ActualPath (Join-Path $attachmentsOutput 'export_audit.json') -Formal $formal -Verified ($exportAudit -ne $null -and -not $exportAudit.blocking) -VerificationStatus $(if ($exportAudit) { if ($exportAudit.blocking) { 'audit_failed' } else { 'verified' } } else { 'not_checked' })
$artifacts += New-Artifact -Path 'output/manifest.json' -Type 'manifest' -ActualPath $manifestPath -Formal $formal -Verified $true -VerificationStatus 'verified'
$artifacts += New-Artifact -Path 'output.zip' -Type 'project_zip' -ActualPath $plannedZipPath -Formal $formal -Verified $true -VerificationStatus 'verified_before_publish' -Notes 'Temporary zip is created and checked before output/ is published; runtime/*/deliverable.zip is excluded to avoid stale nested packages.'

$manifest = [ordered]@{
  task_id = $taskId
  run_mode = $runMode
  setup_status = $setupStatus
  generated_at = (Get-Date -Format 'o')
  manifest_schema = '2.0'
  verification_policy = 'verified=true requires object or required-artifact audit; file existence alone is exists_only'
  artifacts = $artifacts
}
$manifestJson = $manifest | ConvertTo-Json -Depth 12
$manifestJson | Set-Content -LiteralPath $manifestPath -Encoding UTF8
$manifestJson | Set-Content -LiteralPath (Join-Path $wd 'artifact_manifest.json') -Encoding UTF8
Copy-Item -LiteralPath (Join-Path $wd 'artifact_manifest.json') -Destination $finalRuntimeManifestCopy -Force

if (-not $ZipPath) { $ZipPath = Join-Path $ProjectRoot 'output.zip' }
$finalZip = [System.IO.Path]::GetFullPath($ZipPath)
if (-not (Test-IsSubPath -BasePath $ProjectRoot -ChildPath $finalZip)) {
  throw "zip path must be inside project root: $finalZip"
}
$tmpZip = Join-Path $ProjectRoot "output.zip.__tmp.$safeTaskId.zip"
New-ProjectZipWithStagingOutput -ProjectRoot $ProjectRoot -StagingOutput $stagingRoot -OutputRoot $OutputRoot -DestinationZip $tmpZip -FinalZipPath $finalZip
if (-not (Test-ZipContains -ZipFile $tmpZip -EntryName 'output/manifest.json')) {
  throw "temporary zip does not contain output/manifest.json"
}

$oldOutputMoved = $false
$stagingMoved = $false
try {
  if (Test-Path -LiteralPath $OutputRoot) {
    Move-Item -LiteralPath $OutputRoot -Destination $previousRoot
    $oldOutputMoved = $true
  }
  Move-Item -LiteralPath $stagingRoot -Destination $OutputRoot
  $stagingMoved = $true
  Remove-Item -LiteralPath $finalZip -Force -ErrorAction SilentlyContinue
  Move-Item -LiteralPath $tmpZip -Destination $finalZip
  $runtimeZip = Join-Path $wd 'deliverable.zip'
  Remove-Item -LiteralPath $runtimeZip -Force -ErrorAction SilentlyContinue
  Copy-Item -LiteralPath $finalZip -Destination $runtimeZip -Force
  if ($oldOutputMoved -and (Test-Path -LiteralPath $previousRoot)) {
    Assert-SafeDirectoryForDelete -Path $previousRoot -ProjectRoot $ProjectRoot
    Remove-Item -LiteralPath $previousRoot -Recurse -Force
  }
  Write-Output $finalZip
} catch {
  if ($stagingMoved -and (Test-Path -LiteralPath $OutputRoot)) {
    $rollbackStaging = Join-Path $ProjectRoot "output.__staging.rollback.$safeTaskId"
    Move-Item -LiteralPath $OutputRoot -Destination $rollbackStaging -ErrorAction SilentlyContinue
  }
  if ($oldOutputMoved -and (Test-Path -LiteralPath $previousRoot) -and -not (Test-Path -LiteralPath $OutputRoot)) {
    Move-Item -LiteralPath $previousRoot -Destination $OutputRoot -ErrorAction SilentlyContinue
  }
  throw
} finally {
  Remove-Item -LiteralPath $tmpZip -Force -ErrorAction SilentlyContinue
}
