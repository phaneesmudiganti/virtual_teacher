import re
import os
import logging
import logging.handlers
from pathlib import Path

import gradio as gr

from virtual_teacher.crew import VirtualTeacher
from virtual_teacher.tools.custom_tool import ProcessUploadedDocumentTool, AnswerFromDocumentTool
from virtual_teacher.utils.utils import clean_text_for_audio, generate_tts, load_pdf_content, load_pdf_from_path

logger = logging.getLogger(__name__)


def resolve_chapter_content(subject: str, chapter_number: int, content_source: str, pdf_file: str | Path | None) -> str:
    """
    Returns the chapter content based on selected content_source.
    Raises FileNotFoundError / ValueError for missing or unreadable inputs.
    """
    logger.info(f"Resolving content: subject={subject}, chapter={chapter_number}, source={content_source}")
    if content_source == "Upload PDF":
        if not pdf_file:
            raise FileNotFoundError("No PDF uploaded. Please upload a chapter PDF.")
        return load_pdf_from_path(pdf_file)
    elif content_source == "Camera Document (📱 NEW!)":
        # This will be handled by the OCR tools
        return ""
    # Default: Chapter from repo content
    return load_pdf_content(subject, chapter_number)


def is_specific_question(message: str) -> bool:
    """Check if the message contains a specific question or request"""
    if not message or len(message.strip()) < 3:
        return False

    message_lower = message.lower().strip()

    # Direct question indicators
    question_words = ['what', 'how', 'why', 'where', 'when', 'which', 'who', 'can you', 'could you',
                      'please', 'help me', 'explain', 'tell me', 'meaning', 'define', 'solve']

    # Check for question marks or request patterns
    has_question_mark = '?' in message
    has_request_words = any(word in message_lower for word in question_words)

    # Avoid generic greetings
    generic_greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'namaste']
    is_just_greeting = any(message_lower.startswith(greeting) for greeting in generic_greetings) and len(
        message_lower.split()) <= 3

    result = (has_question_mark or has_request_words) and not is_just_greeting
    logger.debug(f"is_specific_question={result}")
    return result


def clean_response_text(raw_response: str) -> str:
    """Clean the response text to remove any agent thinking patterns and verbose output"""
    if not raw_response:
        return ""

    # Convert to string if it's not already
    response_text = str(raw_response)

    # Remove "Thought:" sections and reasoning patterns
    lines = response_text.split('\n')
    cleaned_lines = []
    skip_line = False

    thought_patterns = [
        'thought:', 'i need to', 'i should', 'i must', 'i will', 'let me think',
        'my goal is', 'my task is', 'i am tasked', 'oh dear', 'it seems',
        'my apologies', 'i tried to', 'i made a mistake', 'i need to remember',
        'since the student', 'let me', 'i\'ll maintain', 'keeping in mind',
        'let\'s break down'
    ]

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        line_lower = line_clean.lower()

        # Skip lines that contain thinking patterns
        is_thought = any(pattern in line_lower for pattern in thought_patterns)

        # Skip lines that start with typical reasoning indicators
        starts_with_reasoning = any(line_lower.startswith(pattern) for pattern in [
            'thought:', 'i need', 'i should', 'i must', 'i will', 'let me',
            'my goal', 'my task', 'oh dear', 'it seems', 'since the', 'keeping'
        ])

        if not is_thought and not starts_with_reasoning:
            cleaned_lines.append(line_clean)

    # Join the cleaned lines
    cleaned = '\n'.join(cleaned_lines).strip()

    # Remove any remaining "Thought:" markers that might be embedded
    cleaned = re.sub(r'Thought:\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bThought\b[:\s]*', '', cleaned, flags=re.IGNORECASE)

    # Remove excessive whitespace and empty lines
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
    cleaned = cleaned.strip()

    # If we removed too much content, try a different approach
    if not cleaned or len(cleaned) < 20:
        # Try to extract only the last substantial paragraph
        paragraphs = [p.strip() for p in response_text.split('\n\n') if p.strip()]
        for paragraph in reversed(paragraphs):
            para_lower = paragraph.lower()
            if not any(pattern in para_lower for pattern in thought_patterns):
                if len(paragraph) > 20:
                    cleaned = paragraph
                    break

    # Final fallback
    if not cleaned or len(cleaned) < 10:
        return "I'm here to help you! Could you please repeat your question?"

    logger.debug(f"Cleaned response length={len(cleaned)}")
    return cleaned


