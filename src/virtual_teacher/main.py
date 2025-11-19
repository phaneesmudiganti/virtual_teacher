from pathlib import Path

from virtual_teacher.crew import VirtualTeacher
from virtual_teacher.utils.utils import clean_text_for_audio, generate_tts, load_pdf_content, load_pdf_from_path
import gradio as gr

def resolve_chapter_content(subject: str, chapter_number: int, content_source: str, pdf_file: str | Path | None) -> str:
    """
    Returns the chapter content based on selected content_source.
    Raises FileNotFoundError / ValueError for missing or unreadable inputs.
    """
    if content_source == "Upload PDF":
        if not pdf_file:
            raise FileNotFoundError("No PDF uploaded. Please upload a chapter PDF.")
        return load_pdf_from_path(pdf_file)
    # Default: Chapter from repo content
    return load_pdf_content(subject, chapter_number)

def start_session(subject, chapter_number, content_source, pdf_file):
    """Step 1: Greeting and asking what the student needs."""
    try:
        # chapter_content = resolve_chapter_content(subject, chapter_number, content_source, pdf_file)
        vt = VirtualTeacher()
        crew = vt.crew()

        # Run only the greeting task
        crew.tasks = [vt.teaching_task()]
        greeting_result = crew.kickoff(inputs={
            "subject": subject,
            "chapter_number": chapter_number,
            # "chapter_content": chapter_content
        })

        response_text = getattr(greeting_result, "raw", None)
        if not response_text or "record_unknown_question" in str(response_text):
            response_text = f"Hello! Good morning! I'm your {subject} teacher. Would you like me to explain the chapter, give meanings of words, or answer a question?"

        cleaned_text = clean_text_for_audio(response_text)
        audio_path = generate_tts(cleaned_text, lang='hi' if subject.lower() == 'hindi' else 'en')
        return response_text, audio_path
    except FileNotFoundError as fnf:
        print(f"[Content not found] {fnf}")
        return f"Sorry, I couldn't find your content. {fnf}", None
    except ValueError as ve:
        print(f"[Unreadable content] {ve}")
        return f"I found a file but couldn't read text from it. {ve}", None
    except Exception as e:
        print(f"[Error in start_session]: {e}")
        return "Oops! Something went wrong while starting the session. Please try again.", None


def follow_up(subject, chapter_number, content_source, pdf_file, student_query):
    """Step 2: Respond based on student input."""
    try:
        chapter_content = resolve_chapter_content(subject, chapter_number, content_source, pdf_file)
        vt = VirtualTeacher()
        crew = vt.crew()

        # Run only the follow-up task
        crew.tasks = [vt.follow_up_task()]
        follow_up_result = crew.kickoff(inputs={
            "subject": subject,
            "chapter_number": chapter_number,
            "chapter_content": chapter_content,
            "student_query": student_query
        })

        response_text = getattr(follow_up_result, "raw", None)
        if not response_text:
            response_text = "I'm here to help! Could you clarify your question?"

        cleaned_text = clean_text_for_audio(response_text)
        audio_path = generate_tts(cleaned_text, lang='hi' if subject.lower() == 'hindi' else 'en')
        return response_text, audio_path
    except FileNotFoundError as fnf:
        print(f"[Content not found] {fnf}")
        return f"Sorry, I couldn't find your content. {fnf}", None
    except ValueError as ve:
        print(f"[Unreadable content] {ve}")
        return f"I found a file but couldn't read text from it. {ve}", None
    except Exception as e:
        print(f"[Error in follow_up]: {e}")
        return "Oops! Something went wrong while answering your question. Please try again.", None



def run():
    with gr.Blocks(title="CBSE Grade 2 Subject Teacher") as demo:
        gr.Markdown("### Select a subject, choose content source (chapter or PDF), and ask questions about the chapter!")

        with gr.Row():
            subject = gr.Dropdown(label="Subject", choices=["Hindi", "Math", "Science"], value="Hindi")
            chapter_number = gr.Dropdown(label="Chapter Number", choices=["1", "2", "3", "4", "5", "6"], value="1", visible=True)
            content_source = gr.Radio(label="Content Source", choices=["Chapter", "Upload PDF"], value="Chapter")
            pdf_file = gr.File(label="Upload PDF", file_types=[".pdf"], type="filepath", visible=False)

        message = gr.Textbox(label="Your message", placeholder="Type your question here...")
        ask_btn = gr.Button("Ask")

        with gr.Row():
            response = gr.TextArea(label="Response", lines=10)
            audio = gr.Audio(label="Voice Response", type="filepath")

        chat_md = gr.Markdown(label="Chat History")
        history_state = gr.State([])

        # --- Conditional UI visibility based on Content Source selection ---
        def toggle_content_inputs(src_choice):
            show_chapter = (src_choice == "Chapter")
            show_upload = (src_choice == "Upload PDF")
            # Optionally clear the opposite input to avoid stale values
            chapter_update = gr.update(visible=show_chapter)  # keep current value
            pdf_update = gr.update(visible=show_upload, value=None)  # clear file when switching
            return chapter_update, pdf_update

        content_source.change(
            fn=toggle_content_inputs,
            inputs=content_source,
            outputs=[chapter_number, pdf_file],
        )

        # --- Chat handler: greeting vs follow-up, using selected content source ---
        def chat(subject_v, chapter_v, src_v, pdf_v, message_v, history_v):
            try:
                # Ensure history as list
                if history_v is None:
                    history_v = []

                # Decide greeting vs follow-up:
                is_first_turn = (len(history_v) == 0)
                is_empty_message = (message_v is None or str(message_v).strip() == "")

                # Cast chapter to int safely (in Chapter mode only)
                chap_int = None
                if chapter_v is not None and str(chapter_v).isdigit():
                    chap_int = int(chapter_v)

                if is_first_turn or is_empty_message:
                    response_text, audio_path = start_session(subject_v, chap_int or 1, src_v, pdf_v)
                else:
                    response_text, audio_path = follow_up(subject_v, chap_int or 1, src_v, pdf_v, message_v)

                # Append the current turn
                history_v.append((message_v, response_text))

                # Build Markdown conversation
                md_lines = []
                for i, (user_msg, teacher_msg) in enumerate(history_v, start=1):
                    md_lines.append(f"**Turn {i}**")
                    md_lines.append(f"**User:** {user_msg or ''}\n\n**Teacher:** {teacher_msg or ''}")
                md = "\n\n---\n\n".join(md_lines)

                return response_text, audio_path, history_v, md

            except Exception as e:
                print(f"[Error in chat]: {e}")
                return "An unexpected error occurred. Please refresh and try again.", None, history_v or [], ""

        ask_btn.click(
            fn=chat,
            inputs=[subject, chapter_number, content_source, pdf_file, message, history_state],
            outputs=[response, audio, history_state, chat_md],
        )

    demo.launch(inbrowser=True)

if __name__ == "__main__":
    run()