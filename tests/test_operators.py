import pytest
from amino.operators.registry import OperatorDef, OperatorRegistry
from amino.operators.standard import build_operator_registry
from amino.errors import OperatorConflictError

def test_register_and_lookup():
    reg = OperatorRegistry()
    reg.register(OperatorDef(symbol="~", kind="prefix", fn=lambda x: ~x,
        binding_power=50, input_types=("Int",), return_type="Int"))
    assert reg.lookup_by_types("~", ("Int",)) is not None

def test_type_dispatch():
    reg = OperatorRegistry()
    fn_list = lambda l, r: l in r
    fn_cidr = lambda l, r: False  # placeholder
    reg.register(OperatorDef(symbol="in", kind="infix", fn=fn_list,
        binding_power=40, input_types=("*", "List"), return_type="Bool"))
    reg.register(OperatorDef(symbol="in", kind="infix", fn=fn_cidr,
        binding_power=40, input_types=("ipv4", "cidr"), return_type="Bool"))
    assert reg.lookup_by_types("in", ("ipv4", "cidr")).fn is fn_cidr
    assert reg.lookup_by_types("in", ("Str", "List")).fn is fn_list

def test_conflict_same_types_raises():
    reg = OperatorRegistry()
    op = OperatorDef(symbol="=", kind="infix", fn=lambda l,r: l==r,
        binding_power=40, input_types=("*","*"), return_type="Bool")
    reg.register(op)
    with pytest.raises(OperatorConflictError):
        reg.register(op)

def test_standard_preset():
    reg = build_operator_registry("standard")
    assert reg.lookup_symbol("=") is not None
    assert reg.lookup_keyword("contains") is not None
    assert reg.lookup_keyword("and") is not None

def test_minimal_preset():
    reg = build_operator_registry("minimal")
    assert reg.lookup_keyword("and") is not None
    assert reg.lookup_symbol("=") is None

def test_explicit_list_preset():
    reg = build_operator_registry(["=", "!="])
    assert reg.lookup_symbol("=") is not None
    assert reg.lookup_symbol(">") is None

def test_binding_powers():
    reg = build_operator_registry("standard")
    assert reg.get_binding_power("or") == 10
    assert reg.get_binding_power("and") == 20
    assert reg.get_binding_power("not") == 30
    assert reg.get_binding_power("=") == 40