def process_camera_document(pdf_file, student_question=""):
    """Process camera-captured or uploaded document using OCR"""
    if not pdf_file:
        return "Please upload a document first!", None

    try:
        logger.info("Processing camera document")
        doc_processor = ProcessUploadedDocumentTool()
        response_text = doc_processor._run(pdf_file, student_question if student_question.strip() else None)

        cleaned_text = clean_text_for_audio(response_text)
        audio_path = generate_tts(cleaned_text, lang='en')
        logger.info("Camera document processed successfully")
        return response_text, audio_path

    except Exception:
        logger.exception("Error processing document")
        return "I encountered an error processing your document.", None


def answer_document_question(question):
    """Answer questions about uploaded document"""
    if not question.strip():
        return "Please ask a question about your uploaded document!", None

    try:
        logger.info("Answering document question")
        answer_tool = AnswerFromDocumentTool()
        response_text = answer_tool._run(question)

        cleaned_text = clean_text_for_audio(response_text)
        audio_path = generate_tts(cleaned_text, lang='en')
        logger.info("Answered document question successfully")
        return response_text, audio_path

    except Exception:
        logger.exception("Error answering document question")
        return "I had trouble answering your question.", None

def start_session(subject, chapter_number, content_source, pdf_file):
    """Step 1: Greeting and asking what the student needs."""
    try:
        logger.info(f"Starting session: subject={subject}, chapter={chapter_number}, source={content_source}")
        # Handle camera document mode
        if content_source == "Camera Document (📱 NEW!)":
            if not pdf_file:
                return "Please upload your homework or textbook photo/PDF first!", None
            return process_camera_document(pdf_file, "")

        # Load chapter content for both Chapter and Upload PDF modes
        chapter_content = resolve_chapter_content(subject, chapter_number, content_source, pdf_file)

        # Create VirtualTeacher with appropriate agent
        vt = VirtualTeacher()
        crew = vt.crew()

        # For non-document modes, use only the chapter_teacher task
        if content_source != "Camera Document (📱 NEW!)":
            # Override the default agents to use only chapter_teacher
            crew.agents = [vt.chapter_teacher()]
            crew.tasks = [vt.teaching_task()]

        logger.info("Kicking off greeting task")
        greeting_result = crew.kickoff(inputs={
            "subject": subject,
            "chapter_number": chapter_number,
            "chapter_content": chapter_content
        })

        response_text = getattr(greeting_result, "raw", None)
        response_text = clean_response_text(response_text)

        if not response_text or "record_unknown_question" in str(response_text):
            response_text = f"Hello! Good morning! I'm your {subject} teacher. Would you like me to explain the chapter, give meanings of words, or answer a question?"

        cleaned_text = clean_text_for_audio(response_text)
        audio_path = generate_tts(cleaned_text, lang='hi' if subject.lower() == 'hindi' else 'en')
        logger.info("Session started successfully")
        return response_text, audio_path

    except FileNotFoundError as fnf:
        logger.exception("Content not found")
        return f"Sorry, I couldn't find your content. {fnf}", None
    except ValueError as ve:
        logger.exception("Unreadable content")
        return f"I found a file but couldn't read text from it. {ve}", None
    except Exception:
        logger.exception("Error in start_session")
        return "Oops! Something went wrong while starting the session. Please try again.", None

def smart_first_response(subject, chapter_number, content_source, pdf_file, student_query):
    """Handle first interaction when student asks a specific question"""
    try:
        logger.info("Handling smart first response")
        # Handle document-based questions
        if content_source == "Camera Document (📱 NEW!)":
            if not pdf_file:
                return "Please upload your homework or textbook first!", None
            return process_camera_document(pdf_file, student_query)

        # For chapter/PDF content with specific questions
        chapter_content = resolve_chapter_content(subject, chapter_number, content_source, pdf_file)

        vt = VirtualTeacher()
        crew = vt.crew()

        # Override to use chapter_teacher only
        crew.agents = [vt.chapter_teacher()]
        crew.tasks = [vt.smart_response_task()]

        logger.info("Kicking off smart response task")
        smart_result = crew.kickoff(inputs={
            "subject": subject,
            "chapter_number": chapter_number,
            "chapter_content": chapter_content,
            "student_query": student_query
        })

        response_text = getattr(smart_result, "raw", None)
        response_text = clean_response_text(response_text)

        if not response_text:
            response_text = "I'm here to help! Could you clarify your question?"

        cleaned_text = clean_text_for_audio(response_text)
        audio_path = generate_tts(cleaned_text, lang='hi' if subject.lower() == 'hindi' else 'en')
        logger.info("Smart response handled successfully")
        return response_text, audio_path

    except FileNotFoundError as fnf:
        logger.exception("Content not found")
        return f"Sorry, I couldn't find your content. {fnf}", None
    except ValueError as ve:
        logger.exception("Unreadable content")
        return f"I found a file but couldn't read text from it. {ve}", None
    except Exception:
        logger.exception("Error in smart_first_response")
        return "Oops! Something went wrong while answering your question. Please try again.", None

