"""Tarot Deck Generator - CrewAI crew definition."""

import argparse
import json  # required for run() serialization path: _extract_style_bible_data, _write_style_bible
import os
from pathlib import Path
from typing import Any

import yaml
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv

from tarot_deck_generator.models import CardConcept, CardSpec, StyleBible

# Load .env at import time - must happen before any OpenAI client is instantiated
load_dotenv()

_SETTINGS_ENV = "TAROT_CONFIG_PATH"
_CARDS_ENV = "TAROT_CARDS_PATH"
STYLE_BIBLE_FILENAME = "style_bible.json"
# Index of generate_style_bible_task in crew.tasks (sequential order); used to read from tasks_output.
STYLE_BIBLE_TASK_INDEX = 0
# Shown in task prompt when an optional CLI arg is omitted; task description instructs agent to infer.
OMITTED_INPUT_PLACEHOLDER = "(not specified — infer from art style and mood)"


def _optional_input_or_placeholder(value: str) -> str:
    """Return value if non-empty, else OMITTED_INPUT_PLACEHOLDER (for CLI optional args)."""
    return value if value else OMITTED_INPUT_PLACEHOLDER


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
        project_root = _discover_project_root(Path(__file__).resolve().parent)
        output_dir = project_root / self.settings["output_path"].strip("/")
        self._style_bible_path = output_dir / STYLE_BIBLE_FILENAME
        self._style_bible: StyleBible | None = None

    @property
    def style_bible(self) -> StyleBible:
        """Load and cache StyleBible from output/style_bible.json. Raises if missing (REQ-3)."""
        if self._style_bible is None:
            if not self._style_bible_path.exists():
                raise FileNotFoundError(
                    "Style Bible not found at output/style_bible.json — run the Style Bible "
                    "generation step first (REQ-2)"
                )
            self._style_bible = StyleBible.model_validate(
                json.loads(self._style_bible_path.read_text(encoding="utf-8"))
            )
        return self._style_bible

    @agent
    def style_bible_agent(self) -> Agent:
        """Structured output is enforced at Task level (generate_style_bible_task.output_json)."""
        return Agent(
            config=self.agents_config["style_bible_agent"],
            llm=self.settings["model"],
            verbose=True,
        )

    @agent
    def concept_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["concept_agent"],
            llm=self.settings["model"],
            verbose=True,
        )

    @agent
    def prompt_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["prompt_agent"],
            llm=self.settings["model"],
            verbose=True,
        )

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
        """Task-level output_json (CrewAI convention) drives StyleBible; Agent does not use output_json."""
        return Task(
            config=self.tasks_config["generate_style_bible_task"],
            output_json=StyleBible,
        )

    @task
    def generate_concept_task(self) -> Task:
        return Task(
            config=self.tasks_config["generate_concept_task"],
            output_json=CardConcept,
            context=[self.generate_style_bible_task],
        )

    @task
    def build_prompt_task(self) -> Task:
        return Task(
            config=self.tasks_config["build_prompt_task"],
            context=[self.generate_concept_task],
        )

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


def _extract_style_bible_data(result: Any) -> dict[str, Any]:
    """Extract style bible dict from crew kickoff result (json_dict, pydantic, or JSON fallback)."""
    if hasattr(result, "json_dict") and result.json_dict:
        return result.json_dict
    if hasattr(result, "pydantic") and result.pydantic:
        return result.pydantic.model_dump()
    try:
        return json.loads(str(result))
    except json.JSONDecodeError as e:
        raise ValueError(
            "Style Bible output was not valid JSON; cannot persist to file. "
            "Ensure the style_bible_agent returns strict JSON only."
        ) from e


def _write_style_bible(style_bible_data: dict[str, Any], output_dir: Path) -> Path:
    """Create output_dir if needed and write style_bible.json; return path to written file."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / STYLE_BIBLE_FILENAME
    with open(path, "w", encoding="utf-8") as file:
        file.write(json.dumps(style_bible_data, indent=2))
    return path


def run():
    """CLI entry point - invoked by `crewai run`.

    Inputs:
        Taken from sys.argv (or crewai-injected args). Required: --style.
        Optional: --mood, --palette, --suit-wands, --suit-cups, --suit-swords,
        --suit-pentacles (underscore variants accepted). All are passed to
        crew.kickoff(inputs=...) as a dict with keys style, mood, palette,
        suit_wands, suit_cups, suit_swords, suit_pentacles (omitted options
        default to empty string).

    Outputs:
        Returns the crew kickoff result. Side effect: writes the Style Bible
        to {output_path}/style_bible.json (see config/settings.yaml).
        Creates the output directory if it does not exist.

    Failure modes:
        - SystemExit(2): --style not provided (argparse usage error).
        - ValueError: crew result was not valid JSON when using the fallback
          parse path (e.g. agent returned markdown instead of strict JSON).
        - FileNotFoundError: TAROT_CONFIG_PATH or TAROT_CARDS_PATH point to
          missing paths, or config/settings.yaml / data/cards.json not found.
    """
    parser = argparse.ArgumentParser(
        description="Autonomous AI Tarot Deck Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  crewai run --style "dark gothic watercolor"
  crewai run --style "art nouveau" --mood "mystical" --palette "gold, ivory, deep teal"
  crewai run --style "ukiyo-e woodblock" --suit-wands "fire and dragons" --suit-cups "water and koi"
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
        "--suit-wands",
        "--suit_wands",
        dest="suit_wands",
        default="",
        help="Wands suit visual association override",
    )
    parser.add_argument(
        "--suit-cups",
        "--suit_cups",
        dest="suit_cups",
        default="",
        help="Cups suit visual association override",
    )
    parser.add_argument(
        "--suit-swords",
        "--suit_swords",
        dest="suit_swords",
        default="",
        help="Swords suit visual association override",
    )
    parser.add_argument(
        "--suit-pentacles",
        "--suit_pentacles",
        dest="suit_pentacles",
        default="",
        help="Pentacles suit visual association override",
    )

    # parse_known_args() so CrewAI-injected CLI args (e.g. subcommands, flags) do not cause
    # "unrecognized arguments" errors; only our deck options are consumed.
    args, _ = parser.parse_known_args()

    inputs = {
        "style": args.style,
        "mood": _optional_input_or_placeholder(args.mood),
        "palette": _optional_input_or_placeholder(args.palette),
        "suit_wands": _optional_input_or_placeholder(args.suit_wands),
        "suit_cups": _optional_input_or_placeholder(args.suit_cups),
        "suit_swords": _optional_input_or_placeholder(args.suit_swords),
        "suit_pentacles": _optional_input_or_placeholder(args.suit_pentacles),
    }

    print(f"Tarot Deck Generator - starting with style: '{args.style}'")
    crew_instance = TarotDeckGeneratorCrew()
    result = crew_instance.crew().kickoff(inputs=inputs)

    # In sequential mode kickoff() returns the last task's output; the Style Bible
    # is produced by the first task (generate_style_bible_task). Use tasks_output[STYLE_BIBLE_TASK_INDEX].
    tasks_output = getattr(result, "tasks_output", None)
    first_task_output = (
        result.tasks_output[STYLE_BIBLE_TASK_INDEX]
        if tasks_output and len(tasks_output) > STYLE_BIBLE_TASK_INDEX
        else result
    )
    output_dir = Path(crew_instance.settings["output_path"])
    style_bible_data = _extract_style_bible_data(first_task_output)
    style_bible_path = _write_style_bible(style_bible_data, output_dir)

    print(f"Style Bible written to {style_bible_path}")
    print("Generation complete.")
    return result
