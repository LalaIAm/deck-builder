"""Tests for REQ-4: Image generation agent and generate_image_task."""

import base64
import json
from unittest.mock import MagicMock, patch

import pytest

from tarot_deck_generator.crew import (
    TarotDeckGeneratorCrew,
    _generate_tarot_image_impl,
)


# Minimal 1x1 PNG (valid PNG bytes)
_MINIMAL_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="


class TestGenerateTarotImageTool:
    """generate_tarot_image_tool: API call, save PNG, return path, error handling."""

    def test_returns_path_and_writes_png(self, tmp_path, monkeypatch):
        """On successful API response, returns path and writes valid PNG to output/images/."""
        monkeypatch.chdir(tmp_path)
        mock_response = MagicMock()
        mock_response.data = [MagicMock(b64_json=_MINIMAL_PNG_B64)]
        mock_generate = MagicMock(return_value=mock_response)
        mock_client = MagicMock()
        mock_client.images.generate = mock_generate

        with patch("tarot_deck_generator.crew.openai.OpenAI", return_value=mock_client):
            result = _generate_tarot_image_impl(
                prompt_string="test prompt",
                card_id="seven_of_wands",
                attempt_number=2,
            )

        assert result == "output/images/seven_of_wands_attempt_2.png"
        out_file = tmp_path / "output" / "images" / "seven_of_wands_attempt_2.png"
        assert out_file.exists()
        assert out_file.read_bytes() == base64.b64decode(_MINIMAL_PNG_B64)
        mock_generate.assert_called_once_with(
            model="gpt-image-1",
            prompt="test prompt",
            size="1024x1536",
            n=1,
            response_format="b64_json",
        )

    def test_creates_output_images_directory_if_missing(self, tmp_path, monkeypatch):
        """When output/images/ does not exist, directory is created before writing."""
        monkeypatch.chdir(tmp_path)
        assert not (tmp_path / "output" / "images").exists()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(b64_json=_MINIMAL_PNG_B64)]
        with patch("tarot_deck_generator.crew.openai.OpenAI") as mock_openai:
            mock_openai.return_value.images.generate.return_value = mock_response
            _generate_tarot_image_impl(
                prompt_string="x", card_id="test_card", attempt_number=1
            )
        assert (tmp_path / "output" / "images").is_dir()
        assert (tmp_path / "output" / "images" / "test_card_attempt_1.png").exists()

    def test_raises_runtime_error_with_card_id_and_attempt_on_api_failure(
        self, tmp_path, monkeypatch
    ):
        """When API raises, RuntimeError contains both card_id and attempt_number."""
        monkeypatch.chdir(tmp_path)
        with patch("tarot_deck_generator.crew.openai.OpenAI") as mock_openai:
            mock_openai.return_value.images.generate.side_effect = Exception(
                "API quota exceeded"
            )
            with pytest.raises(RuntimeError) as exc_info:
                _generate_tarot_image_impl(
                    prompt_string="test",
                    card_id="test_card",
                    attempt_number=2,
                )
        msg = str(exc_info.value)
        assert "test_card" in msg
        assert "2" in msg
        assert "API quota exceeded" in msg


def _minimal_style_bible_dict():
    """Minimal REQ-2–shaped dict for style_bible (matches test_crew_run)."""
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


class TestImageAgentAndTaskWiring:
    """REQ-4: image_agent and generate_image_task config and context."""

    def test_crew_instantiates_and_image_agent_has_llm(self, tmp_path):
        """Crew loads; image_agent exists and uses image_model from settings."""
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
        agent = crew_instance.image_agent()
        assert agent is not None
        assert getattr(agent, "llm", None) is not None

    def test_tasks_yaml_has_generate_image_task_with_placeholders(self):
        """generate_image_task in tasks.yaml references prompt_string, card_id, attempt_number."""
        import yaml
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        tasks_path = root / "src" / "tarot_deck_generator" / "config" / "tasks.yaml"
        with open(tasks_path, encoding="utf-8") as f:
            tasks = yaml.safe_load(f)
        gen = tasks["generate_image_task"]
        desc = gen.get("description", "")
        assert "{prompt_string}" in desc
        assert "{card_id}" in desc
        assert "{attempt_number}" in desc
        assert gen.get("agent") == "image_agent"
        out = gen.get("expected_output", "")
        assert "file path" in out.lower()
        assert "json" not in out.lower() or "no json" in out.lower()