def follow_up(subject, chapter_number, content_source, pdf_file, student_query):
    """Step 2: Respond based on student input."""
    try:
        logger.info("Handling follow-up interaction")
        # Handle document-based questions
        if content_source == "Camera Document (📱 NEW!)":
            if not pdf_file:
                return "Please upload your homework or textbook first!", None
            # First process the document, then answer the question
            doc_response, _ = process_camera_document(pdf_file, student_query)
            if "I can help you with:" in doc_response:
                # Document was processed successfully, now answer the specific question
                return answer_document_question(student_query)
            else:
                return doc_response, None

        # Original functionality for chapters and uploaded PDFs
        chapter_content = resolve_chapter_content(subject, chapter_number, content_source, pdf_file)

        vt = VirtualTeacher()
        crew = vt.crew()

        # Override to use chapter_teacher only
        crew.agents = [vt.chapter_teacher()]
        crew.tasks = [vt.follow_up_task()]

        logger.info("Kicking off follow-up task")
        follow_up_result = crew.kickoff(inputs={
            "subject": subject,
            "chapter_number": chapter_number,
            "chapter_content": chapter_content,
            "student_query": student_query
        })

        response_text = getattr(follow_up_result, "raw", None)
        response_text = clean_response_text(response_text)

        if not response_text:
            response_text = "I'm here to help! Could you clarify your question?"

        cleaned_text = clean_text_for_audio(response_text)
        audio_path = generate_tts(cleaned_text, lang='hi' if subject.lower() == 'hindi' else 'en')
        logger.info("Follow-up handled successfully")
        return response_text, audio_path

    except FileNotFoundError as fnf:
        logger.exception("Content not found")
        return f"Sorry, I couldn't find your content. {fnf}", None
    except ValueError as ve:
        logger.exception("Unreadable content")
        return f"I found a file but couldn't read text from it. {ve}", None
    except Exception:
        logger.exception("Error in follow_up")
        return "Oops! Something went wrong while answering your question. Please try again.", None

