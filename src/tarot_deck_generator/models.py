"""Pydantic models for inter-agent data contracts."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class CardSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_id: str
    card_name: str
    arcana: Literal["major", "minor"]
    suit: Optional[Literal["wands", "cups", "swords", "pentacles"]] = None
    meaning_keywords: list[str]


class StyleBible(BaseModel):
    model_config = ConfigDict(extra="forbid")

    global_style_rules: dict
    suit_systems: dict
    major_arcana_rules: dict
    prompt_prefix: str
    avoid_terms: list[str]


class CardConcept(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_id: str
    symbolic_elements: list[str]
    composition_notes: str
    prompt_string: str

    @field_validator("symbolic_elements")
    @classmethod
    def max_three_elements(cls, v):
        if len(v) > 3:
            raise ValueError(
                f"symbolic_elements must have at most 3 items, got {len(v)}"
            )
        return v


class EvaluationVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_id: str
    passed: bool
    subscores: dict[str, float]
    prompt_patch: str
    attempt_number: int


class CardResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_id: str
    card_name: str
    concept: CardConcept
    initial_prompt: str
    best_attempt_path: str
    total_attempts: int
    final_verdict: EvaluationVerdict