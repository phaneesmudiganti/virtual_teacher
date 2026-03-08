"""Utility package exports.

Expose commonly used utilities at package level so callers can do:

	from virtual_teacher.utils import DocumentProcessor

Direct submodule imports remain available for advanced usage.
"""

from .document_processor import DocumentProcessor
from .audio_processor import AudioProcessor
from .file_manager import FileManager

__all__ = [
	'DocumentProcessor',
	'AudioProcessor',
	'FileManager'
]
