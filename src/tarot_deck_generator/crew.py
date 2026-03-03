"""Tarot Deck Generator - CrewAI crew definition."""

import json
import os
from pathlib import Path
from typing import Any

import yaml
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv

from tarot_deck_generator.models import CardSpec

# Load .env at import time - must happen before any OpenAI client is instantiated
load_dotenv()

_SETTINGS_ENV = "TAROT_CONFIG_PATH"
_CARDS_ENV = "TAROT_CARDS_PATH"


def _discover_project_root(start: Path) -> Path:
    """Discover project root by walking up for a pyproject.toml marker."""
    for candidate in [start, *start.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise FileNotFoundError(
        f"Could not discover project root from {start}. "
        "Set TAROT_CONFIG_PATH and TAROT_CARDS_PATH explicitly."
    )


def _resolve_resource_path(env_var: str, relative_path: str) -> Path:
    """Resolve resource path using env override first, then discovered project root."""
    env_value = os.getenv(env_var)
    if env_value:
        resolved = Path(env_value).expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(
                f"{env_var} points to a missing path: {resolved}"
            )
        return resolved

    project_root = _discover_project_root(Path(__file__).resolve().parent)
    resolved = (project_root / relative_path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(
            f"Required file not found at {resolved}. "
            f"Set {env_var} to override this path."
        )
    return resolved


def _load_settings() -> dict[str, Any]:
    """Load deck runtime settings from YAML config."""
    settings_path = _resolve_resource_path(_SETTINGS_ENV, "config/settings.yaml")
    with open(settings_path, encoding="utf-8") as file:
        return yaml.safe_load(file)


def _load_cards() -> list[CardSpec]:
    """Load and validate the bundled card specification."""
    cards_path = _resolve_resource_path(_CARDS_ENV, "data/cards.json")
    with open(cards_path, encoding="utf-8") as file:
        raw = json.load(file)
    return [CardSpec.model_validate(card) for card in raw]


@CrewBase
class TarotDeckGeneratorCrew:
    """Crew lifecycle for tarot deck generation.

    On instantiation, settings and card specs are loaded and validated.
    Agent/task methods wire YAML-defined components through CrewAI decorators.
    `crew()` assembles the executable Crew object, and `run()` is the CLI
    entrypoint used by `crewai run` for startup bootstrap.
    """

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self):
        self.settings = _load_settings()
        self.cards = _load_cards()

    @agent
    def style_bible_agent(self) -> Agent:
        from tarot_deck_generator.models import StyleBible

        return Agent(
            config=self.agents_config["style_bible_agent"],
            llm=self.settings["model"],
            output_json=StyleBible,
            verbose=True,
        )

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
        from tarot_deck_generator.models import StyleBible

        return Task(
            config=self.tasks_config["generate_style_bible_task"],
            output_json=StyleBible,
        )

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
    import argparse

    parser = argparse.ArgumentParser(
        description="Autonomous AI Tarot Deck Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  crewai run --style "dark gothic watercolor"
  crewai run --style "art nouveau" --mood "mystical" --palette "gold, ivory, deep teal"
  crewai run --style "ukiyo-e woodblock" --suit_wands "fire and dragons" --suit_cups "water and koi"
        """,
    )
    parser.add_argument(
        "--style",
        required=True,
        help='Art style descriptor (e.g. "dark gothic watercolor")',
    )
    parser.add_argument(
        "--mood",
        default="",
        help='Emotional tone (e.g. "mysterious, introspective")',
    )
    parser.add_argument(
        "--palette",
        default="",
        help='Color palette hints (e.g. "deep purples, blacks, silver")',
    )
    parser.add_argument(
        "--suit_wands",
        default="",
        help="Wands suit visual association override",
    )
    parser.add_argument(
        "--suit_cups",
        default="",
        help="Cups suit visual association override",
    )
    parser.add_argument(
        "--suit_swords",
        default="",
        help="Swords suit visual association override",
    )
    parser.add_argument(
        "--suit_pentacles",
        default="",
        help="Pentacles suit visual association override",
    )

    args = parser.parse_args()

    inputs = {
        "style": args.style,
        "mood": args.mood,
        "palette": args.palette,
        "suit_wands": args.suit_wands,
        "suit_cups": args.suit_cups,
        "suit_swords": args.suit_swords,
        "suit_pentacles": args.suit_pentacles,
    }

    print(f"Tarot Deck Generator - starting with style: '{args.style}'")
    crew_instance = TarotDeckGeneratorCrew()
    result = crew_instance.crew().kickoff(inputs=inputs)

    # Persist the Style Bible to disk
    output_dir = Path(crew_instance.settings["output_path"])
    output_dir.mkdir(parents=True, exist_ok=True)
    style_bible_path = output_dir / "style_bible.json"

    if hasattr(result, "json_dict") and result.json_dict:
        style_bible_data = result.json_dict
    elif hasattr(result, "pydantic") and result.pydantic:
        style_bible_data = result.pydantic.model_dump()
    else:
        style_bible_data = json.loads(str(result))

    with open(style_bible_path, "w", encoding="utf-8") as file:
        file.write(json.dumps(style_bible_data, indent=2))

    print(f"Style Bible written to {style_bible_path}")
    print("Generation complete.")
    return result
