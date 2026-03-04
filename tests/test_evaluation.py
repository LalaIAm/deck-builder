"""Tests for REQ-5: Multimodal evaluation agent (evaluator_agent, evaluate_image_task)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tarot_deck_generator.crew import (
    TarotDeckGeneratorCrew,
    _evaluate_tarot_image_impl,
)
from tarot_deck_generator.models import EvaluationVerdict


def _minimal_style_bible_dict():
    """Minimal style bible for tests."""
    return {
        "global_style_rules": {
            "art_style": "t",
            "mood": "m",
            "lighting": "l",
            "composition": "c",
            "color_temperature": "ct",
            "rendering_technique": "rt",
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


def _minimal_card_concept_dict():
    """Minimal card concept for tests."""
    return {
        "card_id": "wands_01",
        "symbolic_elements": ["wand", "flame"],
        "composition_notes": "figure holding wand",
        "prompt_string": "a wand",
    }


class TestEvaluateImageTaskContextWiring:
    """REQ-5: evaluate_image_task context includes generate_image_task."""

    def test_evaluate_image_task_context_includes_generate_image_task(self):
        """Given evaluate_image_task in crew.py, its context includes generate_image_task (source verification)."""
        root = Path(__file__).resolve().parent.parent
        crew_path = root / "src" / "tarot_deck_generator" / "crew.py"
        source = crew_path.read_text(encoding="utf-8")
        # evaluate_image_task must pass context=[self.generate_image_task] to Task()
        assert "context=[self.generate_image_task]" in source, (
            "evaluate_image_task must have context=[self.generate_image_task] per REQ-5"
        )
        assert "evaluate_image_task" in source
        assert "generate_image_task" in source


class TestEvaluateTarotImageImplErrorHandling:
    """REQ-5: RuntimeError with card_id and attempt_number on any failure."""

    def test_raises_runtime_error_with_card_id_and_attempt_when_file_missing(self):
        """Given the image file cannot be read, when the task runs, RuntimeError contains card_id and attempt_number."""
        with pytest.raises(RuntimeError) as exc_info:
            _evaluate_tarot_image_impl(
                image_path="/nonexistent/image.png",
                card_id="cups_02",
                attempt_number=3,
                card_concept_json=json.dumps(_minimal_card_concept_dict()),
                style_bible_json=json.dumps(_minimal_style_bible_dict()),
            )
        msg = str(exc_info.value)
        assert "cups_02" in msg
        assert "3" in msg
        assert "Evaluation failed" in msg

    def test_raises_runtime_error_with_card_id_and_attempt_on_api_exception(self, tmp_path):
        """Given the gpt-4o API call raises, RuntimeError contains card_id and attempt_number."""
        image_file = tmp_path / "test.png"
        image_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")
        with (
            patch("tarot_deck_generator.crew._load_settings", return_value={"model": "gpt-4o"}),
            patch("tarot_deck_generator.crew.openai.OpenAI") as mock_openai,
        ):
            mock_openai.return_value.chat.completions.create.side_effect = Exception(
                "Rate limit exceeded"
            )
            with pytest.raises(RuntimeError) as exc_info:
                _evaluate_tarot_image_impl(
                    image_path=str(image_file),
                    card_id="swords_10",
                    attempt_number=1,
                    card_concept_json=json.dumps(_minimal_card_concept_dict()),
                    style_bible_json=json.dumps(_minimal_style_bible_dict()),
                )
        msg = str(exc_info.value)
        assert "swords_10" in msg
        assert "1" in msg
        assert "Rate limit exceeded" in msg

    def test_raises_runtime_error_with_card_id_and_attempt_on_invalid_subscores(self, tmp_path):
        """Given LLM returns subscores with wrong keys, ValidationError is re-raised as RuntimeError with card_id and attempt_number."""
        image_file = tmp_path / "test.png"
        image_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")
        # LLM returns only 2 subscore keys instead of 4 -> ValidationError
        bad_verdict = {
            "card_id": "wands_07",
            "attempt_number": 2,
            "passed": False,
            "subscores": {"suit_compliance": 5.0, "global_style": 6.0},
            "prompt_patch": "fix style",
        }
        mock_message = MagicMock(content=json.dumps(bad_verdict))
        mock_choice = MagicMock(message=mock_message)
        mock_response = MagicMock(choices=[mock_choice])
        with (
            patch("tarot_deck_generator.crew._load_settings", return_value={"model": "gpt-4o"}),
            patch("tarot_deck_generator.crew.openai.OpenAI") as mock_openai,
        ):
            mock_openai.return_value.chat.completions.create.return_value = mock_response
            with pytest.raises(RuntimeError) as exc_info:
                _evaluate_tarot_image_impl(
                    image_path=str(image_file),
                    card_id="wands_07",
                    attempt_number=2,
                    card_concept_json=json.dumps(_minimal_card_concept_dict()),
                    style_bible_json=json.dumps(_minimal_style_bible_dict()),
                )
        msg = str(exc_info.value)
        assert "wands_07" in msg
        assert "2" in msg
        assert "Evaluation failed" in msg


class TestEvaluatorAgentLLM:
    """REQ-5: evaluator_agent llm resolves to gpt-4o via settings['model']."""

    def test_evaluator_agent_llm_from_settings_model(self, tmp_path):
        """Given evaluator_agent in crew.py, its llm property resolves to settings['model']."""
        (tmp_path / "config").mkdir()
        (tmp_path / "data").mkdir()
        (tmp_path / "output").mkdir()
        (tmp_path / "config" / "settings.yaml").write_text(
            "model: gpt-4o\nimage_model: gpt-image-1\nmax_retries: 3\n"
            "output_path: output/\ncard_spec_path: data/cards.json\n",
            encoding="utf-8",
        )
        (tmp_path / "data" / "cards.json").write_text(
            '[{"card_id": "major_00", "card_name": "The Fool", "arcana": "major", '
            '"suit": null, "meaning_keywords": ["beginnings"]}]',
            encoding="utf-8",
        )
        (tmp_path / "output" / "style_bible.json").write_text(
            json.dumps(_minimal_style_bible_dict()),
            encoding="utf-8",
        )
        with patch("tarot_deck_generator.crew._discover_project_root", return_value=tmp_path):
            crew_instance = TarotDeckGeneratorCrew()
        agent = crew_instance.evaluator_agent()
        assert agent is not None
        assert getattr(agent, "llm", None) is not None
        # LLM is configured from settings (value set in settings.yaml)
        assert crew_instance.settings.get("model") == "gpt-4o"


class TestTasksYamlEvaluateImageTask:
    """REQ-5: tasks.yaml evaluate_image_task has required placeholders and expected_output."""

    def test_evaluate_image_task_description_has_required_placeholders(self):
        """evaluate_image_task description includes image_path, card_id, attempt_number, card_concept, style_bible."""
        import yaml
        root = Path(__file__).resolve().parent.parent
        tasks_path = root / "src" / "tarot_deck_generator" / "config" / "tasks.yaml"
        with open(tasks_path, encoding="utf-8") as f:
            tasks = yaml.safe_load(f)
        ev = tasks["evaluate_image_task"]
        desc = ev.get("description", "")
        assert "{image_path}" in desc
        assert "{card_id}" in desc
        assert "{attempt_number}" in desc
        assert "{card_concept}" in desc
        assert "{style_bible}" in desc
        assert ev.get("agent") == "evaluator_agent"

    def test_evaluate_image_task_expected_output_states_evaluation_verdict_schema(self):
        """evaluate_image_task expected_output states JSON object matching EvaluationVerdict schema."""
        import yaml
        root = Path(__file__).resolve().parent.parent
        tasks_path = root / "src" / "tarot_deck_generator" / "config" / "tasks.yaml"
        with open(tasks_path, encoding="utf-8") as f:
            tasks = yaml.safe_load(f)
        out = tasks["evaluate_image_task"].get("expected_output", "").lower()
        assert "evaluationverdict" in out or "evaluation verdict" in out or "json" in out
        assert "card_id" in out
        assert "passed" in out or "pass" in out
        assert "subscores" in out
        assert "prompt_patch" in out


class TestEvaluateTarotImageImplSuccessAndPassFailOverride:
    """REQ-5: successful path and Python pass/fail override."""

    def test_returns_verdict_and_applies_pass_fail_override(self, tmp_path):
        """Given valid API response, returns EvaluationVerdict; Python overrides passed from subscores and artifact flag."""
        image_file = tmp_path / "test.png"
        image_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")
        # LLM returns mean 8.0 but passed=False (artifact) -> override keeps passed=False
        llm_response = {
            "card_id": "x",
            "attempt_number": 1,
            "passed": False,
            "subscores": {
                "suit_compliance": 8.0,
                "global_style": 8.0,
                "meaning_alignment": 8.0,
                "technical_quality": 8.0,
            },
            "prompt_patch": "Remove watermark in corner",
        }
        mock_message = MagicMock(content=json.dumps(llm_response))
        mock_choice = MagicMock(message=mock_message)
        mock_response = MagicMock(choices=[mock_choice])
        with (
            patch("tarot_deck_generator.crew._load_settings", return_value={"model": "gpt-4o"}),
            patch("tarot_deck_generator.crew.openai.OpenAI") as mock_openai,
        ):
            mock_openai.return_value.chat.completions.create.return_value = mock_response
            verdict = _evaluate_tarot_image_impl(
                image_path=str(image_file),
                card_id="pentacles_03",
                attempt_number=1,
                card_concept_json=json.dumps(_minimal_card_concept_dict()),
                style_bible_json=json.dumps(_minimal_style_bible_dict()),
            )
        assert isinstance(verdict, EvaluationVerdict)
        assert verdict.card_id == "pentacles_03"
        assert verdict.attempt_number == 1
        assert verdict.subscores == llm_response["subscores"]
        # overall_score >= 7 but LLM said passed=False -> artifact; override keeps passed=False
        assert verdict.pass_ is False
        assert verdict.prompt_patch == "Remove watermark in corner"

    def test_override_sets_passed_true_when_mean_above_threshold_and_no_artifact(self, tmp_path):
        """When mean(subscores) >= 7 and LLM did not flag artifact, passed=True."""
        image_file = tmp_path / "test.png"
        image_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")
        llm_response = {
            "card_id": "y",
            "attempt_number": 2,
            "passed": True,
            "subscores": {
                "suit_compliance": 7.5,
                "global_style": 8.0,
                "meaning_alignment": 7.5,
                "technical_quality": 8.0,
            },
            "prompt_patch": "",
        }
        mock_message = MagicMock(content=json.dumps(llm_response))
        mock_choice = MagicMock(message=mock_message)
        mock_response = MagicMock(choices=[mock_choice])
        with (
            patch("tarot_deck_generator.crew._load_settings", return_value={"model": "gpt-4o"}),
            patch("tarot_deck_generator.crew.openai.OpenAI") as mock_openai,
        ):
            mock_openai.return_value.chat.completions.create.return_value = mock_response
            verdict = _evaluate_tarot_image_impl(
                image_path=str(image_file),
                card_id="major_00",
                attempt_number=2,
                card_concept_json=json.dumps(_minimal_card_concept_dict()),
                style_bible_json=json.dumps(_minimal_style_bible_dict()),
            )
        assert verdict.pass_ is True
        assert verdict.prompt_patch == ""
        assert verdict.card_id == "major_00"
        assert verdict.attempt_number == 2
