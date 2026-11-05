"""Le schéma JSON d'un rêve est valide et l'exemple le respecte."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "dream.schema.json").read_text(encoding="utf-8"))
EXAMPLE = json.loads((ROOT / "dream.example.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=Draft202012Validator.FORMAT_CHECKER)


def test_schema_is_valid() -> None:
    """Le schéma respecte la méta-spécification 2020-12."""
    Draft202012Validator.check_schema(SCHEMA)


def test_example_is_valid() -> None:
    """L'exemple documenté est conforme."""
    VALIDATOR.validate(EXAMPLE)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("status",), "en_cours"),
        (("emotion", "key"), "colere"),
        (("image", "ai_generated"), False),
        (("emotion", "score"), 1.5),
    ],
)
def test_invalid_values_are_rejected(path: tuple[str, ...], value: object) -> None:
    """Valeurs hors domaine refusées (statut, émotion, transparence IA, score)."""
    dream = copy.deepcopy(EXAMPLE)
    target = dream
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValidationError):
        VALIDATOR.validate(dream)


def test_failed_dream_without_results_is_valid() -> None:
    """Un rêve en échec, sans transcription ni image, reste représentable."""
    dream = copy.deepcopy(EXAMPLE)
    dream.update(status="failed", transcript=None, emotion=None, image=None)
    dream["error"] = {"code": "timeout", "step": "transcription", "retryable": True}
    VALIDATOR.validate(dream)
