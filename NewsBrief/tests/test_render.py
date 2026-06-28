# tests/test_render.py
from unittest.mock import patch, MagicMock
import pytest


def test_render_calls_subprocess_with_correct_args():
    from src.stages.render import render_videos

    with patch("src.stages.render.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        render_videos(
            spec_path="/tmp/spec.json",
            output_dir="/tmp/output",
            renderer_dir="/path/to/newsbrief-renderer",
        )

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd = call_args[0][0]  # first positional arg is the command list
        assert "render.sh" in cmd[0] or "render.sh" in " ".join(str(c) for c in cmd)


def test_render_raises_on_nonzero_exit():
    from src.stages.render import render_videos, RenderError

    with patch("src.stages.render.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Chromium crash")

        with pytest.raises(RenderError, match="Render failed"):
            render_videos(
                spec_path="/tmp/spec.json",
                output_dir="/tmp/output",
                renderer_dir="/path/to/renderer",
            )
