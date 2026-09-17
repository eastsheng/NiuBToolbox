from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import cajCvtPdf


class CajToPdfConverter:
    """Run the bundled caj2pdf engine in an isolated working directory."""

    @staticmethod
    def _available_output(source: Path) -> Path:
        output = source.with_suffix(".pdf")
        index = 2
        while output.exists():
            output = source.with_name(f"{source.stem}_{index}.pdf")
            index += 1
        return output

    def convert(self, source_path: str, output_dir: str | Path | None = None) -> Path:
        source = Path(source_path).resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        if source.suffix.lower() not in (".caj", ".nh", ".kdh"):
            raise ValueError("Unsupported CAJ file extension.")

        engine_dir = Path(cajCvtPdf.__file__).resolve().parent / "bin"
        engine = engine_dir / "caj2pdf.exe"
        mutool = engine_dir / "mutool.exe"
        if not engine.is_file():
            raise FileNotFoundError("The CAJ conversion engine was not found.")
        if not mutool.is_file():
            raise FileNotFoundError("The MuPDF conversion component was not found.")

        output = self._available_output(Path(output_dir) / source.name if output_dir else source)
        environment = os.environ.copy()
        environment["PATH"] = str(engine_dir) + os.pathsep + environment.get("PATH", "")
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        with tempfile.TemporaryDirectory(prefix="NiuBToolbox-caj-") as work_dir:
            result = subprocess.run(
                [str(engine), "convert", str(source), "-o", str(output), "-m", str(mutool)],
                cwd=work_dir,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW,
                check=False,
            )
        if result.returncode != 0 or not output.is_file():
            output.unlink(missing_ok=True)
            details = (result.stderr or result.stdout).strip()
            raise RuntimeError(details or f"caj2pdf exited with code {result.returncode}.")
        with output.open("rb") as pdf_file:
            signature = pdf_file.read(5)
        if output.stat().st_size < 5 or signature != b"%PDF-":
            output.unlink(missing_ok=True)
            raise RuntimeError("The converter did not produce a valid PDF file.")
        return output
