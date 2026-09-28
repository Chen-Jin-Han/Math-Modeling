[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)]
  [string]$WorkDir,
  [string]$PaperOutput
)

$ErrorActionPreference = 'Stop'

function ConvertTo-PdfLiteral {
  param([string]$Text)
  $builder = New-Object System.Text.StringBuilder
  foreach ($ch in $Text.ToCharArray()) {
    $code = [int][char]$ch
    if ($ch -eq '\') {
      [void]$builder.Append('\\')
    } elseif ($ch -eq '(') {
      [void]$builder.Append('\(')
    } elseif ($ch -eq ')') {
      [void]$builder.Append('\)')
    } elseif ($code -lt 32 -or $code -gt 126) {
      [void]$builder.Append('?')
    } else {
      [void]$builder.Append($ch)
    }
  }
  $builder.ToString()
}

function New-SimplePdf {
  param(
    [Parameter(Mandatory=$true)]
    [string]$TextPath,
    [Parameter(Mandatory=$true)]
    [string]$OutputPath
  )

  $rawLines = Get-Content -LiteralPath $TextPath -Encoding UTF8 -ErrorAction Stop
  if (-not $rawLines) { $rawLines = @('') }

  $wrapped = New-Object System.Collections.Generic.List[string]
  foreach ($line in $rawLines) {
    $current = [string]$line
    if ($current.Length -eq 0) {
      $wrapped.Add('')
      continue
    }
    while ($current.Length -gt 92) {
      $wrapped.Add($current.Substring(0, 92))
      $current = $current.Substring(92)
    }
    $wrapped.Add($current)
  }

  $linesPerPage = 48
  $pageCount = [Math]::Max(1, [int][Math]::Ceiling($wrapped.Count / $linesPerPage))
  $fontId = 3 + ($pageCount * 2)
  $objects = @{}

  $objects[1] = '<< /Type /Catalog /Pages 2 0 R >>'
  $kids = New-Object System.Collections.Generic.List[string]

  for ($pageIndex = 0; $pageIndex -lt $pageCount; $pageIndex++) {
    $pageId = 3 + ($pageIndex * 2)
    $contentId = $pageId + 1
    $kids.Add("$pageId 0 R")

    $content = New-Object System.Text.StringBuilder
    [void]$content.AppendLine('BT')
    [void]$content.AppendLine('/F1 10 Tf')
    [void]$content.AppendLine('50 790 Td')
    [void]$content.AppendLine('13 TL')

    $start = $pageIndex * $linesPerPage
    $end = [Math]::Min($start + $linesPerPage - 1, $wrapped.Count - 1)
    for ($i = $start; $i -le $end; $i++) {
      $literal = ConvertTo-PdfLiteral $wrapped[$i]
      [void]$content.AppendLine("($literal) Tj")
      [void]$content.AppendLine('T*')
    }

    [void]$content.AppendLine('ET')
    $contentText = $content.ToString()
    $contentLength = [System.Text.Encoding]::ASCII.GetByteCount($contentText)
    $objects[$pageId] = "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 $fontId 0 R >> >> /Contents $contentId 0 R >>"
    $objects[$contentId] = "<< /Length $contentLength >>`nstream`n$contentText`nendstream"
  }

  $objects[2] = "<< /Type /Pages /Kids [$($kids -join ' ')] /Count $pageCount >>"
  $objects[$fontId] = '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>'

  $pdf = New-Object System.Text.StringBuilder
  [void]$pdf.Append("%PDF-1.4`n")
  $offsets = @{}
  for ($id = 1; $id -le $fontId; $id++) {
    $offsets[$id] = [System.Text.Encoding]::ASCII.GetByteCount($pdf.ToString())
    [void]$pdf.Append("$id 0 obj`n$($objects[$id])`nendobj`n")
  }
  $xrefOffset = [System.Text.Encoding]::ASCII.GetByteCount($pdf.ToString())
  [void]$pdf.Append("xref`n0 $($fontId + 1)`n")
  [void]$pdf.Append("0000000000 65535 f `n")
  for ($id = 1; $id -le $fontId; $id++) {
    [void]$pdf.Append(('{0:0000000000} 00000 n ' -f $offsets[$id]) + "`n")
  }
  [void]$pdf.Append("trailer`n<< /Size $($fontId + 1) /Root 1 0 R >>`nstartxref`n$xrefOffset`n%%EOF`n")

  [System.IO.File]::WriteAllBytes($OutputPath, [System.Text.Encoding]::ASCII.GetBytes($pdf.ToString()))
}

function Get-MarkdownMetrics {
  param([Parameter(Mandatory=$true)][string]$MarkdownPath)
  $text = Get-Content -Raw -LiteralPath $MarkdownPath -Encoding UTF8
  $imageMatches = [regex]::Matches($text, '!\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
  $formulaBlocks = [regex]::Matches($text, '(?ms)^\s*\$\$\s*\n.*?\n\s*\$\$\s*$')
  $lines = $text -split "`r?`n"
  $tableCount = 0
  for ($i = 0; $i -lt ($lines.Count - 1); $i++) {
    if (($lines[$i] -match '\|') -and ($lines[$i + 1] -match '^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$')) {
      $tableCount += 1
    }
  }
  [ordered]@{
    markdown_image_count = $imageMatches.Count
    markdown_formula_block_count = $formulaBlocks.Count
    markdown_table_count = $tableCount
    non_ascii_count = ([regex]::Matches($text, '[^\x00-\x7F]')).Count
  }
}

function Get-DocxMetrics {
  param([Parameter(Mandatory=$true)][string]$DocxPath)
  $result = [ordered]@{
    docx_readable = $false
    docx_formula_objects_count = 0
    docx_latex_fallback_count = 0
    embedded_image_count = 0
    docx_table_count = 0
    docx_error = ''
  }
  if (-not (Test-Path -LiteralPath $DocxPath)) {
    $result.docx_error = 'docx_missing'
    return $result
  }
  try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction SilentlyContinue
    $zip = [System.IO.Compression.ZipFile]::OpenRead($DocxPath)
    try {
      $docEntry = $zip.GetEntry('word/document.xml')
      if (-not $docEntry) { throw 'word/document.xml missing' }
      $reader = New-Object System.IO.StreamReader($docEntry.Open())
      try { $xml = $reader.ReadToEnd() } finally { $reader.Dispose() }
      $result.docx_readable = $true
      $result.docx_formula_objects_count = ([regex]::Matches($xml, '<m:oMath')).Count + ([regex]::Matches($xml, '<m:oMathPara')).Count
      $result.docx_latex_fallback_count = ([regex]::Matches($xml, '\$[^$]{1,300}\$')).Count
      $result.docx_table_count = ([regex]::Matches($xml, '<w:tbl')).Count
      $result.embedded_image_count = @($zip.Entries | Where-Object { $_.FullName -like 'word/media/*' }).Count
    } finally {
      $zip.Dispose()
    }
  } catch {
    $result.docx_error = $_.Exception.Message
  }
  $result
}

function Select-ReferenceDoc {
  param([Parameter(Mandatory=$true)][string]$RuntimeDir)
  $thesisFile = Join-Path $RuntimeDir 'thesis_match.json'
  if (-not (Test-Path -LiteralPath $thesisFile)) {
    return [ordered]@{ path = ''; missing_reason = 'thesis_match.json missing' }
  }
  try {
    $thesis = Get-Content -Raw -LiteralPath $thesisFile | ConvertFrom-Json
  } catch {
    return [ordered]@{ path = ''; missing_reason = 'thesis_match.json parse failed' }
  }
  $templateDir = [string]$thesis.template_dir
  if (-not $templateDir -or $templateDir -eq 'INTERNAL' -or -not (Test-Path -LiteralPath $templateDir -PathType Container)) {
    return [ordered]@{ path = ''; missing_reason = 'template_dir unavailable or INTERNAL' }
  }
  $candidates = Get-ChildItem -LiteralPath $templateDir -Recurse -File -Filter '*.docx' -ErrorAction SilentlyContinue |
    Where-Object {
      $_.Length -gt 10240 -and
      $_.Name -notmatch '(说明|readme|README|format2025|格式要求|通知)'
    } |
    Sort-Object @{Expression = { if ($_.Name -match '(reference|template|模板|论文)') { 0 } else { 1 } }}, Length -Descending
  if (-not $candidates) {
    return [ordered]@{ path = ''; missing_reason = "no usable .docx reference template in $templateDir" }
  }
  [ordered]@{ path = $candidates[0].FullName; missing_reason = '' }
}

