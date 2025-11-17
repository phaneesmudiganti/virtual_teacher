import os
import re
from gtts import gTTS
import tempfile
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


def load_pdf_content(subject, chapter_number):
    path = f"content/{subject.lower()}/chapter{chapter_number}.pdf"
    if not os.path.exists(path):
        return f"No content found for subject: {subject} Chapter {chapter_number}."
    reader = PdfReader(path)
    content = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            content += text
    return content