def run():
    log_dir = Path.cwd() / "logs"
    os.makedirs(log_dir, exist_ok=True)
    stream_handler = logging.StreamHandler()
    file_handler = logging.handlers.RotatingFileHandler(
        str(log_dir / "virtual_teacher.log"), maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[stream_handler, file_handler]
    )
    logger.info("Virtual Teacher app starting")
    with gr.Blocks(title="Virtual Teacher - Your Learning Assistant") as teacher:
        gr.Markdown("### 📚 Virtual Teacher - Choose your learning mode!")
        gr.Markdown("**New!** Upload photos of your homework or textbook pages and get instant help!")

        with gr.Row():
            subject = gr.Dropdown(
                label="Subject",
                choices=["Hindi", "Math", "Science", "English", "Social Studies"],
                value="Math"
            )
            chapter_number = gr.Dropdown(
                label="Chapter Number",
                choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
                value="1",
                visible=True
            )
            content_source = gr.Radio(
                label="Learning Mode",
                choices=["Chapter", "Upload PDF", "Camera Document (📱 NEW!)"],
                value="Chapter"
            )
            pdf_file = gr.File(
                label="Upload your homework/textbook (PDF or Photo)",
                file_types=[".pdf", ".jpg", ".jpeg", ".png", ".bmp"],
                type="filepath",
                visible=False
            )

        # Enhanced message input with examples
        message = gr.Textbox(
            label="Your Question",
            placeholder="Ask me anything! e.g., 'What does this word mean?', 'Help me solve this problem', 'Explain this concept'",
            lines=2
        )
        ask_btn = gr.Button("🎓 Ask Teacher", variant="primary", size="lg")

        with gr.Row():
            response = gr.TextArea(label="Teacher's Response", lines=10)
            audio = gr.Audio(label="Voice Response", type="filepath")

        # Quick action buttons for document mode
        with gr.Row(visible=False) as quick_actions:
            explain_btn = gr.Button("📖 Explain this page", size="sm")
            solve_btn = gr.Button("🧮 Help solve problems", size="sm")
            words_btn = gr.Button("📝 Explain difficult words", size="sm")

        chat_md = gr.Markdown(label="Chat History")
        history_state = gr.State([])

        # --- Enhanced UI visibility logic ---
        def toggle_content_inputs(src_choice):
            show_chapter = (src_choice == "Chapter")
            show_upload = (src_choice == "Upload PDF")
            show_camera = (src_choice == "Camera Document (📱 NEW!)")
            show_quick = show_camera

            chapter_update = gr.update(visible=show_chapter)
            pdf_update = gr.update(
                visible=(show_upload or show_camera),
                value=None,
                label="Upload PDF" if show_upload else "Upload your homework/textbook (PDF or Photo)"
            )
            quick_update = gr.update(visible=show_quick)

            return chapter_update, pdf_update, quick_update

        content_source.change(
            fn=toggle_content_inputs,
            inputs=content_source,
            outputs=[chapter_number, pdf_file, quick_actions],
        )

        # --- Enhanced chat handler with smart question detection ---
        def chat(subject_v, chapter_v, src_v, pdf_v, message_v, history_v):
            try:
                if history_v is None:
                    history_v = []

                is_first_turn = (len(history_v) == 0)
                is_empty_message = (message_v is None or str(message_v).strip() == "")

                # Cast chapter to int safely
                chap_int = None
                if chapter_v is not None and str(chapter_v).isdigit():
                    chap_int = int(chapter_v)

                if is_first_turn and not is_empty_message and is_specific_question(message_v):
                    # Student asked a specific question in first interaction - answer directly
                    response_text, audio_path = smart_first_response(subject_v, chap_int or 1, src_v, pdf_v, message_v)
                elif is_first_turn or (is_empty_message and src_v != "Camera Document (📱 NEW!)"):
                    # First turn without specific question - show greeting
                    response_text, audio_path = start_session(subject_v, chap_int or 1, src_v, pdf_v)
                else:
                    # Follow-up interactions
                    response_text, audio_path = follow_up(subject_v, chap_int or 1, src_v, pdf_v, message_v)

                # Append the current turn
                display_message = message_v if message_v else "👋 Starting session..."
                history_v.append((display_message, response_text))

                # Build enhanced Markdown conversation
                md_lines = []
                for i, (user_msg, teacher_msg) in enumerate(history_v, start=1):
                    md_lines.append(f"### 💬 Turn {i}")
                    md_lines.append(f"**You:** {user_msg or ''}")
                    md_lines.append(f"**Teacher:** {teacher_msg or ''}")
                md = "\n\n---\n\n".join(md_lines)

                return response_text, audio_path, history_v, md, ""

            except Exception:
                logger.exception("Error in chat")
                return "An unexpected error occurred. Please refresh and try again.", None, history_v or [], "", ""

        # Quick action handlers
        def quick_action(action_type, subject_v, chapter_v, src_v, pdf_v, history_v):
            quick_messages = {
                "explain": "Please explain what's on this page",
                "solve": "Help me solve the problems on this page",
                "words": "Explain the difficult words on this page"
            }
            return chat(subject_v, chapter_v, src_v, pdf_v, quick_messages[action_type], history_v)

        # Event handlers
        ask_btn.click(
            fn=chat,
            inputs=[subject, chapter_number, content_source, pdf_file, message, history_state],
            outputs=[response, audio, history_state, chat_md, message],
        )

        # Quick action buttons
        explain_btn.click(
            fn=lambda s, c, src, p, h: quick_action("explain", s, c, src, p, h),
            inputs=[subject, chapter_number, content_source, pdf_file, history_state],
            outputs=[response, audio, history_state, chat_md, message],
        )

        solve_btn.click(
            fn=lambda s, c, src, p, h: quick_action("solve", s, c, src, p, h),
            inputs=[subject, chapter_number, content_source, pdf_file, history_state],
            outputs=[response, audio, history_state, chat_md, message],
        )

        words_btn.click(
            fn=lambda s, c, src, p, h: quick_action("words", s, c, src, p, h),
            inputs=[subject, chapter_number, content_source, pdf_file, history_state],
            outputs=[response, audio, history_state, chat_md, message],
        )

        # Enhanced examples section
        gr.Markdown("---")
        with gr.Accordion("📚 How to Use - Examples", open=False):
            gr.Markdown("""
            ### 🌟 Three Ways to Learn:

            **1. 📖 Chapter Mode** - Study specific textbook chapters
            - Select subject and chapter number
            - Ask questions about the chapter content

            **2. 📄 Upload PDF Mode** - Upload any PDF textbook
            - Upload a PDF file of your textbook
            - Ask questions about the content

            **3. 📱 Camera Document Mode (NEW!)** - Photo your homework!
            - Take a photo of your homework or textbook with your phone/tablet
            - Upload the image and ask questions like:
              - "What does this word mean?"
              - "Help me solve question number 3"
              - "Explain this math problem step by step"
              - "I don't understand this paragraph"

            ### 💡 Example Questions:
            - **Math**: "How do I solve 15 + 27?", "What is multiplication?"
            - **English**: "What does 'magnificent' mean?", "Help me write a story"
            - **Science**: "Why do plants need water?", "Explain photosynthesis"

            ### 🎯 Perfect for:
            - Homework help without judgment
            - Understanding difficult concepts
            - Learning at your own pace
            - Getting explanations in simple words
            """)

    teacher.launch(inbrowser=True, share=False)


if __name__ == "__main__":
    run()
