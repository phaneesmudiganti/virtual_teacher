"""
Simple file-based response store to reuse text and audio without re-running the LLM.
"""
from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from .file_manager import FileManager


class ResponseStore:
    """
    Stores responses in a JSON index with audio copied into a stable folder.
    """

    def __init__(self, root_dir: Optional[Path] = None) -> None:
        repo_root = FileManager.get_repo_root()
        self.root_dir = root_dir or (repo_root / "data" / "response_store")
        self.audio_dir = self.root_dir / "audio"
        self.index_path = self.root_dir / "index.json"
        self._ensure_dirs()
        self._index = self._load_index()

    def _ensure_dirs(self) -> None:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> Dict[str, Any]:
        if not self.index_path.exists():
            return {}
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_index(self) -> None:
        self.index_path.write_text(
            json.dumps(self._index, ensure_ascii=True, indent=2),
            encoding="utf-8"
        )

    @staticmethod
    def _stable_hash(payload: Dict[str, Any]) -> str:
        data = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    @staticmethod
    def file_hash(path: str | Path) -> str:
        p = Path(path)
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def get(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        key = self._stable_hash(payload)
        return self._index.get(key)

    def save(self, payload: Dict[str, Any], response_text: str, audio_path: Optional[str]) -> Dict[str, Any]:
        key = self._stable_hash(payload)
        stored_audio = None

        if audio_path:
            src = Path(audio_path)
            if src.exists():
                ext = src.suffix or ".mp3"
                dst = self.audio_dir / f"{key}{ext}"
                try:
                    shutil.copyfile(src, dst)
                    stored_audio = str(dst)
                except Exception:
                    stored_audio = audio_path

        entry = {
            "text": response_text,
            "audio_path": stored_audio or audio_path,
            "meta": payload,
        }
        self._index[key] = entry
        self._save_index()
        return entry
