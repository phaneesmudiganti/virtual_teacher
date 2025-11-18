import os
import re
from gtts import gTTS
import tempfile
from pathlib import Path
from pypdf import PdfReader

def clean_text_for_audio(text):
    text = re.sub(r'\*\*|\*|__|~~|`|–|-', '', text)
    text = re.sub(r'\([^()\n]+\)', '', text)
    text = re.sub(r'(\d+\.\s*)([^\n]+)', r'\1\2.', text)
    text = re.sub(r'(English meaning:.*?)\n', r'\1. ', text)
    text = re.sub(r'\n\s*[\*\-•]\s*', r'. ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.replace('\n', ' ').strip()

def generate_tts(text, lang='en'):
    tts = gTTS(text=text, lang=lang)
    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(temp_audio.name)
    return temp_audio.name


def get_repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if parent.name == "src":
            return parent.parent  # repo root is the parent of 'src'
    # Fallback: assume current working directory is the repo root
    return Path.cwd()

def load_pdf_content(subject, chapter_number):
    """
    Loads PDF text content. Raises FileNotFoundError if the PDF doesn't exist.
    Raises ValueError if the PDF exists but has no extractable text.
    """

    repo_root = get_repo_root()
    content_root = os.path.join(repo_root, "content")
    path = os.path.join(content_root, subject.lower(), f"chapter{chapter_number}.pdf")

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Content not found: {path} "
            f"(subject={subject}, chapter={chapter_number})"
        )

    reader = PdfReader(path)
    content = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            content += text

    if not content:
        # PDF is present but has no extractable text (images, scanned, etc.)
        raise ValueError(
            f"PDF has no extractable text: {path}. "
            "Consider using OCR for scanned documents."
        )

    return content

def load_pdf_from_path(pdf_filepath: str | Path) -> str:
    """
    Extracts text from a PDF at pdf_filepath.
    Raises FileNotFoundError if path doesn't exist.
    Raises ValueError if no extractable text is found.
    """
    from pypdf import PdfReader  # use whichever you're using in your project
    p = Path(pdf_filepath)
    if not p.exists():
        raise FileNotFoundError(f"Uploaded file not found: {p}")
    if p.suffix.lower() != ".pdf":
        raise ValueError(f"Unsupported file type: {p.suffix}. Please upload a .pdf")

    reader = PdfReader(str(p))
    parts = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            parts.append(t)
    text = "\n".join(parts).strip()
    if not text:
        raise ValueError("The uploaded PDF has no extractable text. It may be scanned. Try OCR.")
    return text