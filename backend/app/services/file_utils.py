"""File utility services for ZIP creation and management."""

import io
import os
import zipfile
from typing import Dict
from datetime import datetime
import hashlib


class FileUtilsService:
    """Service for file operations including ZIP creation."""

    def __init__(self, output_dir: str = "generated_code"):
        """
        Initialize file utils service.

        Args:
            output_dir: Directory to store generated files (relative to backend/)
        """
        self.output_dir = output_dir
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

    def create_zip_from_files(
        self, files: Dict[str, str], zip_name: str = None
    ) -> tuple[bytes, str]:
        """
        Create a ZIP file from a dictionary of filenames and contents.

        Args:
            files: Dictionary mapping filename to file content
            zip_name: Optional custom ZIP filename (without extension)

        Returns:
            Tuple of (zip_bytes, zip_filename)
        """
        # Generate ZIP filename if not provided
        if not zip_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_name = f"terraform_code_{timestamp}"

        if not zip_name.endswith(".zip"):
            zip_name = f"{zip_name}.zip"

        # Create ZIP file in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for filename, content in files.items():
                # Add file to ZIP
                zip_file.writestr(filename, content)

        # Get the ZIP bytes
        zip_buffer.seek(0)
        zip_bytes = zip_buffer.read()

        return zip_bytes, zip_name

    def save_zip_to_disk(self, zip_bytes: bytes, zip_name: str) -> str:
        """
        Save ZIP bytes to disk.

        Args:
            zip_bytes: ZIP file content as bytes
            zip_name: Name of the ZIP file

        Returns:
            Full path to the saved file
        """
        file_path = os.path.join(self.output_dir, zip_name)

        with open(file_path, "wb") as f:
            f.write(zip_bytes)

        return file_path

    def generate_file_hash(self, content: bytes) -> str:
        """
        Generate SHA256 hash of file content.

        Args:
            content: File content as bytes

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(content).hexdigest()

    def cleanup_old_files(self, max_age_hours: int = 24):
        """
        Clean up old generated files.

        Args:
            max_age_hours: Maximum age of files to keep (in hours)
        """
        if not os.path.exists(self.output_dir):
            return

        current_time = datetime.now().timestamp()
        max_age_seconds = max_age_hours * 3600

        for filename in os.listdir(self.output_dir):
            file_path = os.path.join(self.output_dir, filename)

            # Skip if not a file
            if not os.path.isfile(file_path):
                continue

            # Check file age
            file_mtime = os.path.getmtime(file_path)
            age_seconds = current_time - file_mtime

            # Delete if too old
            if age_seconds > max_age_seconds:
                try:
                    os.remove(file_path)
                except Exception:
                    # Ignore errors during cleanup
                    pass
