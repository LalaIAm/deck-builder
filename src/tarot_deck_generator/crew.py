"""Tarot Deck Generator - CrewAI crew definition."""

import json
from pathlib import Path

import yaml
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv

from tarot_deck_generator.models import CardSpec

# Load .env at import time - must happen before any OpenAI client is instantiated
load_dotenv()

# Resolve paths relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SETTINGS_PATH = _PROJECT_ROOT / "config" / "settings.yaml"
_CARDS_PATH = _PROJECT_ROOT / "data" / "cards.json"


def _load_settings() -> dict:
    with open(_SETTINGS_PATH, encoding="utf-8") as file:
        return yaml.safe_load(file)


def _load_cards() -> list[CardSpec]:
    with open(_CARDS_PATH, encoding="utf-8") as file:
        raw = json.load(file)
    return [CardSpec.model_validate(card) for card in raw]


@CrewBase
class TarotDeckGeneratorCrew:
    """CrewAI crew for autonomous tarot deck generation."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self):
        self.settings = _load_settings()
        self.cards = _load_cards()

    @agent
    def style_bible_agent(self) -> Agent:
        return Agent(config=self.agents_config["style_bible_agent"], verbose=True)

    @agent
    def concept_agent(self) -> Agent:
        return Agent(config=self.agents_config["concept_agent"], verbose=True)

    @agent
    def prompt_agent(self) -> Agent:
        return Agent(config=self.agents_config["prompt_agent"], verbose=True)

    @agent
    def image_agent(self) -> Agent:
        return Agent(config=self.agents_config["image_agent"], verbose=True)

    @agent
    def evaluator_agent(self) -> Agent:
        return Agent(config=self.agents_config["evaluator_agent"], verbose=True)

    @agent
    def repair_agent(self) -> Agent:
        return Agent(config=self.agents_config["repair_agent"], verbose=True)

    @agent
    def orchestrator_agent(self) -> Agent:
        return Agent(config=self.agents_config["orchestrator_agent"], verbose=True)

    @task
    def generate_style_bible_task(self) -> Task:
        return Task(config=self.tasks_config["generate_style_bible_task"])

    @task
    def generate_concept_task(self) -> Task:
        return Task(config=self.tasks_config["generate_concept_task"])

    @task
    def build_prompt_task(self) -> Task:
        return Task(config=self.tasks_config["build_prompt_task"])

    @task
    def generate_image_task(self) -> Task:
        return Task(config=self.tasks_config["generate_image_task"])

    @task
    def evaluate_image_task(self) -> Task:
        return Task(config=self.tasks_config["evaluate_image_task"])

    @task
    def repair_prompt_task(self) -> Task:
        return Task(config=self.tasks_config["repair_prompt_task"])

    @task
    def orchestrate_deck_task(self) -> Task:
        return Task(config=self.tasks_config["orchestrate_deck_task"])

    @crew
    def crew(self) -> Crew:
        """Assemble the crew with sequential process."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )


def run():
    """CLI entry point - invoked by `crewai run`."""
    print("Tarot Deck Generator - initialising crew...")
    crew_instance = TarotDeckGeneratorCrew()
    print(f"Loaded {len(crew_instance.cards)} cards from spec.")
    print(f"Settings: {crew_instance.settings}")
    print(
        "Crew initialised successfully. Full pipeline implementation "
        "in REQ-2 through REQ-7."
    )
    # Stub: full kickoff deferred to REQ-7
    # crew_instance.crew().kickoff()
