"""
File management utilities extracted from `utils.py`.
"""
import os
import logging
from pathlib import Path
import fitz

logger = logging.getLogger(__name__)


class FileManager:
    """
    Handles file system operations and content loading.
    """

    @staticmethod
    def get_repo_root() -> Path:
        cur = Path(__file__).resolve()
        for parent in cur.parents:
            if parent.name == "src":
                repo_root = parent.parent
                logger.info(f"Detected repo root: {repo_root}")
                return repo_root
        repo_root = Path.cwd()
        logger.info(f"Fallback repo root: {repo_root}")
        return repo_root

    @staticmethod
    def load_pdf_content(subject: str, chapter_number: int) -> str:
        repo_root = FileManager.get_repo_root()
        content_root = os.path.join(repo_root, "content")
        path = os.path.join(content_root, subject.lower(), f"chapter{chapter_number}.pdf")
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Content not found: {path} "
                f"(subject={subject}, chapter={chapter_number})"
            )
        logger.info(f"Loading PDF content: {path}")
        doc = fitz.open(path)
        content = ""
        for page in doc:
            text = page.get_text()
            if text:
                content += text
        doc.close()
        if not content:
            raise ValueError(
                f"PDF has no extractable text: {path}. "
                "Consider using OCR for scanned documents."
            )
        logger.info(f"Loaded PDF content characters: {len(content)}")
        return content

    @staticmethod
    def load_pdf_from_path(pdf_filepath: str | Path) -> str:
        p = Path(pdf_filepath)
        if not p.exists():
            raise FileNotFoundError(f"Uploaded file not found: {p}")
        if p.suffix.lower() != ".pdf":
            raise ValueError(f"Unsupported file type: {p.suffix}. Please upload a .pdf")
        doc = fitz.open(str(p))
        parts = []
        for page in doc:
            text = page.get_text()
            if text:
                parts.append(text)
        doc.close()
        text = "\n".join(parts).strip()
        logger.info(f"Extracted uploaded PDF characters: {len(text)}")
        if not text:
            raise ValueError("The uploaded PDF has no extractable text. It may be scanned. Try OCR.")
        return text
