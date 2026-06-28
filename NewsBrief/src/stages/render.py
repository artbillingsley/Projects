# src/stages/render.py
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import time

import structlog

log = structlog.get_logger()


class RenderError(Exception):
    pass


def _copy_audio_to_public(audio_dir: str, renderer_dir: str) -> None:
    """Copy audio MP3 files into Remotion's public/audio/ so <Audio src={staticFile('audio/X.mp3')}> works."""
    public_audio = os.path.join(renderer_dir, "public", "audio")
    os.makedirs(public_audio, exist_ok=True)

    for mp3 in glob.glob(os.path.join(audio_dir, "*.mp3")):
        dest = os.path.join(public_audio, os.path.basename(mp3))
        shutil.copy2(mp3, dest)
        log.info("render.copy_audio", src=mp3, dest=dest)


def _copy_images_to_public(image_dir: str, renderer_dir: str) -> None:
    """Copy stock photo JPGs into Remotion's public/images/ so staticFile('images/X.jpg') works."""
    public_images = os.path.join(renderer_dir, "public", "images")
    os.makedirs(public_images, exist_ok=True)
    for pattern in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        for img in glob.glob(os.path.join(image_dir, pattern)):
            dest = os.path.join(public_images, os.path.basename(img))
            shutil.copy2(img, dest)
            log.info("render.copy_image", src=img, dest=dest)


def render_videos(
    spec_path: str,
    output_dir: str,
    renderer_dir: str,
    audio_dir: str = "",
    timeout_seconds: int = 1200,
) -> float:
    log.info("render.start", spec=spec_path, output=output_dir)

    # Copy audio into Remotion public/ so staticFile() can serve them
    if audio_dir and os.path.isdir(audio_dir):
        _copy_audio_to_public(audio_dir, renderer_dir)

    # Copy stock photos into Remotion public/ so staticFile() can serve them
    image_dir = os.path.join(os.path.dirname(audio_dir), "images") if audio_dir else ""
    if image_dir and os.path.isdir(image_dir):
        _copy_images_to_public(image_dir, renderer_dir)

    render_script = os.path.join(renderer_dir, "render.sh")

    t0 = time.monotonic()
    result = subprocess.run(
        [render_script, spec_path, output_dir],
        capture_output=True,
        text=True,
        cwd=renderer_dir,
        timeout=timeout_seconds,
    )

    duration = time.monotonic() - t0

    if result.returncode != 0:
        log.error("render.failed", stderr=result.stderr[:500])
        raise RenderError(f"Render failed (exit {result.returncode}): {result.stderr[:500]}")

    log.info("render.done", duration_s=round(duration, 2))
    return duration
