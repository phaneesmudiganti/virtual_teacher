from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from .tools.custom_tool import record_unknown_question, record_user_details
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class VirtualTeacher():
    """VirtualTeacher crew"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def teacher(self) -> Agent:
        return Agent(
            config=self.agents_config['teacher'], # type: ignore[index]
            tools=[
                record_unknown_question,
                record_user_details
            ],
            verbose=True
        )

    @task
    def teaching_task(self) -> Task:
        return Task(
            config=self.tasks_config['teaching_task'] # type: ignore[index]
        )

    # @task
    # def follow_up_task(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['follow_up_task'] # type: ignore[index]
    # )

    @crew
    def crew(self) -> Crew:
        """Creates the VirtualTeacher crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True
        )