function Invoke-PandocChecked {
  param(
    [Parameter(Mandatory=$true)]$PandocCommand,
    [Parameter(Mandatory=$true)][string[]]$Arguments
  )
  $errFile = [System.IO.Path]::GetTempFileName()
  try {
    $pandocExe = if ($PandocCommand.Path) { $PandocCommand.Path } elseif ($PandocCommand.Source) { $PandocCommand.Source } else { $PandocCommand.Name }
    & $pandocExe @Arguments 2> $errFile
    $exitCode = $LASTEXITCODE
    $stderrRaw = Get-Content -Raw -LiteralPath $errFile -ErrorAction SilentlyContinue
    $stderr = if ($null -eq $stderrRaw) { '' } else { $stderrRaw.Trim() }
    [ordered]@{ ok = ($exitCode -eq 0); exit_code = $exitCode; stderr = $stderr }
  } finally {
    Remove-Item -LiteralPath $errFile -Force -ErrorAction SilentlyContinue
  }
}

$wd = (Resolve-Path -LiteralPath $WorkDir).Path
if (-not $PaperOutput) {
  $pathsFile = Join-Path $wd 'project_paths.json'
  if (Test-Path $pathsFile) {
    $paths = Get-Content -Raw -LiteralPath $pathsFile | ConvertFrom-Json
    $PaperOutput = $paths.paper_output
  } else {
    $PaperOutput = Join-Path $wd 'paper_export'
  }
}
New-Item -ItemType Directory -Force -Path $PaperOutput | Out-Null

$paperMd = Join-Path $wd 'paper.md'
if (-not (Test-Path $paperMd)) {
  throw "paper.md not found in $wd"
}

$outMd = Join-Path $PaperOutput 'paper.md'
$outDocx = Join-Path $PaperOutput 'paper.docx'
$outTxt = Join-Path $PaperOutput 'paper.txt'
$outPdf = Join-Path $PaperOutput 'paper.pdf'
foreach ($target in @($outMd, $outDocx, $outTxt, $outPdf)) {
  Remove-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
}

Copy-Item -LiteralPath $paperMd -Destination $outMd -Force
$markdownMetrics = Get-MarkdownMetrics -MarkdownPath $paperMd
$reference = Select-ReferenceDoc -RuntimeDir $wd
$referenceDoc = [string]$reference.path

$pandoc = Get-Command pandoc -ErrorAction SilentlyContinue
if ($pandoc) {
  Push-Location $wd
  try {
    $docxArgs = @('paper.md', '--from', 'gfm+tex_math_dollars+pipe_tables', '--to', 'docx', '--output', $outDocx, '--resource-path', '.')
    if ($referenceDoc) { $docxArgs += "--reference-doc=$referenceDoc" }
    $docxRun = Invoke-PandocChecked -PandocCommand $pandoc -Arguments $docxArgs

    $txtArgs = @('paper.md', '--from', 'gfm', '--to', 'plain', '--output', $outTxt, '--resource-path', '.')
    $txtRun = Invoke-PandocChecked -PandocCommand $pandoc -Arguments $txtArgs

    $pdfArgs = @('paper.md', '--from', 'gfm+tex_math_dollars+pipe_tables', '--to', 'pdf', '--output', $outPdf, '--resource-path', '.')
    $pdfRun = Invoke-PandocChecked -PandocCommand $pandoc -Arguments $pdfArgs
    if (-not $pdfRun.ok) { $pdfError = $pdfRun.stderr }
  } finally {
    Pop-Location
  }
} else {
  Copy-Item -LiteralPath $paperMd -Destination $outTxt -Force
  $pandocMissing = $true
}

