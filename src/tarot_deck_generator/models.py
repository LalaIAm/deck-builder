"""Pydantic models for inter-agent data contracts."""

from typing import Literal, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class CardSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_id: str
    card_name: str
    arcana: Literal["major", "minor"]
    suit: Optional[Literal["wands", "cups", "swords", "pentacles"]] = None
    meaning_keywords: list[str]


# REQ-2 Style Bible schema: nested models for strict validation.


class GlobalStyleRules(BaseModel):
    """Six required keys per REQ-2 global_style_rules."""

    model_config = ConfigDict(extra="forbid")

    art_style: str
    mood: str
    lighting: str
    composition: str
    color_temperature: str
    rendering_technique: str


class SuitSystem(BaseModel):
    """Per-suit visual system: palette, lighting, motif, energy."""

    model_config = ConfigDict(extra="forbid")

    palette: str
    lighting: str
    motif: str
    energy: str


class SuitSystems(BaseModel):
    """Four suits required: wands, cups, swords, pentacles."""

    model_config = ConfigDict(extra="forbid")

    wands: SuitSystem
    cups: SuitSystem
    swords: SuitSystem
    pentacles: SuitSystem


class MajorArcanaRules(BaseModel):
    """Four keys; archetypal_realism must be true per REQ-2."""

    model_config = ConfigDict(extra="forbid")

    figure_style: str
    symbolism_approach: str
    background_complexity: str
    archetypal_realism: bool = True


class StyleBible(BaseModel):
    """Deck Style Bible per REQ-2: global rules, suit systems, major arcana, prompt prefix, avoid terms."""

    model_config = ConfigDict(extra="forbid")

    global_style_rules: GlobalStyleRules
    suit_systems: SuitSystems
    major_arcana_rules: MajorArcanaRules
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
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    card_id: str
    pass_: bool = Field(
        validation_alias=AliasChoices("pass", "passed"),
        serialization_alias="pass",
    )
    subscores: dict[str, float]
    rule_checks: dict[str, bool]
    reasons: list[str]
    prompt_patch: str
    failure_mode: str
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
