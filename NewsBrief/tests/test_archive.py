# tests/test_archive.py
from unittest.mock import MagicMock, patch
import pytest


def test_archive_creates_date_folder():
    from src.stages.archive import archive_to_drive

    mock_service = MagicMock()
    mock_service.files.return_value.create.return_value.execute.return_value = {"id": "folder123"}

    with patch("src.stages.archive.get_drive_service", return_value=mock_service), \
         patch("src.stages.archive.upload_file_to_drive"), \
         patch("os.listdir", return_value=[]), \
         patch("os.path.isfile", return_value=False), \
         patch("os.path.isdir", return_value=False):

        result = archive_to_drive(
            artifacts_dir="/tmp/2026-06-10",
            parent_folder_id="root123",
            sa_key_path="/fake/key.json",
            date_str="2026-06-10",
        )

    assert result == "https://drive.google.com/drive/folders/folder123"
    # Verify create_folder was called (via the service mock)
    mock_service.files.return_value.create.assert_called()
