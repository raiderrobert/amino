"""Run the shared conformance corpus in spec/conformance/ against this implementation.

Every host must pass these. Cases marked ``xfail`` in the corpus describe
required behaviour the reference implementation does not yet have; they are
strict expected failures so that fixing the gap forces the marker off.
"""

import json
import pathlib

import pytest

import amino
from amino.errors import AminoError, RuleParseError, TypeMismatchError

CORPUS = pathlib.Path(__file__).resolve().parents[2] / "spec" / "conformance"

# Which Python error classes satisfy each named validation rule.
ERROR_CLASSES: dict[str, tuple[type[Exception], ...]] = {
    "syntax": (RuleParseError,),
    "unknown_field": (RuleParseError,),
    "unknown_function": (RuleParseError,),
    "unknown_operator": (RuleParseError,),
    "type_mismatch": (TypeMismatchError, RuleParseError),
    "depth_exceeded": (RuleParseError,),
}


def _expand(expression: str) -> str:
    """Corpus macros for inputs too large to write literally."""
    if expression.startswith("@deep:"):
        depth = int(expression.split(":", 1)[1])
        return "(" * depth + "score > 1" + ")" * depth
    return expression


def _load(kind: str) -> list[tuple[str, dict, dict]]:
    out = []
    for path in sorted((CORPUS / kind).glob("*.json")):
        doc = json.loads(path.read_text())
        for case in doc["cases"]:
            out.append((path.stem, doc, case))
    return out


def _param(file: str, doc: dict, case: dict, label: str):
    marks = []
    # Only expected failures for this host apply; other hosts' reasons are
    # prefixed with their own name and this implementation must pass those.
    if case.get("xfail", "").startswith("python:"):
        marks.append(pytest.mark.xfail(reason=case["xfail"], strict=True))
    return pytest.param(doc, case, id=f"{file}::{label}", marks=marks)


_ENGINES: dict[int, amino.Engine] = {}


def _engine(doc: dict) -> amino.Engine:
    key = id(doc)
    if key not in _ENGINES:
        _ENGINES[key] = amino.load_schema(doc["schema"], operators=doc.get("operators", "standard"))
    return _ENGINES[key]


@pytest.mark.parametrize(
    "doc, case",
    [_param(f, d, c, c["name"]) for f, d, c in _load("parse")],
)
def test_parse(doc, case):
    engine = _engine(doc)
    text = _expand(case["expression"])
    if case["expect"] == "accept":
        expr = engine.parse(text)
        assert expr.ast.return_type == case["type"]
        return
    assert case["expect"] == "reject", case
    allowed = ERROR_CLASSES[case["error"]]
    with pytest.raises(AminoError) as info:
        engine.parse(text)
    assert isinstance(info.value, allowed), f"{case['error']} should raise one of {allowed}, got {type(info.value)}"


@pytest.mark.parametrize(
    "doc, case",
    [_param(f, d, c, c["expression"]) for f, d, c in _load("eval")],
)
def test_eval(doc, case):
    engine = _engine(doc)
    compiled = engine.compile([{"id": "q", "rule": case["expression"]}])
    matched = sorted(r.id for r in compiled.eval(doc["records"]) if "q" in r.matched)
    assert matched == case["matches"]
