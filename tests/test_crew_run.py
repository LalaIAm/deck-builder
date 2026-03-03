"""Tests for run() CLI parsing and style_bible persistence (AC #38 / TASK-11)."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tarot_deck_generator.crew import OMITTED_INPUT_PLACEHOLDER, run


def _minimal_style_bible_dict():
    """Minimal REQ-2–shaped dict for style_bible persistence tests."""
    return {
        "global_style_rules": {
            "art_style": "test",
            "mood": "test",
            "lighting": "test",
            "composition": "test",
            "color_temperature": "test",
            "rendering_technique": "test",
        },
        "suit_systems": {
            "wands": {"palette": "p", "lighting": "l", "motif": "m", "energy": "e"},
            "cups": {"palette": "p", "lighting": "l", "motif": "m", "energy": "e"},
            "swords": {"palette": "p", "lighting": "l", "motif": "m", "energy": "e"},
            "pentacles": {"palette": "p", "lighting": "l", "motif": "m", "energy": "e"},
        },
        "major_arcana_rules": {
            "figure_style": "f",
            "symbolism_approach": "s",
            "background_complexity": "b",
            "archetypal_realism": True,
        },
        "prompt_prefix": "prefix",
        "avoid_terms": ["text", "watermark"],
    }


class TestRunCLIParsing:
    """run() CLI argument parsing."""

    def test_missing_style_exits_with_usage_error(self):
        """Without --style, argparse should exit with usage error (exit code 2)."""
        with patch.object(sys, "argv", ["crewai", "run", "--mood", "dark"]):
            with pytest.raises(SystemExit) as exc_info:
                run()
        assert exc_info.value.code == 2

    def test_required_style_parsed_and_passed_to_kickoff(self, tmp_path):
        """With --style (and optional args), kickoff receives inputs with all seven keys."""
        mock_kickoff = MagicMock(return_value=MagicMock(json_dict=_minimal_style_bible_dict()))
        mock_crew = MagicMock()
        mock_crew.kickoff = mock_kickoff
        mock_crew_instance = MagicMock()
        mock_crew_instance.settings = {"output_path": str(tmp_path)}
        mock_crew_instance.crew.return_value = mock_crew

        with patch.object(sys, "argv", ["crewai", "run", "--style", "gothic", "--mood", "mysterious"]):
            with patch("tarot_deck_generator.crew.TarotDeckGeneratorCrew", return_value=mock_crew_instance):
                run()

        mock_kickoff.assert_called_once()
        call_kw = mock_kickoff.call_args.kwargs
        assert "inputs" in call_kw
        inputs = call_kw["inputs"]
        assert inputs["style"] == "gothic"
        assert inputs["mood"] == "mysterious"
        assert inputs["palette"] == OMITTED_INPUT_PLACEHOLDER
        assert inputs["suit_wands"] == OMITTED_INPUT_PLACEHOLDER
        assert set(inputs.keys()) == {
            "style", "mood", "palette",
            "suit_wands", "suit_cups", "suit_swords", "suit_pentacles",
        }

    def test_unknown_args_ignored_no_failure(self, tmp_path):
        """Extra CLI args (e.g. crewai-injected) are ignored; run() does not fail."""
        mock_kickoff = MagicMock(return_value=MagicMock(json_dict=_minimal_style_bible_dict()))
        mock_crew = MagicMock()
        mock_crew.kickoff = mock_kickoff
        mock_crew_instance = MagicMock()
        mock_crew_instance.settings = {"output_path": str(tmp_path)}
        mock_crew_instance.crew.return_value = mock_crew

        with patch.object(sys, "argv", [
            "crewai", "run", "--verbose", "--style", "art nouveau",
            "--mood", "mystical", "--unknown-flag",
        ]):
            with patch("tarot_deck_generator.crew.TarotDeckGeneratorCrew", return_value=mock_crew_instance):
                run()

        inputs = mock_kickoff.call_args.kwargs["inputs"]
        assert inputs["style"] == "art nouveau"
        assert inputs["mood"] == "mystical"


class TestRunStyleBiblePersistence:
    """run() style bible write to output/style_bible.json."""

    def test_persists_from_json_dict(self, tmp_path):
        """When result has json_dict, that dict is written to output/style_bible.json."""
        data = _minimal_style_bible_dict()
        data["prompt_prefix"] = "custom prefix"
        mock_result = MagicMock()
        mock_result.json_dict = data
        mock_result.pydantic = None

        mock_kickoff = MagicMock(return_value=mock_result)
        mock_crew = MagicMock()
        mock_crew.kickoff = mock_kickoff
        mock_crew_instance = MagicMock()
        mock_crew_instance.settings = {"output_path": str(tmp_path)}
        mock_crew_instance.crew.return_value = mock_crew

        with patch.object(sys, "argv", ["crewai", "run", "--style", "x"]):
            with patch("tarot_deck_generator.crew.TarotDeckGeneratorCrew", return_value=mock_crew_instance):
                run()

        out_file = tmp_path / "style_bible.json"
        assert out_file.exists()
        with open(out_file, encoding="utf-8") as f:
            written = json.load(f)
        assert written["prompt_prefix"] == "custom prefix"
        assert written["global_style_rules"]["art_style"] == "test"
        assert written["avoid_terms"] == ["text", "watermark"]

    def test_persists_from_pydantic_model_dump(self, tmp_path):
        """When result has pydantic (no json_dict), model_dump() is written."""
        data = _minimal_style_bible_dict()
        mock_pydantic = MagicMock()
        mock_pydantic.model_dump.return_value = data
        mock_result = MagicMock()
        mock_result.json_dict = None
        mock_result.pydantic = mock_pydantic

        mock_kickoff = MagicMock(return_value=mock_result)
        mock_crew = MagicMock()
        mock_crew.kickoff = mock_kickoff
        mock_crew_instance = MagicMock()
        mock_crew_instance.settings = {"output_path": str(tmp_path)}
        mock_crew_instance.crew.return_value = mock_crew

        with patch.object(sys, "argv", ["crewai", "run", "--style", "x"]):
            with patch("tarot_deck_generator.crew.TarotDeckGeneratorCrew", return_value=mock_crew_instance):
                run()

        out_file = tmp_path / "style_bible.json"
        assert out_file.exists()
        with open(out_file, encoding="utf-8") as f:
            written = json.load(f)
        assert written["prompt_prefix"] == "prefix"

    def test_invalid_json_fallback_raises_value_error(self, tmp_path):
        """When result has no json_dict/pydantic and str(result) is not valid JSON, ValueError is raised."""
        mock_result = MagicMock()
        mock_result.json_dict = None
        mock_result.pydantic = None
        mock_result.__str__ = lambda self: "not valid json {"

        mock_kickoff = MagicMock(return_value=mock_result)
        mock_crew = MagicMock()
        mock_crew.kickoff = mock_kickoff
        mock_crew_instance = MagicMock()
        mock_crew_instance.settings = {"output_path": str(tmp_path)}
        mock_crew_instance.crew.return_value = mock_crew

        with patch.object(sys, "argv", ["crewai", "run", "--style", "x"]):
            with patch("tarot_deck_generator.crew.TarotDeckGeneratorCrew", return_value=mock_crew_instance):
                with pytest.raises(ValueError, match="not valid JSON"):
                    run()

    def test_persists_from_first_task_output_when_tasks_output_present(self, tmp_path):
        """When result has tasks_output (multi-task crew), use first task's output for style_bible.json."""
        style_bible_data = _minimal_style_bible_dict()
        style_bible_data["prompt_prefix"] = "from first task"
        first_task = MagicMock()
        first_task.json_dict = style_bible_data
        first_task.pydantic = None
        # Last task (e.g. orchestrate_deck_task) would have different output
        mock_result = MagicMock()
        mock_result.tasks_output = [first_task]
        mock_result.json_dict = {"card_results": "manifest"}  # last task output
        mock_result.pydantic = None

        mock_kickoff = MagicMock(return_value=mock_result)
        mock_crew = MagicMock()
        mock_crew.kickoff = mock_kickoff
        mock_crew_instance = MagicMock()
        mock_crew_instance.settings = {"output_path": str(tmp_path)}
        mock_crew_instance.crew.return_value = mock_crew

        with patch.object(sys, "argv", ["crewai", "run", "--style", "x"]):
            with patch("tarot_deck_generator.crew.TarotDeckGeneratorCrew", return_value=mock_crew_instance):
                run()

        out_file = tmp_path / "style_bible.json"
        assert out_file.exists()
        with open(out_file, encoding="utf-8") as f:
            written = json.load(f)
        assert written["prompt_prefix"] == "from first task"
        assert "card_results" not in written

    def test_output_dir_created_if_missing(self, tmp_path):
        """output_path directory is created if it does not exist."""
        output_subdir = tmp_path / "nested" / "output"
        assert not output_subdir.exists()

        mock_kickoff = MagicMock(return_value=MagicMock(json_dict=_minimal_style_bible_dict()))
        mock_crew = MagicMock()
        mock_crew.kickoff = mock_kickoff
        mock_crew_instance = MagicMock()
        mock_crew_instance.settings = {"output_path": str(output_subdir)}
        mock_crew_instance.crew.return_value = mock_crew

        with patch.object(sys, "argv", ["crewai", "run", "--style", "x"]):
            with patch("tarot_deck_generator.crew.TarotDeckGeneratorCrew", return_value=mock_crew_instance):
                run()

        assert output_subdir.exists()
        assert (output_subdir / "style_bible.json").exists()
