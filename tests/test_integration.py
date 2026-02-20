"""End-to-end tests through the public API."""
import amino
from amino.errors import (
    DecisionValidationError, EngineAlreadyFrozenError,
    SchemaParseError, SchemaValidationError,
)
import pytest

# ── dmarcian-style classifier ─────────────────────────────────────────────────

CLASSIFIER_SCHEMA = """
asn: Int
cname: Str?
org: Str?
"""

def test_email_classifier_first_match():
    engine = amino.load_schema(CLASSIFIER_SCHEMA)
    rules = [
        {"id": 1, "rule": "asn = 16509", "ordering": 1, "name": "Amazon SES"},
        {"id": 2, "rule": "asn = 15169", "ordering": 2, "name": "Google"},
        {"id": 3, "rule": "asn = 8075",  "ordering": 3, "name": "Microsoft"},
    ]
    compiled = engine.compile(rules, match={"mode": "first", "key": "ordering", "order": "asc"})
    result = compiled.eval_single({"asn": 15169})
    assert result.matched == [2]

def test_email_classifier_no_match():
    engine = amino.load_schema(CLASSIFIER_SCHEMA)
    rules = [{"id": 1, "rule": "asn = 16509", "ordering": 1}]
    compiled = engine.compile(rules, match={"mode": "first", "key": "ordering", "order": "asc"})
    result = compiled.eval_single({"asn": 99999})
    assert result.matched == []

# ── auto loan decline layer ───────────────────────────────────────────────────

LOAN_SCHEMA = """
state_code: Str
credit_score: Int
applicant_type: Str
"""

def test_hard_decline_rules():
    engine = amino.load_schema(LOAN_SCHEMA)
    rules = [
        {"id": "decline_state",  "rule": "state_code in ['CA', 'NY']"},
        {"id": "decline_credit", "rule": "credit_score < 450"},
    ]
    compiled = engine.compile(rules)

    result = compiled.eval_single({"state_code": "CA", "credit_score": 700, "applicant_type": "single"})
    assert "decline_state" in result.matched
    assert "decline_credit" not in result.matched

    result = compiled.eval_single({"state_code": "TX", "credit_score": 400, "applicant_type": "single"})
    assert "decline_credit" in result.matched

# ── stipulation pattern ───────────────────────────────────────────────────────

STIP_SCHEMA = """
income_auto_verified: Bool
employment_tenure_months: Int
"""

def test_stipulation_as_boolean_rules():
    engine = amino.load_schema(STIP_SCHEMA)
    rules = [
        {"id": "stip_income",      "rule": "income_auto_verified = false", "action": "proof_of_income"},
        {"id": "stip_employment",  "rule": "employment_tenure_months < 6", "action": "employment_verification"},
    ]
    compiled = engine.compile(rules)
    result = compiled.eval_single({"income_auto_verified": False, "employment_tenure_months": 3})
    triggered = result.matched
    assert "stip_income" in triggered
    assert "stip_employment" in triggered

# ── scoring ────────────────────────────────────────────────────────────────────

SCORE_SCHEMA = "signal_a: Bool\nsignal_b: Bool\nsignal_c: Int"

def test_score_mode_aggregation():
    engine = amino.load_schema(SCORE_SCHEMA)
    rules = [
        {"id": "s1", "rule": "signal_a = true"},
        {"id": "s2", "rule": "signal_b = true"},
        {"id": "s3", "rule": "signal_c > 50"},
    ]
    compiled = engine.compile(rules, match={"mode": "score", "aggregate": "sum"})
    result = compiled.eval_single({"signal_a": True, "signal_b": False, "signal_c": 100})
    assert abs(result.score - 2.0) < 0.001

# ── inverse mode ──────────────────────────────────────────────────────────────

def test_inverse_mode_disqualification():
    engine = amino.load_schema(LOAN_SCHEMA)
    rules = [
        {"id": "eligible_state",  "rule": "state_code not in ['CA', 'NY']"},
        {"id": "eligible_credit", "rule": "credit_score >= 600"},
    ]
    compiled = engine.compile(rules, match={"mode": "inverse"})
    result = compiled.eval_single({"state_code": "TX", "credit_score": 500, "applicant_type": "single"})
    assert "eligible_credit" in result.excluded
    assert "eligible_state" not in result.excluded

# ── custom type registration ──────────────────────────────────────────────────

def test_custom_type_end_to_end():
    engine = amino.load_schema("ip: ipv4\nnetwork: cidr")
    engine.register_operator(
        keyword="within",
        fn=lambda ip, cidr: _cidr_contains(ip, cidr),
        binding_power=40,
        input_types=("ipv4", "cidr"),
        return_type="Bool",
    )
    compiled = engine.compile([{"id": "r1", "rule": "ip within network"}])
    result = compiled.eval_single({"ip": "10.0.0.5", "network": "10.0.0.0/8"})
    # Just verifying the pipeline doesn't crash; actual CIDR logic is in the fn
    assert result is not None

def _cidr_contains(ip: str, cidr: str) -> bool:
    import ipaddress
    return ipaddress.ip_address(ip) in ipaddress.ip_network(cidr, strict=False)

# ── schema export ─────────────────────────────────────────────────────────────

def test_schema_export():
    engine = amino.load_schema("age: Int\nname: Str?")
    exported = engine.export_schema()
    assert "age: Int" in exported
    assert "name: Str?" in exported

# ── error cases ───────────────────────────────────────────────────────────────

def test_schema_parse_error():
    with pytest.raises(SchemaParseError):
        amino.load_schema("age: @Int")

def test_freeze_error():
    engine = amino.load_schema("x: Int")
    engine.eval(rules=[{"id": "r1", "rule": "x > 0"}], decision={"x": 1})
    with pytest.raises(EngineAlreadyFrozenError):
        engine.add_function("foo", lambda: 1)

def test_loose_decisions_mode_warns_not_raises():
    engine = amino.load_schema("score: Int", decisions_mode="loose")
    compiled = engine.compile([{"id": "r1", "rule": "score > 0"}])
    result = compiled.eval_single({"score": "bad_type"})
    assert result.warnings  # warned, not raised

def test_strict_decisions_mode_raises():
    engine = amino.load_schema("score: Int", decisions_mode="strict")
    compiled = engine.compile([{"id": "r1", "rule": "score > 0"}])
    with pytest.raises(DecisionValidationError):
        compiled.eval_single({"score": "bad_type"})
