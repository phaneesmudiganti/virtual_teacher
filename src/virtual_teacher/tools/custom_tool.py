from crewai.tools import BaseTool

class RecordUnknownQuestionTool(BaseTool):
    name: str = "record_unknown_question"
    description: str = "Records an unknown question and guides the student back to the topic."

    def _run(self, question: str, subject: str) -> str:
        print(f"[Tool] Recording unknown question: '{question}' for subject '{subject}'")
        return f"That's an interesting thought! But let's focus on {subject}. What would you like to learn today?"

class RecordUserDetailsTool(BaseTool):
    name: str = "record_user_details"
    description: str = "Records user contact details and responds warmly."

    def _run(self, details: str) -> str:
        print(f"[Tool] Recording user details: '{details}'")
        return "Thank you for sharing your details! Let's continue learning."