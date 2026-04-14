---
title: Virtual Teacher
sdk: docker
app_port: 7860
---

# Virtual Teacher

## Project Overview
Virtual Teacher is a Gradio-based, multi-agent tutoring app built with crewAI. It helps Indian school students (CBSE and similar boards) by explaining textbook chapters, answering questions, and assisting with uploaded PDFs or photos of homework/textbook pages using OCR. Target users are students and educators who want a friendly, step-by-step learning assistant with English/Hindi support.

## Architecture Overview
- **High-level flow**: Gradio UI collects subject/chapter/mode + user questions -> crewAI agents/tasks generate responses -> optional OCR + document tools for uploaded content -> text response + TTS audio.
- **Key components**
  - `virtual_teacher.main`: Gradio UI, session orchestration, routing between modes, and response cleanup.
  - `virtual_teacher.crew`: crewAI agents and tasks wiring (chapter teacher, document teacher, greeter).
  - `virtual_teacher.tools.custom_tool`: CrewAI tools for recording user details, handling off-topic questions, document processing, and answering from extracted document content.
  - `virtual_teacher.utils.*`: OCR/document handling (`DocumentProcessor`), file loading (`FileManager`), and TTS (`AudioProcessor`).
  - `virtual_teacher.llm.llm_manager`: OpenAI model selection and configuration.
- **Data flow and integration points**
  - Chapter mode: PDF content is loaded from `content/<subject>/chapter< n >.pdf`.
  - Upload/Camera document mode: OCR pipeline (PyMuPDF + Tesseract + OpenCV) extracts text and stores it in a temp file, tracked via `CURRENT_SESSION_CONTENT`.
  - LLM: OpenAI models configured via `config/llm_config.yaml` and `OPENAI_API_KEY`.
- **Patterns**
  - Configuration-driven agent/task definitions (`config/*.yaml`).
  - Tool-based extension points for document processing and safe off-topic handling.

## Project Structure
```
c:\ERS\Agents\virtual_teacher
├─ config\
│  └─ llm_config.yaml
├─ content\
│  └─ hindi\chapter1.pdf
├─ knowledge\
│  └─ user_preference.txt
├─ logs\
│  └─ virtual_teacher.log
├─ src\
│  └─ virtual_teacher\
│     ├─ config\
│     │  ├─ agents.yaml
│     │  └─ tasks.yaml
│     ├─ llm\
│     │  ├─ indic_processor.py
│     │  └─ llm_manager.py
│     ├─ tools\
│     │  └─ custom_tool.py
│     ├─ utils\
│     │  ├─ audio_processor.py
│     │  ├─ document_processor.py
│     │  └─ file_manager.py
│     ├─ crew.py
│     └─ main.py
├─ tests\
│  └─ test_main_helpers.py
├─ Dockerfile
├─ pyproject.toml
└─ setup.sh
```
Key files:
- `src/virtual_teacher/main.py`: App entry point and Gradio UI.
- `src/virtual_teacher/crew.py`: crewAI composition.
- `src/virtual_teacher/config/agents.yaml` and `tasks.yaml`: Agent/task prompts and rules.
- `config/llm_config.yaml`: OpenAI model configuration and API settings.
- `Dockerfile`: Container build for deployment.

## Design Principles & Standards
- **Separation of concerns**: UI orchestration, OCR/document processing, and LLM/crew logic are separated into modules.
- **Configuration-first agent design**: Agent behavior is defined in YAML and injected into crewAI.
- **Tool-gated actions**: Document processing and user-detail handling are encapsulated as tools.
- **Logging**: App logs to console and a rotating file `logs/virtual_teacher.log`.
- **Error handling**: Exceptions are caught with friendly fallbacks, especially around OCR, file IO, and model calls.

## Technology Stack
- **Language**: Python 3.12
- **Frameworks/Libraries**
  - `crewai` for multi-agent orchestration
  - `gradio` for UI
  - `openai` + `litellm` for LLM access
  - OCR and document: `pytesseract`, `PyMuPDF`, `opencv-python`, `Pillow`
  - TTS: `gTTS`, `pyttsx3`
  - Indic NLP: `indic-nlp-library`, `indictrans`, `ai4bharat-transliteration`, `transformers`, `torch`
- **External services**
  - OpenAI API (LLM inference)
  - Google TTS via `gTTS` (network required)

## Prerequisites
- Python `>=3.12,<3.13`
- System packages for OCR (Linux):
  - `tesseract-ocr`, `tesseract-ocr-eng`, `tesseract-ocr-hin`
  - `libgl1`, `libglib2.0-0` (OpenCV dependencies)
- Environment variables:
  - `OPENAI_API_KEY` (required)
- Optional: `uv` for dependency management

## How to Build and Run
### Local (Python)
1. Create a virtual environment and install dependencies:
   ```bash
   pip install -e .
   ```
2. Set environment variables:
   ```bash
   setx OPENAI_API_KEY "your-api-key-here"
   ```
3. Run the app:
   ```bash
   python -m virtual_teacher.main
   ```
   The Gradio UI starts on `http://0.0.0.0:7860`.

### crewAI CLI
If you use crewAI's CLI:
```bash
crewai run
```

### Docker
```bash
docker build -t virtual-teacher .
docker run -p 7860:7860 -e OPENAI_API_KEY=your-api-key-here virtual-teacher
```

### Configuration
- LLM settings: `config/llm_config.yaml`
- Agent behavior: `src/virtual_teacher/config/agents.yaml`
- Task behavior: `src/virtual_teacher/config/tasks.yaml`
- Content: `content/<subject>/chapter< n >.pdf`

## Testing
- **Framework**: `unittest`
- **Tests**: `tests/test_main_helpers.py`
- Run:
  ```bash
  python -m unittest
  ```

## Deployment
- **Containerization**: Dockerfile provisions Tesseract OCR and runs `python -m virtual_teacher.main`.
- **Port**: 7860 (configurable via `GRADIO_SERVER_PORT` or `PORT`).
- **Environment**: Requires `OPENAI_API_KEY` and outbound network access for LLM + gTTS.

## Operational & Support Notes
- Logs are written to `logs/virtual_teacher.log` with rotation (5 MB, 3 backups).
- OCR results are stored in a temporary file and referenced via the `CURRENT_SESSION_CONTENT` env var for follow-up questions.
- If OCR extraction fails, the UI returns a friendly retry message.
- Common issues:
  - Missing `OPENAI_API_KEY` -> app fails at startup.
  - OCR language packs missing -> low/no text extraction.
  - Scanned PDFs without embedded text require OCR.

## Security Considerations
- **Secrets**: Use environment variables for `OPENAI_API_KEY`. Do not commit `.env` files with real keys.
- **Data handling**: Uploaded document text is stored in a temp file. No explicit retention policy or cleanup mechanism beyond process lifetime.
- **User data**: A tool exists to handle personal details, but no persistence is implemented.

## Contribution Guidelines
No explicit contribution or branching guidelines are defined in the repository. If contributions are needed, align with your team's standard review and branching practices.

## Assumptions & Limitations
- Chapter PDFs are expected in `content/<subject>/chapter< n >.pdf`; only chapters 1-10 are exposed in the UI.
- OCR accuracy depends on image quality and installed language packs.
- TTS uses `gTTS` by default; offline TTS is best-effort via `pyttsx3`.
- No persistent session store; document context is maintained via temp files only during a session.
