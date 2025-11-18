from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from .tools.custom_tool import RecordUnknownQuestionTool, RecordUserDetailsTool

@CrewBase
class VirtualTeacher:
    """VirtualTeacher crew"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def teacher(self) -> Agent:
        return Agent(
            config=self.agents_config['teacher'],
            tools=[RecordUnknownQuestionTool(), RecordUserDetailsTool()],
            verbose=True
        )

    @task
    def teaching_task(self) -> Task:
        return Task(
            config=self.tasks_config['teaching_task']
        )

    @task
    def follow_up_task(self) -> Task:
        return Task(
            config=self.tasks_config['follow_up_task']
        )

    @crew
    def crew(self) -> Crew:
        """Creates the VirtualTeacher crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )