<#
.SYNOPSIS
ROTA-EXCEL-VBA-ENGINE-ADAPTER brief.md section 10: deterministic build of
ELNATH_ROTA_ADDIN.xlam from its VBA source (src/elnath_rota_addin.bas).

Requires a real, licensed desktop Excel installation with "Trust access
to the VBA project object model" enabled (Excel Options -> Trust Center
-> Trust Center Settings -> Macro Settings) -- this is a one-time setting
on the BUILD machine only, never required of the end user's machine.
The .xlam itself carries no macro-security prompt of its own kind beyond
the normal one-time "enable this add-in" Excel already shows for any
add-in the first time it loads.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File excel\build_addin.ps1
#>
[CmdletBinding()]
param(
    [string]$SourcePath = (Join-Path $PSScriptRoot "src\elnath_rota_addin.bas"),
    [string]$OutputPath = (Join-Path $PSScriptRoot "ELNATH_ROTA_ADDIN.xlam")
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $SourcePath)) {
    throw "VBA source not found: $SourcePath"
}
if (Test-Path $OutputPath) {
    Remove-Item $OutputPath -Force
}

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
try {
    $workbook = $excel.Workbooks.Add()

    try {
        $workbook.VBProject.VBComponents.Import($SourcePath) | Out-Null
    } catch {
        throw "Could not import VBA source. In Excel: File > Options > Trust Center > " + `
              "Trust Center Settings > Macro Settings > check 'Trust access to the VBA " + `
              "project object model', then re-run this script. Original error: $($_.Exception.Message)"
    }

    # A blank Workbooks.Add() default module (if any) is left as-is --
    # Excel does not add one to a new .xlsm/.xlam-bound workbook by
    # default, so ElnathRotaAddin is the only module.

    $workbook.IsAddin = $true
    # xlOpenXMLAddIn = 55 (.xlam)
    $workbook.SaveAs($OutputPath, 55)
    $workbook.Close($false)
    Write-Host "Built $OutputPath"
} finally {
    $excel.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
}
