from .registry import OperatorDef, OperatorRegistry

_ALWAYS = {"or", "and", "not"}

_ALL_OPS: list[OperatorDef] = [
    OperatorDef(keyword="or",       fn=None, binding_power=10, kind="infix",  input_types=("Bool","Bool"), return_type="Bool"),
    OperatorDef(keyword="and",      fn=None, binding_power=20, kind="infix",  input_types=("Bool","Bool"), return_type="Bool"),
    OperatorDef(keyword="not",      fn=None, binding_power=30, kind="prefix", input_types=("Bool",),       return_type="Bool"),
    OperatorDef(keyword="in",       fn=lambda l,r: l in r,     binding_power=40, input_types=("*","List"),  return_type="Bool"),
    OperatorDef(keyword="not in",   fn=lambda l,r: l not in r, binding_power=40, input_types=("*","List"),  return_type="Bool"),
    OperatorDef(symbol="=",         fn=lambda l,r: l == r,     binding_power=40, input_types=("*","*"),     return_type="Bool"),
    OperatorDef(symbol="!=",        fn=lambda l,r: l != r,     binding_power=40, input_types=("*","*"),     return_type="Bool"),
    OperatorDef(symbol=">",         fn=lambda l,r: l > r,      binding_power=40, input_types=("*","*"),     return_type="Bool"),
    OperatorDef(symbol="<",         fn=lambda l,r: l < r,      binding_power=40, input_types=("*","*"),     return_type="Bool"),
    OperatorDef(symbol=">=",        fn=lambda l,r: l >= r,     binding_power=40, input_types=("*","*"),     return_type="Bool"),
    OperatorDef(symbol="<=",        fn=lambda l,r: l <= r,     binding_power=40, input_types=("*","*"),     return_type="Bool"),
    OperatorDef(keyword="contains", fn=lambda l,r: r in l,     binding_power=40, input_types=("Str","Str"), return_type="Bool"),
]
_BY_TOKEN = {(op.symbol or op.keyword): op for op in _ALL_OPS}


def build_operator_registry(preset: "str | list[str]") -> OperatorRegistry:
    if preset == "standard":
        ops = _ALL_OPS
    elif preset == "minimal":
        ops = [op for op in _ALL_OPS if (op.symbol or op.keyword) in _ALWAYS]
    elif isinstance(preset, list):
        enabled = set(preset) | _ALWAYS
        ops = [op for op in _ALL_OPS if (op.symbol or op.keyword) in enabled]
    else:
        raise ValueError(f"Unknown preset: {preset!r}")
    reg = OperatorRegistry()
    for op in ops:
        reg.register(op)
    return reg
