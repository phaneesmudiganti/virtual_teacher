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
            llm=self.llm_manager.get_llm("primary"),  # Use Ollama LLM
            verbose=False
        )
        logger.info("Initialized chapter_teacher agent")
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
            llm=self.llm_manager.get_llm("primary"),  # Use Ollama LLM
            verbose=False
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
            config=self.tasks_config['teaching_task']
        )

    @task
    def smart_response_task(self) -> Task:
        return Task(
            config=self.tasks_config['smart_response_task']
        )

    @task
    def follow_up_task(self) -> Task:
        return Task(
            config=self.tasks_config['follow_up_task']
        )

    @crew
    def crew(self) -> Crew:
        """Creates the default crew"""
        c = Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False
        )
        logger.info("Crew created")
        return c
