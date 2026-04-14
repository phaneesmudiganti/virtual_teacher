"""
Audio processing utilities extracted from `utils.py`.
"""
import re
import tempfile
import logging
from typing import Optional
from gtts import gTTS
import pyttsx3

logger = logging.getLogger(__name__)


class AudioProcessor:
    """
    Enhanced audio processing with Indian language support
    """

    @staticmethod
    def clean_text_for_audio(text: str, preserve_parentheses: bool = False) -> str:
        text = re.sub(r'\*\*|\*|__|~~|`|–|-', '', text)
        def _paren_repl(match):
            inner = match.group(1).strip()
            if not inner:
                return ''
            if inner.endswith(('.', '!', '?')):
                return f". {inner} "
            return f". {inner}. "
        text = re.sub(r'\(([^()\n]+)\)', _paren_repl, text)
        text = re.sub(r'(\d+\.\s*)([^\n]+)', r'\1\2.', text)
        text = re.sub(r'(English meaning:.*?)\n', r'\1. ', text)
        text = re.sub(
            r'([^\n]*?:[^\n]+)\n',
            lambda m: (
                lambda line: f"{line} " if line.endswith(('.', '!', '?')) else f"{line}. "
            )(m.group(1).strip()),
            text
        )
        text = re.sub(r'\s-\s', '. ', text)
        text = re.sub(r'\n\s*[\*\-•]\s*', r'. ', text)
        text = re.sub(r'\s{2,}', ' ', text)
        return text.replace('\n', ' ').strip()

    @staticmethod
    def generate_tts(text: str, lang: str = 'en') -> str:
        try:
            logger.info(f"Generating TTS, lang={lang}")
            if lang in ['hi', 'hi-in', 'hindi']:
                return AudioProcessor._generate_gtts(text, lang)
            else:
                return AudioProcessor._generate_gtts(text, lang)
        except Exception:
            logger.exception("TTS generation failed")
            return AudioProcessor._generate_system_tts(text, lang)

    @staticmethod
    def _generate_gtts(text: str, lang: str) -> str:
        tts = gTTS(text=text, lang=lang)
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(temp_audio.name)
        logger.info(f"gTTS audio saved: {temp_audio.name}")
        return temp_audio.name

    @staticmethod  
    def _generate_indic_tts(text: str, lang: str) -> str:
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            for voice in voices:
                if 'hindi' in voice.name.lower() or 'hi' in voice.id.lower():
                    engine.setProperty('voice', voice.id)
                    break
            engine.setProperty('rate', 150)
            temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            engine.save_to_file(text, temp_audio.name)
            engine.runAndWait()
            logger.info(f"Indic TTS audio saved: {temp_audio.name}")
            return temp_audio.name
        except Exception:
            logger.exception("Indic TTS failed")
            return AudioProcessor._generate_gtts(text, 'hi')

    @staticmethod
    def _generate_system_tts(text: str, lang: str) -> str:
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
