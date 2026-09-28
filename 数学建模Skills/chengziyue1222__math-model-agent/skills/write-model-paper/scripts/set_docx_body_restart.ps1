param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$resolved = (Resolve-Path -LiteralPath $Path).Path
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $document = $word.Documents.Open($resolved, $false, $false, $false)
    $range = $document.Content
    $target = -join @(
        [char]0x95EE,
        [char]0x9898,
        [char]0x91CD,
        [char]0x8FF0
    )
    $found = $range.Find.Execute($target)
    if (-not $found) {
        throw "Cannot locate the problem-restatement heading for the body-section restart."
    }
    $range.Collapse(1) # wdCollapseStart
    $range.InsertBreak(2) # wdSectionBreakNextPage

    if ($document.Sections.Count -lt 2) {
        throw "The body section break was not created."
    }
    for ($index = 1; $index -lt $document.Sections.Count; $index++) {
        $frontFooter = $document.Sections.Item($index).Footers.Item(1)
        $frontFooter.LinkToPrevious = $false
        $frontFooter.Range.Text = ""
    }
    $body = $document.Sections.Item($document.Sections.Count)
    $bodyFooter = $body.Footers.Item(1)
    $bodyFooter.LinkToPrevious = $false
    $bodyFooter.Range.Text = ""
    $null = $bodyFooter.PageNumbers.Add(1, $true) # centered, show on first page
    $body.Footers.Item(1).PageNumbers.RestartNumberingAtSection = $true
    $body.Footers.Item(1).PageNumbers.StartingNumber = 1
    $document.Save()
    $document.Close($false)
}
finally {
    $word.Quit()
}
