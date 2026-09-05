# tests/test_rule_ast.py
from amino.rules.ast import Literal, Variable, BinaryOp, UnaryOp, FunctionCall, RuleAST

def test_literal_node():
    n = Literal(value=42, type_name="Int")
    assert n.value == 42 and n.type_name == "Int"

def test_variable_node():
    n = Variable(name="credit_score", type_name="Int")
    assert n.name == "credit_score"

def test_binary_op_node():
    left = Variable("score", "Int")
    right = Literal(500, "Int")
    n = BinaryOp(op_token="=", left=left, right=right, type_name="Bool", fn=lambda l, r: l == r)
    assert n.op_token == "="

def test_unary_op_node():
    operand = Variable("active", "Bool")
    n = UnaryOp(op_token="not", operand=operand, type_name="Bool", fn=lambda v: not v)
    assert n.op_token == "not"

def test_function_call_node():
    n = FunctionCall(name="is_valid", args=[], type_name="Bool")
    assert n.name == "is_valid"

def test_rule_ast():
    root = Literal(True, "Bool")
    ast = RuleAST(root=root, return_type="Bool")
    assert ast.return_type == "Bool"