if (-not (Test-Path $outTxt)) {
  Copy-Item -LiteralPath $paperMd -Destination $outTxt -Force
  $txtFallback = 'paper.md copied as text because pandoc plain export failed'
}

if (-not (Test-Path $outDocx)) {
  $existingDocx = Join-Path $wd 'paper.docx'
  if (Test-Path $existingDocx) {
    $existing = Get-Item -LiteralPath $existingDocx
    $paper = Get-Item -LiteralPath $paperMd
    if ($existing.LastWriteTimeUtc -ge $paper.LastWriteTimeUtc) {
      Copy-Item -LiteralPath $existingDocx -Destination $outDocx -Force
      $docxFallback = 'copied runtime paper.docx newer than paper.md'
    } else {
      $docxFallbackRejected = 'runtime paper.docx older than paper.md; not reused'
    }
  }
}

if (-not (Test-Path $outPdf)) {
  try {
    $pdfSource = if (Test-Path $outTxt) { $outTxt } else { $paperMd }
    New-SimplePdf -TextPath $pdfSource -OutputPath $outPdf
    $pdfFallback = $true
    $pdfReadability = if ($markdownMetrics.non_ascii_count -gt 0) { 'placeholder' } else { 'text_only' }
  } catch {
    $pdfFallbackError = $_.Exception.Message
    $pdfReadability = 'failed_or_placeholder'
  }
} else {
  $pdfReadability = 'pandoc_pdf'
}

$docxMetrics = Get-DocxMetrics -DocxPath $outDocx
$paperPdfHighFidelity = (Test-Path $outPdf) -and (-not $pdfFallback)

$result = [ordered]@{
  paper_md = (Test-Path $outMd)
  paper_docx = (Test-Path $outDocx)
  paper_txt = (Test-Path $outTxt)
  paper_pdf = (Test-Path $outPdf)
  output_dir = (Resolve-Path -LiteralPath $PaperOutput).Path
  pandoc_available = [bool]$pandoc
  reference_doc_used = $referenceDoc
  reference_doc_missing_reason = [string]$reference.missing_reason
  paper_pdf_high_fidelity = [bool]$paperPdfHighFidelity
  pdf_readability = $pdfReadability
  markdown_image_count = $markdownMetrics.markdown_image_count
  markdown_formula_block_count = $markdownMetrics.markdown_formula_block_count
  markdown_table_count = $markdownMetrics.markdown_table_count
  non_ascii_count = $markdownMetrics.non_ascii_count
  docx_readable = $docxMetrics.docx_readable
  docx_formula_objects_count = $docxMetrics.docx_formula_objects_count
  docx_latex_fallback_count = $docxMetrics.docx_latex_fallback_count
  embedded_image_count = $docxMetrics.embedded_image_count
  docx_table_count = $docxMetrics.docx_table_count
}
if ($docxRun) { $result.docx_exit_code = $docxRun.exit_code; if ($docxRun.stderr) { $result.docx_error = $docxRun.stderr } }
if ($txtRun) { $result.txt_exit_code = $txtRun.exit_code; if ($txtRun.stderr) { $result.txt_error = $txtRun.stderr } }
if ($pdfRun) { $result.pdf_exit_code = $pdfRun.exit_code }
if ($pdfError) { $result.pdf_error = $pdfError }
if ($pdfFallback) { $result.pdf_fallback = 'simple text-only PDF; non-ASCII is replaced with ?' }
if ($pdfFallbackError) { $result.pdf_fallback_error = $pdfFallbackError }
if ($pandocMissing) { $result.error = 'pandoc not available; only markdown/text fallback produced' }
if ($txtFallback) { $result.txt_fallback = $txtFallback }
if ($docxFallback) { $result.docx_fallback = $docxFallback }
if ($docxFallbackRejected) { $result.docx_fallback_rejected = $docxFallbackRejected }
if ($docxMetrics.docx_error) { $result.docx_inspect_error = $docxMetrics.docx_error }

$json = $result | ConvertTo-Json -Depth 8
$json | Set-Content -LiteralPath (Join-Path $wd 'export_report.json') -Encoding UTF8
$json
