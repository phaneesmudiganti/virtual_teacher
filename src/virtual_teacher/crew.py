import logging
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from .tools.custom_tool import RecordUnknownQuestionTool, RecordUserDetailsTool, ProcessUploadedDocumentTool, AnswerFromDocumentTool
from .llm.llm_manager import get_llm_manager

logger = logging.getLogger(__name__)

@CrewBase
class VirtualTeacher:
    """Enhanced VirtualTeacher crew with content-source-specific agents"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self):
        self.llm_manager = get_llm_manager()

    @agent
    def chapter_teacher(self) -> Agent:
        """Agent for Chapter and Upload PDF modes - NO document processing tools"""
        agent = Agent(
            config=self.agents_config['chapter_teacher'],
            tools=[
                RecordUnknownQuestionTool(),
                RecordUserDetailsTool()
            ],
            llm=self.llm_manager.get_llm("primary"),  # Use OpenAI LLM
            verbose=False,
            max_iter=3  # Prevent infinite loops
        )
        logger.info("Initialized chapter_teacher agent")
        return agent

    @agent
    def simple_greeter(self) -> Agent:
        """Agent for simple greeting tasks - NO tools to avoid confusion"""
        agent = Agent(
            config=self.agents_config['simple_greeter'],
            tools=[],  # NO TOOLS - just greet and respond
            llm=self.llm_manager.get_llm("primary"),
            verbose=False,
            max_iter=1  # Only one iteration needed for greetings
        )
        logger.info("Initialized simple_greeter agent")
        return agent

    @agent
    def document_teacher(self) -> Agent:
        """Agent for Camera Document mode - WITH document processing tools"""
        agent = Agent(
            config=self.agents_config['document_teacher'],
            tools=[
                RecordUnknownQuestionTool(),
                RecordUserDetailsTool(),
                ProcessUploadedDocumentTool(),
                AnswerFromDocumentTool()
            ],
            llm=self.llm_manager.get_llm("primary"),  # Use OpenAI LLM
            verbose=False,
            max_iter=5  # Prevent infinite loops
        )
        logger.info("Initialized document_teacher agent")
        return agent

    @task
    def document_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['document_analysis_task']
        )

    @task
    def teaching_task(self) -> Task:
        return Task(
            config=self.tasks_config['teaching_task'],
            agent=self.simple_greeter()  # Use simple greeter without tools
        )

    @task
    def smart_response_task(self) -> Task:
        task = Task(
            config=self.tasks_config['smart_response_task']
        )
        task.agent = self.chapter_teacher()
        return task

    @task
    def follow_up_task(self) -> Task:
        task = Task(
            config=self.tasks_config['follow_up_task']
        )
        task.agent = self.chapter_teacher()
        return task

    @crew
    def crew(self) -> Crew:
        """Creates the default crew"""
        crew = Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )
        logger.info("Crew created")
        return crew
