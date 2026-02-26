"""
Virtual Teacher Utilities Module

This module provides utility classes and functions for:
- Document processing (OCR, PDF extraction, content analysis)
- Audio processing (TTS, text cleaning)
- File management (repository paths, content loading)
"""

import os
import re
import io
import tempfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import pytesseract
from PIL import Image
import cv2
import numpy as np
import fitz 
from gtts import gTTS
import pyttsx3
from virtual_teacher.llm.indic_processor import get_indic_processor

logger = logging.getLogger(__name__)


# ============================================================================
# DOCUMENT PROCESSING CLASSES
# ============================================================================

class DocumentProcessor:
    """
    Handles various document types including camera-captured PDFs and images.
    Provides OCR capabilities and content analysis.
    """

    def __init__(self, tesseract_path: Optional[str] = None):
        """
        Initialize DocumentProcessor.

        Args:
            tesseract_path: Optional path to Tesseract executable (for Windows)
        """
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def enhance_image_quality(self, image_path: str) -> str:
        """
        Enhance image quality for better OCR results.

        Args:
            image_path: Path to the input image

        Returns:
            Path to the enhanced image
        """
        logger.info(f"Enhancing image quality: {image_path}")
        img = cv2.imread(image_path)

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply noise reduction
        denoised = cv2.fastNlMeansDenoising(gray)

        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # Save enhanced image
        enhanced_path = image_path.replace('.jpg', '_enhanced.jpg').replace('.png', '_enhanced.png')
        cv2.imwrite(enhanced_path, thresh)
        logger.info(f"Enhanced image saved: {enhanced_path}")

        return enhanced_path

    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from image using OCR.

        Args:
            image_path: Path to the image file

        Returns:
            Extracted text content

        Raises:
            ValueError: If text extraction fails
        """
        try:
            logger.info(f"Extracting text from image: {image_path}")
            # Enhance image quality first
            enhanced_path = self.enhance_image_quality(image_path)

            # Use Tesseract for OCR
            text = pytesseract.image_to_string(
                Image.open(enhanced_path),
                config='--psm 6 -l eng'  # Page segmentation mode 6, English language
            )

            # Clean up temporary enhanced image
            if os.path.exists(enhanced_path):
                os.remove(enhanced_path)

            result = text.strip()
            logger.info(f"Image OCR extracted characters: {len(result)}")
            return result

        except Exception:
            logger.exception("Failed to extract text from image")
            raise ValueError("Failed to extract text from image")

    def process_pdf_with_ocr(self, pdf_path: str) -> str:
        """
        Process PDF using OCR for scanned documents.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text content

        Raises:
            ValueError: If PDF processing fails
        """
        try:
            logger.info(f"Processing PDF with OCR if needed: {pdf_path}")
            # First try regular text extraction
            regular_text = self._extract_regular_pdf_text(pdf_path)
            if regular_text and len(regular_text.strip()) > 50:
                logger.info("Using regular PDF text extraction path")
                return regular_text

            # If no text or very little text, use OCR
            logger.info("Falling back to OCR PDF extraction")
            return self._extract_pdf_with_ocr(pdf_path)

        except Exception:
            logger.exception("Failed to process PDF")
            raise ValueError("Failed to process PDF")

    def identify_content_type(self, text: str) -> Dict[str, Any]:
        """
        Identify what type of content this is (homework, textbook, etc.)

        Args:
            text: Text content to analyze

        Returns:
            Dictionary containing content analysis results
        """
        text_lower = text.lower()

        content_type = {
            'type': 'general',
            'subject': 'unknown',
            'has_questions': False,
            'has_exercises': False,
            'confidence': 0.5
        }

        # Subject identification
        subjects = {
            'math': ['math', 'mathematics', 'algebra', 'geometry', 'arithmetic',
                     'addition', 'subtraction', 'multiplication', 'division'],
            'english': ['english', 'grammar', 'vocabulary', 'reading', 'writing', 'story', 'poem'],
            'science': ['science', 'physics', 'chemistry', 'biology', 'experiment', 'observation'],
            'history': ['history', 'ancient', 'medieval', 'freedom', 'independence', 'rulers'],
            'geography': ['geography', 'map', 'continent', 'country', 'climate', 'river', 'mountain']
        }

        for subject, keywords in subjects.items():
            if any(keyword in text_lower for keyword in keywords):
                content_type['subject'] = subject
                content_type['confidence'] = 0.8
                break

        # Content type identification
        if any(word in text_lower for word in ['homework', 'assignment', 'complete', 'solve']):
            content_type['type'] = 'homework'
            content_type['confidence'] = 0.9
        elif any(word in text_lower for word in ['chapter', 'lesson', 'learn', 'understand']):
            content_type['type'] = 'textbook'
            content_type['confidence'] = 0.8

        # Question detection
        question_indicators = ['?', 'what', 'how', 'why', 'where', 'when', 'which', 'solve', 'find', 'calculate']
        if any(indicator in text_lower for indicator in question_indicators):
            content_type['has_questions'] = True

        # Exercise detection
        exercise_indicators = ['exercise', 'practice', 'solve', 'complete', 'fill', 'choose', 'match']
        if any(indicator in text_lower for indicator in exercise_indicators):
            content_type['has_exercises'] = True

        return content_type

    def _extract_regular_pdf_text(self, pdf_path: str) -> str:
        """Try regular PDF text extraction first (private method)"""
        try:
            doc = fitz.open(pdf_path)
            content = ""
            for page in doc:
                text = page.get_text()
                if text:
                    content += text + "\n"
            doc.close()
            logger.info(f"Regular PDF extraction characters: {len(content.strip())}")
            return content.strip()
        except Exception:
            logger.exception("Regular PDF text extraction failed")
            return ""

    def _extract_pdf_with_ocr(self, pdf_path: str) -> str:
        doc = fitz.open(pdf_path)
        full_text = ""
        try:
            for page_num in range(doc.page_count):
                page = doc[page_num]
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("ppm")
                img = Image.open(io.BytesIO(img_data))
                page_text = pytesseract.image_to_string(img, config='--psm 6 -l eng')
                full_text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                logger.debug(f"OCR processed page {page_num + 1}")
            return full_text.strip()
        except Exception:
            logger.exception("OCR PDF extraction failed")
            return full_text.strip()
        finally:
            doc.close()


class AudioProcessor:
    """
    Enhanced audio processing with Indian language support
    """

    @staticmethod
    def clean_text_for_audio(text: str, preserve_parentheses: bool = None) -> str:
        text = re.sub(r'\*\*|\*|__|~~|`|-', '', text)
        if not preserve_parentheses:
            text = re.sub(r'\([^()\n]+\)', '', text)
        text = re.sub(r'(\d+\.\s*)([^\n]+)', r'\1\2.', text)
        text = re.sub(r'(English meaning:.*?)\n', r'\1. ', text)
        text = re.sub(r'\n\s*[\*\->]\s*', r'. ', text)
        text = re.sub(r'\s{2,}', ' ', text)
        return text.replace('\n', ' ').strip()



    @staticmethod
    def generate_tts(text: str, lang: str = 'en') -> str:
        """
        Generate text-to-speech with Indian language support.

        Args:
            text: Text to convert to speech
            lang: Language code ('en', 'hi', 'hi-in')

        Returns:
            Path to the generated audio file
        """
        try:
            logger.info(f"Generating TTS, lang={lang}")
            # For Hindi/Indian languages, use different TTS approach
            if lang in ['hi', 'hi-in', 'hindi']:
                return AudioProcessor._generate_indic_tts(text, lang)
            else:
                # Use gTTS for English
                return AudioProcessor._generate_gtts(text, lang)
                
        except Exception:
            logger.exception("TTS generation failed")
            # Fallback to system TTS
            return AudioProcessor._generate_system_tts(text, lang)
    
    @staticmethod
    def _generate_gtts(text: str, lang: str) -> str:
        """Generate TTS using gTTS (existing method)"""
        tts = gTTS(text=text, lang=lang)
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(temp_audio.name)
        logger.info(f"gTTS audio saved: {temp_audio.name}")
        return temp_audio.name
    
    @staticmethod  
    def _generate_indic_tts(text: str, lang: str) -> str:
        """Generate TTS for Indian languages"""
        try:
            # Use pyttsx3 for Indian languages (better Hindi support)
            engine = pyttsx3.init()
            
            # Configure for Hindi if available
            voices = engine.getProperty('voices')
            for voice in voices:
                if 'hindi' in voice.name.lower() or 'hi' in voice.id.lower():
                    engine.setProperty('voice', voice.id)
                    break
            
            # Adjust speech rate for Indian languages
            engine.setProperty('rate', 150)  # Slower for better comprehension
            
            temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            engine.save_to_file(text, temp_audio.name)
            engine.runAndWait()
            
            logger.info(f"Indic TTS audio saved: {temp_audio.name}")
            return temp_audio.name
            
        except Exception:
            logger.exception("Indic TTS failed")
            # Fallback to gTTS with hindi support
            return AudioProcessor._generate_gtts(text, 'hi')
    
    @staticmethod
    def _generate_system_tts(text: str, lang: str) -> str:
        """Fallback system TTS"""
        try:
            engine = pyttsx3.init()
            temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            engine.save_to_file(text, temp_audio.name)
            engine.runAndWait()
            logger.info(f"System TTS audio saved: {temp_audio.name}")
            return temp_audio.name
        except Exception:
            logger.exception("System TTS failed")
            temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            return temp_audio.name

class FileManager:
    """
    Handles file system operations and content loading.
    """

    @staticmethod
    def get_repo_root() -> Path:
        """
        Get the repository root directory.

        Returns:
            Path to the repository root
        """
        cur = Path(__file__).resolve()
        for parent in cur.parents:
            if parent.name == "src":
                repo_root = parent.parent
                logger.info(f"Detected repo root: {repo_root}")
                return repo_root
        # Fallback: assume current working directory is the repo root
        repo_root = Path.cwd()
        logger.info(f"Fallback repo root: {repo_root}")
        return repo_root

    @staticmethod
    def load_pdf_content(subject: str, chapter_number: int) -> str:
        """
        Load PDF text content from repository.

        Args:
            subject: Subject name
            chapter_number: Chapter number

        Returns:
            PDF text content

        Raises:
            FileNotFoundError: If the PDF doesn't exist
            ValueError: If the PDF exists but has no extractable text
        """
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
        """
        Extract text from a PDF at the specified path.

        Args:
            pdf_filepath: Path to the PDF file

        Returns:
            Extracted text content

        Raises:
            FileNotFoundError: If path doesn't exist
            ValueError: If no extractable text is found or unsupported file type
        """
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


# ============================================================================
# CONVENIENCE FUNCTIONS (for backward compatibility)
# ============================================================================

def clean_text_for_audio(text: str, preserve_parentheses: bool = None) -> str:
    """Convenience function for AudioProcessor.clean_text_for_audio"""
    return AudioProcessor.clean_text_for_audio(text, preserve_parentheses)


def generate_tts(text: str, lang: str = 'en') -> str:
    """Convenience function for AudioProcessor.generate_tts"""
    return AudioProcessor.generate_tts(text, lang)


def get_repo_root() -> Path:
    """Convenience function for FileManager.get_repo_root"""
    return FileManager.get_repo_root()


def load_pdf_content(subject: str, chapter_number: int) -> str:
    """Convenience function for FileManager.load_pdf_content"""
    return FileManager.load_pdf_content(subject, chapter_number)


def load_pdf_from_path(pdf_filepath: str | Path) -> str:
    """Convenience function for FileManager.load_pdf_from_path"""
    return FileManager.load_pdf_from_path(pdf_filepath)


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    # Classes
    'DocumentProcessor',
    'AudioProcessor',
    'FileManager',

    # Convenience functions
    'clean_text_for_audio',
    'generate_tts',
    'get_repo_root',
    'load_pdf_content',
    'load_pdf_from_path'
]
