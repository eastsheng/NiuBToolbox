from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Callable

import cv2
import imageio_ffmpeg
from PIL import Image


ProgressCallback = Callable[[int], None]
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".wmv"}


class MediaConverter:
    """Convert video to GIF or GIF to MP4 through a bundled FFmpeg binary."""

    @staticmethod
    def _unique_output(source: Path, suffix: str) -> Path:
        candidate = source.with_name(f"{source.stem}_converted{suffix}")
        number = 2
        while candidate.exists():
            candidate = source.with_name(f"{source.stem}_converted_{number}{suffix}")
            number += 1
        return candidate

    @staticmethod
    def _duration(source: Path) -> float:
        if source.suffix.lower() == ".gif":
            with Image.open(source) as image:
                return max(0.001, sum(frame.info.get("duration", 100) for frame in _frames(image)) / 1000)
        capture = cv2.VideoCapture(str(source))
        try:
            fps = capture.get(cv2.CAP_PROP_FPS)
            frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
            return max(0.001, frames / fps) if fps > 0 and frames > 0 else 1.0
        finally:
            capture.release()

    @classmethod
    def _source_fps(cls, source: Path) -> float:
        if source.suffix.lower() == ".gif":
            with Image.open(source) as image:
                return max(1.0, min(60.0, getattr(image, "n_frames", 1) / cls._duration(source)))
        capture = cv2.VideoCapture(str(source))
        try:
            value = capture.get(cv2.CAP_PROP_FPS)
            return max(1.0, min(60.0, value)) if value > 0 else 12.0
        finally:
            capture.release()

    @staticmethod
    def _scale_filter(max_width: int) -> str:
        if max_width <= 0:
            return "scale=trunc(iw/2)*2:trunc(ih/2)*2"
        return f"scale='min({max_width},iw)':-2:flags=lanczos"

    def convert(
        self,
        source_path: str | Path,
        fps: int = 12,
        max_width: int = 720,
        callback: ProgressCallback | None = None,
    ) -> Path:
        source = Path(source_path).resolve()
        extension = source.suffix.lower()
        if not source.is_file() or (extension != ".gif" and extension not in VIDEO_EXTENSIONS):
            raise ValueError("Please select a supported video or GIF file.")

        to_gif = extension != ".gif"
        destination = self._unique_output(source, ".gif" if to_gif else ".mp4")
        scale = self._scale_filter(max_width)
        output_fps = self._source_fps(source) if fps <= 0 else float(fps)
        fps_filter = f"fps={output_fps:.3f}"
        if to_gif:
            video_filter = (
                f"{fps_filter},{scale},split[source][palette];"
                "[palette]palettegen=max_colors=256[colors];"
                "[source][colors]paletteuse=dither=sierra2_4a"
            )
            output_options = ["-vf", video_filter, "-loop", "0"]
        else:
            output_options = [
                "-vf", f"{fps_filter},{scale},format=yuv420p",
                "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-movflags", "+faststart", "-an",
            ]

        command = [
            imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(source), *output_options,
            "-progress", "pipe:1", "-nostats", str(destination),
        ]
        duration = self._duration(source)
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags,
        )
        output: list[str] = []
        assert process.stdout is not None
        for line in process.stdout:
            line = line.strip()
            output.append(line)
            match = re.match(r"out_time_ms=(\d+)", line)
            if match and callback is not None:
                seconds = int(match.group(1)) / 1_000_000
                callback(min(99, max(0, int(seconds / duration * 100))))
        return_code = process.wait()
        if return_code != 0 or not destination.is_file() or destination.stat().st_size == 0:
            destination.unlink(missing_ok=True)
            details = "\n".join(output[-12:]).strip()
            raise RuntimeError(details or f"FFmpeg exited with code {return_code}.")
        if callback is not None:
            callback(100)
        return destination


def _frames(image: Image.Image):
    for index in range(getattr(image, "n_frames", 1)):
        image.seek(index)
        yield image
