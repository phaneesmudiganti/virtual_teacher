from crewai.tools import BaseTool, tool

# class VirtualTeacherTools:
"""
A collection of custom tools for the Virtual Teacher Agent.
These tools handle specific interactions like recording unknown questions
or user details.
"""

@tool
def record_unknown_question(question: str, subject: str) -> str:
    """
    Records a question that is unrelated to the current chapter or subject.
    Returns a friendly message guiding the student back to the topic.

    Args:
        question (str): The question asked by the student.
        subject (str): The current subject being taught.
    """
    print(f"\n[Teacher Note]: Recording an unknown question: '{question}' for subject '{subject}'")
    return f"That's an interesting thought! But for now, let's focus on our {subject} chapter. What else would you like to know about it?"

@tool
def record_user_details(details: str) -> str:
    """
    Records user contact details like email or a request to stay in touch.
    Returns a warm, appreciative message.

    Args:
        details (str): The user details provided (e.g., email address, contact request).
    """
    print(f"\n[Teacher Note]: Recording user details: '{details}'")
    return "Thank you for sharing your details! It's lovely to connect. Let's learn more about our chapter now!"

# Initialize the tools. Instances of these tools will be passed to the agent.
# Note: The 'subject' for record_unknown_question will be implicitly handled by the agent's context
# or its ability to access its own 'backstory' subject.
# teacher_tools = VirtualTeacherTools()
