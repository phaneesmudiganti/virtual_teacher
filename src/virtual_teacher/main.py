from virtual_teacher.crew import VirtualTeacher
from virtual_teacher.utils.utils import clean_text_for_audio, generate_tts, load_pdf_content

def run(subject, chapter_number, student_query):
    chapter_content = load_pdf_content(subject, chapter_number)

    # Inject chapter content into agent and task config if needed
    teacher_crew = VirtualTeacher()
    result = teacher_crew.crew().kickoff(inputs={
        "subject": subject,
        "chapter_number": chapter_number,
        "chapter_content": chapter_content,
        "student_query": student_query
    })

    # Generate TTS
    cleaned_text = clean_text_for_audio(result.raw)
    audio_path = generate_tts(cleaned_text, lang='hi' if subject.lower() == 'hindi' else 'en')

    return result, audio_path

def launch_gradio():
    from gradio import Interface, Dropdown, Textbox, State, TextArea, Audio, Markdown

    def chat(subject, chapter_number, message, history=None):
        response, audio_path = run(subject, int(chapter_number), message)
        return response, audio_path, history, f"**User:** {message}\n\n**Teacher:** {response}"

    Interface(
        fn=chat,
        inputs=[
            Dropdown(label="Subject", choices=["Hindi", "Math", "Science"]),
            Dropdown(label="Chapter Number", choices=["1", "2", "3", "4", "5", "6"]),
            Textbox(label="Your message", placeholder="Type your question here..."),
            State()
        ],
        outputs=[
            TextArea(label="Response", lines=10),
            Audio(label="Voice Response", type="filepath"),
            State(),
            Markdown(label="Chat History")
        ],
        title="CBSE Grade 2 Subject Teacher",
        description="Select a subject and ask questions about the chapter!"
    ).launch(inbrowser=True)

if __name__ == "__main__":
    launch_gradio()