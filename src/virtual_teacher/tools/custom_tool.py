import os
import tempfile
import logging
from pathlib import Path
from typing import Optional

from crewai.tools import BaseTool

from virtual_teacher.utils.utils import DocumentProcessor

logger = logging.getLogger(__name__)


class RecordUnknownQuestionTool(BaseTool):
    name: str = "record_unknown_question"
    description: str = "Records an unknown question and guides the student back to the topic."

    def _run(self, question: str, subject: str) -> str:
        logger.info("Recording unknown question", extra={"question": question, "subject": subject})
        return f"That's an interesting thought! But let's focus on {subject}. What would you like to learn today?"


class RecordUserDetailsTool(BaseTool):
    name: str = "record_user_details"
    description: str = "Records user contact details and responds warmly."

    def _run(self, details: str) -> str:
        logger.info("Recording user details", extra={"details": details})
        return "Thank you for sharing your details! Let's continue learning."


class ProcessUploadedDocumentTool(BaseTool):
    name: str = "process_uploaded_document"
    description: str = "Processes an uploaded PDF or image document and extracts text content for teaching assistance."

    def _run(self, file_path: str, student_question: Optional[str] = None) -> str:
        try:
            # Create DocumentProcessor instance inside _run method to avoid BaseTool field issues
            processor = DocumentProcessor()

            # Determine file type and process accordingly
            file_ext = Path(file_path).suffix.lower()

            if file_ext == '.pdf':
                extracted_text = processor.process_pdf_with_ocr(file_path)
            elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                extracted_text = processor.extract_text_from_image(file_path)
            else:
                return "I can only help with PDF files and images (JPG, PNG, BMP). Please upload a supported file type."

            if not extracted_text.strip():
                return "I couldn't extract any text from this document. Could you try taking a clearer photo or check if the document is readable?"

            # Analyze content type
            content_info = processor.identify_content_type(extracted_text)

            # Create helpful response based on content analysis
            response = self._create_helpful_response(extracted_text, content_info, student_question)

            # Store processed content for follow-up questions
            self._store_session_content(extracted_text, content_info)

            return response

        except Exception:
            logger.exception("Error processing uploaded document")
            return "I encountered an error processing your document. Could you try uploading it again or ask me your question directly?"

    def _create_helpful_response(self, text: str, content_info: dict, student_question: Optional[str]) -> str:
        subject = content_info['subject']
        content_type = content_info['type']

        response = f"Great! I can see this is "

        if subject != 'unknown':
            response += f"a {subject.title()} "

        if content_type == 'homework':
            response += "homework assignment. "
        elif content_type == 'textbook':
            response += "textbook content. "
        else:
            response += "study material. "

        if student_question:
            response += f"You asked: '{student_question}'\n\n"

        response += "I can help you with:\n"
        response += "• Explaining difficult concepts\n"
        response += "• Breaking down complex problems\n"
        response += "• Providing step-by-step solutions\n"
        response += "• Explaining the meaning of difficult words\n\n"

        if content_info['has_questions']:
            response += "I noticed there are questions in your document. Would you like me to help you solve them step by step?\n\n"

        response += "What specific part would you like help with? You can ask me about any concept, word, or problem you see!"

        return response

    def _store_session_content(self, text: str, content_info: dict):
        """Store content for the current session"""
        # This would integrate with your session management system
        # For now, we'll use a simple approach
        session_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        session_file.write(f"CONTENT_TYPE: {content_info}\n\n")
        session_file.write(text)
        session_file.close()

        # Store file path in environment or session state
        os.environ['CURRENT_SESSION_CONTENT'] = session_file.name


class AnswerFromDocumentTool(BaseTool):
    name: str = "answer_from_document"
    description: str = "Answers specific questions about the uploaded document content."

    def _run(self, question: str) -> str:
        try:
            # Retrieve stored content
            session_content_path = os.environ.get('CURRENT_SESSION_CONTENT')
            if not session_content_path or not os.path.exists(session_content_path):
                return "I don't have any document content to reference. Please upload your homework or textbook first!"

            with open(session_content_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract the actual text content (skip the metadata)
            if "CONTENT_TYPE:" in content:
                content = content.split('\n\n', 1)[1] if '\n\n' in content else content

            # Analyze the question and provide contextual help
            response = self._provide_contextual_help(question, content)

            return response

        except Exception:
            logger.exception("Error accessing document content for answering")
            return "I had trouble accessing the document content. Could you ask your question again or re-upload the document?"

    def _provide_contextual_help(self, question: str, content: str) -> str:
        question_lower = question.lower()

        # Different types of help based on question type
        if any(word in question_lower for word in ['meaning', 'what does', 'define']):
            return self._explain_terms(question, content)
        elif any(word in question_lower for word in ['solve', 'answer', 'how to']):
            return self._provide_solution_guidance(question, content)
        elif any(word in question_lower for word in ['explain', 'why', 'how']):
            return self._provide_explanation(question, content)
        else:
            return self._general_help(question, content)

    def _explain_terms(self, question: str, content: str) -> str:
        return f"Let me help you understand the terms in your question!\n\n{question}\n\nBased on your document, I can explain this concept in simple words. What specific word or term would you like me to focus on?"

    def _provide_solution_guidance(self, question: str, content: str) -> str:
        return f"I'll help you solve this step by step!\n\n{question}\n\nLet me break this down into smaller, easier steps. First, let's understand what the question is asking, then we'll solve it together."

    def _provide_explanation(self, question: str, content: str) -> str:
        return f"Great question! Let me explain this concept clearly.\n\n{question}\n\nI'll use simple examples to help you understand this better."

    def _general_help(self, question: str, content: str) -> str:
        return f"I'm here to help with your question!\n\n{question}\n\nCould you tell me more specifically what you need help with? For example:\n• Do you need word meanings?\n• Should I solve a problem?\n• Do you want an explanation of a concept?"
