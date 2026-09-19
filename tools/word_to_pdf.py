from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


class WordToPdfConverter:
    """Export Word documents through Microsoft Word or WPS Writer."""

    POWERSHELL_SCRIPT = r"""
param(
    [Parameter(Mandatory=$true)][string]$Source,
    [Parameter(Mandatory=$true)][string]$Destination,
    [Parameter(Mandatory=$true)][string]$Quality
)
$ErrorActionPreference = 'Stop'
$writer = $null
$document = $null
try {
    $errors = @()
    foreach ($progId in @('Word.Application', 'KWPS.Application', 'wps.Application')) {
        try {
            $writer = New-Object -ComObject $progId
            break
        }
        catch {
            $errors += "${progId}: $($_.Exception.Message)"
        }
    }
    if ($null -eq $writer) {
        throw "Microsoft Word or WPS Writer was not found. $($errors -join '; ')"
    }
    $writer.Visible = $false
    try { $writer.DisplayAlerts = 0 } catch {}
    $document = $writer.Documents.Open($Source, $false, $true)
    $optimizeFor = if ($Quality -eq 'small') { 1 } else { 0 }
    try {
        # Word and current WPS releases expose the Word-compatible signature.
        $document.ExportAsFixedFormat(
            $Destination, 17, $false, $optimizeFor, 0, 1, 9999,
            0, $true, $true, 0, $true, $true, $false
        )
    }
    catch {
        # Older WPS releases only expose the required output arguments.
        $document.ExportAsFixedFormat($Destination, 17)
    }
}
finally {
    if ($null -ne $document) {
        $document.Close($false)
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($document)
    }
    if ($null -ne $writer) {
        $writer.Quit()
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($writer)
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
"""

    def convert(self, source_path: str, output_dir: str | Path, quality: str = "high") -> Path:
        source = Path(source_path).resolve()
        if not source.is_file() or source.suffix.lower() not in (".doc", ".docx"):
            raise ValueError("Please select a valid Word document.")
        destination_dir = Path(output_dir).resolve()
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / f"{source.stem}.pdf"

        script_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".ps1", prefix="niub-word-pdf-",
                encoding="utf-8-sig", delete=False,
            ) as script:
                script.write(self.POWERSHELL_SCRIPT)
                script_path = Path(script.name)
            result = subprocess.run(
                [
                    "powershell.exe", "-NoProfile", "-NonInteractive",
                    "-ExecutionPolicy", "Bypass", "-File", str(script_path),
                    "-Source", str(source), "-Destination", str(destination),
                    "-Quality", "small" if quality == "small" else "high",
                ],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False,
            )
        finally:
            if script_path is not None:
                script_path.unlink(missing_ok=True)

        if result.returncode != 0 or not destination.is_file():
            destination.unlink(missing_ok=True)
            if source.suffix.lower() == ".docx":
                from tools.docx_pdf_renderer import DocxPdfRenderer
                DocxPdfRenderer().convert(source, destination, quality)
            else:
                details = (result.stderr or result.stdout).strip()
                raise RuntimeError(details or "Legacy DOC files require Microsoft Word or WPS Writer.")
        with destination.open("rb") as pdf_file:
            if pdf_file.read(5) != b"%PDF-":
                destination.unlink(missing_ok=True)
                raise RuntimeError("Microsoft Word or WPS Writer did not create a valid PDF file.")
        return destination
