"""Tests for Advanced Schema Features - Type System Extensions.

These tests use parametrize decorators following the project's test patterns.
They define the expected behavior for:
1. Function declarations
2. Struct definitions
3. List types
4. Enhanced type constraints
"""

import pytest

import amino
from amino.rules.parser import parse_rule
from amino.schema.parser import parse_schema
from amino.schema.types import SchemaType
from amino.utils.errors import SchemaParseError


@pytest.mark.parametrize(
    "schema_content,expected_functions,should_raise,expected_error",
    [
        (
            """
            amount: Int
            calculate_tax: (amount: Int, rate: Float) -> float
            """,
            [("calculate_tax", [("amount", SchemaType.int), ("rate", SchemaType.float)], SchemaType.float)],
            False,
            None,
        ),
        (
            """
            process_data: (input: Str, count: Int) -> str
            validate_input: (flag: Bool) -> bool
            """,
            [
                ("process_data", [("input", SchemaType.str), ("count", SchemaType.int)], SchemaType.str),
                ("validate_input", [("flag", SchemaType.bool)], SchemaType.bool),
            ],
            False,
            None,
        ),
        (
            """
            struct person {
                name: Str,
                age: Int
            }
            validate_person: (p: person) -> bool
            """,
            [("validate_person", [("p", SchemaType.custom)], SchemaType.bool)],
            False,
            None,
        ),
        ("invalid_func: (param: Int) bool", [], True, "Expected"),
    ],
)
def test_function_declarations(schema_content, expected_functions, should_raise, expected_error):
    """Test function declaration parsing with various scenarios."""
    if should_raise:
        with pytest.raises(SchemaParseError) as excinfo:
            parse_schema(schema_content)
        assert expected_error in str(excinfo.value)
    else:
        ast = parse_schema(schema_content)
        assert len(ast.functions) == len(expected_functions)

        for i, (expected_name, expected_params, expected_output) in enumerate(expected_functions):
            func = ast.functions[i]
            assert func.name == expected_name
            assert len(func.parameters) == len(expected_params)
            for j, (param_name, param_type) in enumerate(expected_params):
                assert func.parameters[j].name == param_name
                assert func.parameters[j].param_type == param_type
            assert func.output_type == expected_output


@pytest.mark.parametrize(
    "rule_content,schema_content,expected_functions,expected_variables",
    [
        (
            "calculate_tax(amount, tax_rate) > 100.0",
            """
            amount: Int
            tax_rate: Float
            calculate_tax: (amt: Int, rate: Float) -> float
            """,
            ["calculate_tax"],
            ["amount", "tax_rate"],
        ),
        (
            "validate_data(user_input, threshold) and result > 0",
            """
            user_input: Str
            threshold: Int
            result: Float
            validate_data: (input: Str, thresh: Int) -> float
            """,
            ["validate_data"],
            ["user_input", "threshold", "result"],
        ),
    ],
)
def test_function_usage_in_rules(rule_content, schema_content, expected_functions, expected_variables):
    """Test using declared functions in rules."""
    schema_ast = parse_schema(schema_content)
    rule_ast = parse_rule(rule_content, schema_ast)

    for func_name in expected_functions:
        assert func_name in rule_ast.functions

    for var_name in expected_variables:
        assert var_name in rule_ast.variables


@pytest.mark.parametrize(
    "schema_def,function_impl,rule_expr,test_data,expected_result",
    [
        (
            """
            amount: Int
            tax_rate: Float
            calculate_tax: (amt: Int, rate: Float) -> float
            """,
            lambda amount, rate: amount * rate,
            "calculate_tax(amount, tax_rate) > 50",
            {"amount": 1000, "tax_rate": 0.08},
            True,  # 1000 * 0.08 = 80 > 50
        ),
        (
            """
            value: Int
            threshold: Int
            check_range: (val: Int, thresh: Int) -> bool
            """,
            lambda val, thresh: 0 <= val <= thresh,
            "check_range(value, threshold)",
            {"value": 50, "threshold": 100},
            True,
        ),
    ],
)
def test_function_evaluation_integration(schema_def, function_impl, rule_expr, test_data, expected_result):
    """Test end-to-end function evaluation."""
    amn = amino.load_schema(schema_def)

    ast = parse_schema(schema_def)
    func_name = ast.functions[0].name

    amn.add_function(func_name, function_impl)
    result = amn.eval(rule_expr, test_data)
    assert result == expected_result


@pytest.mark.parametrize(
    "schema_content,expected_structs,should_raise,expected_error",
    [
        (
            """
            struct person {
                name: Str,
                age: Int
            }
            """,
            [("person", [("name", SchemaType.str, False), ("age", SchemaType.int, False)])],
            False,
            None,
        ),
        (
            """
            struct user {
                username: Str,
                email: Str?,
                age: Int?
            }
            """,
            [
                (
                    "user",
                    [
                        ("username", SchemaType.str, False),
                        ("email", SchemaType.str, True),
                        ("age", SchemaType.int, True),
                    ],
                )
            ],
            False,
            None,
        ),
        (
            """
            struct person {
                name: Str,
                age: Int
            }
            struct address {
                street: Str,
                city: Str?
            }
            """,
            [
                ("person", [("name", SchemaType.str, False), ("age", SchemaType.int, False)]),
                ("address", [("street", SchemaType.str, False), ("city", SchemaType.str, True)]),
            ],
            False,
            None,
        ),
        (
            """
            struct user {
                name: Str,
                tags: List[Str],
                scores: List[Int]
            }
            """,
            [
                (
                    "user",
                    [
                        ("name", SchemaType.str, False),
                        ("tags", SchemaType.list, False),
                        ("scores", SchemaType.list, False),
                    ],
                )
            ],
            False,
            None,
        ),
    ],
)
def test_struct_definitions(schema_content, expected_structs, should_raise, expected_error):
    """Test struct definition parsing with various scenarios."""
    if should_raise:
        with pytest.raises(SchemaParseError) as excinfo:
            parse_schema(schema_content)
        assert expected_error in str(excinfo.value)
    else:
        ast = parse_schema(schema_content)
        assert len(ast.structs) == len(expected_structs)

        for i, (expected_name, expected_fields) in enumerate(expected_structs):
            struct = ast.structs[i]
            assert struct.name == expected_name
            assert len(struct.fields) == len(expected_fields)

            for j, (field_name, field_type, is_optional) in enumerate(expected_fields):
                field = struct.fields[j]
                assert field.name == field_name
                assert field.field_type == field_type
                assert field.optional == is_optional


@pytest.mark.parametrize(
    "rule_content,schema_content,expected_variables",
    [
        (
            "person.age >= 18 and person.name != 'admin'",
            """
            struct person {
                name: Str,
                age: Int
            }
            """,
            ["person.age", "person.name"],
        ),
        (
            "user.active and user.name = 'test'",
            """
            struct user {
                name: Str,
                active: Bool
            }
            """,
            ["user.active", "user.name"],
        ),
    ],
)
def test_struct_field_access_in_rules(rule_content, schema_content, expected_variables):
    """Test accessing struct fields in rules."""
    schema_ast = parse_schema(schema_content)
    rule_ast = parse_rule(rule_content, schema_ast)

    for var_name in expected_variables:
        assert var_name in rule_ast.variables


@pytest.mark.parametrize(
    "schema_def,test_data,rule_expr,expected_result",
    [
        (
            """
            struct applicant {
                name: Str,
                age: Int,
                state: Str
            }
            """,
            {"applicant": {"name": "John Doe", "age": 25, "state": "CA"}},
            "applicant.age >= 21 and applicant.state = 'CA'",
            True,
        ),
        (
            """
            struct user {
                username: Str,
                active: Bool
            }
            """,
            {"user": {"username": "alice", "active": False}},
            "user.active and user.username = 'alice'",
            False,  # user.active is False
        ),
    ],
)
def test_struct_field_evaluation(schema_def, test_data, rule_expr, expected_result):
    """Test end-to-end struct field evaluation."""
    amn = amino.load_schema(schema_def)
    result = amn.eval(rule_expr, test_data)
    assert result == expected_result


@pytest.mark.parametrize(
    "schema_content,expected_fields,should_raise,expected_error",
    [
        (
            """
            tags: List[Str]
            scores: List[Int]
            """,
            [("tags", SchemaType.list, "List[Str]", ["Str"]), ("scores", SchemaType.list, "List[Int]", ["Int"])],
            False,
            None,
        ),
        (
            """
            mixed_data: list[int|str|float]
            """,
            [("mixed_data", SchemaType.list, "list[Int|Str|Float]", ["Int", "Str", "Float"])],
            False,
            None,
        ),
        (
            """
            flexible: list[str|int]
            very_mixed: list[bool|float|str]
            """,
            [
                ("flexible", SchemaType.list, "list[Str|Int]", ["Str", "Int"]),
                ("very_mixed", SchemaType.list, "list[Bool|Float|Str]", ["Bool", "Float", "Str"]),
            ],
            False,
            None,
        ),
        ("bad_list: list[str", [], True, "rbracket"),
    ],
)
def test_list_type_parsing(schema_content, expected_fields, should_raise, expected_error):
    """Test list type parsing with various scenarios."""
    if should_raise:
        with pytest.raises(SchemaParseError) as excinfo:
            parse_schema(schema_content)
        assert expected_error in str(excinfo.value)
    else:
        ast = parse_schema(schema_content)
        assert len(ast.fields) == len(expected_fields)

        for i, (expected_name, expected_type, expected_type_name, expected_elements) in enumerate(expected_fields):
            field = ast.fields[i]
            assert field.name == expected_name
            assert field.field_type == expected_type
            assert field.type_name == expected_type_name
            assert field.element_types == expected_elements


@pytest.mark.parametrize(
    "rule_content,schema_content,expected_variables",
    [
        (
            "user_role in tags",
            """
            tags: List[Str]
            user_role: Str
            """,
            ["tags", "user_role"],
        ),
        (
            "'admin' in permissions and level > 1",
            """
            permissions: List[Str]
            level: Int
            """,
            ["permissions", "level"],
        ),
    ],
)
def test_list_operations_in_rules(rule_content, schema_content, expected_variables):
    """Test using list operations in rules."""
    schema_ast = parse_schema(schema_content)
    rule_ast = parse_rule(rule_content, schema_ast)

    for var_name in expected_variables:
        assert var_name in rule_ast.variables


@pytest.mark.parametrize(
    "schema_def,test_data,rule_expr,expected_result",
    [
        ("tags: List[Str]", {"tags": ["user", "admin", "guest"]}, "'admin' in tags", True),
        ("mixed: list[int|str|float]", {"mixed": [1, "hello", 3.14]}, "1 in mixed", True),
        ("numbers: List[Int]", {"numbers": [10, 20, 30, 40]}, "25 in numbers", False),
    ],
)
def test_list_validation_and_operations(schema_def, test_data, rule_expr, expected_result):
    """Test list validation and operations in rules."""
    amn = amino.load_schema(schema_def)
    result = amn.eval(rule_expr, test_data)
    assert result == expected_result


@pytest.mark.parametrize(
    "schema_content,expected_constraints,should_raise,expected_error",
    [
        (
            """
            username: Str {length: 8}
            password: Str {min: 8, max: 32}
            """,
            [("username", {"length": 8}), ("password", {"min": 8, "max": 32})],
            False,
            None,
        ),
        (
            """
            email: Str {format: email}
            phone: Str {format: phone}
            """,
            [("email", {"format": "email"}), ("phone", {"format": "phone"})],
            False,
            None,
        ),
        (
            """
            age: Int {min: 0, max: 150}
            score: Float {min: 0.0, max: 100.0}
            """,
            [("age", {"min": 0, "max": 150}), ("score", {"min": 0, "max": 100})],
            False,
            None,
        ),
        (
            """
            title: Str {format: title, min: 5, max: 100}
            """,
            [("title", {"format": "title", "min": 5, "max": 100})],
            False,
            None,
        ),
    ],
)
def test_enhanced_constraints_parsing(schema_content, expected_constraints, should_raise, expected_error):
    """Test enhanced constraint parsing with various scenarios."""
    if should_raise:
        with pytest.raises(SchemaParseError) as excinfo:
            parse_schema(schema_content)
        assert expected_error in str(excinfo.value)
    else:
        ast = parse_schema(schema_content)
        assert len(ast.fields) == len(expected_constraints)

        for i, (expected_name, expected_constraint_dict) in enumerate(expected_constraints):
            field = ast.fields[i]
            assert field.name == expected_name
            for key, value in expected_constraint_dict.items():
                assert field.constraints[key] == value


@pytest.mark.parametrize(
    "schema_def,test_data,expected_valid,expected_error_contains",
    [
        ("email: Str {format: email}", {"email": "user@example.com"}, True, None),
        ("email: Str {format: email}", {"email": "invalid-email"}, False, "email"),
        ("age: Int {min: 0, max: 150}", {"age": 25}, True, None),
        ("age: Int {min: 18, max: 120}", {"age": 16}, False, "minimum"),
        ("age: Int {min: 0, max: 120}", {"age": 150}, False, "maximum"),
    ],
)
def test_constraint_validation_integration(schema_def, test_data, expected_valid, expected_error_contains):
    """Test constraint validation with type registry."""
    from amino.types.validation import TypeValidator

    schema_ast = parse_schema(schema_def)
    validator = TypeValidator(schema_ast)
    result = validator.validate_data(test_data)

    assert result.valid == expected_valid

    if not expected_valid:
        assert len(result.errors) > 0
        assert any(expected_error_contains in error.message.lower() for error in result.errors)


@pytest.mark.parametrize(
    "schema_def,function_impl,test_data,rule_expr,expected_result",
    [
        (
            """
            struct applicant {
                name: Str,
                age: Int,
                tags: List[Str]
            }

            MIN_AGE: Int = 18
            validate_eligibility: (app: applicant, min_age: Int) -> bool
            """,
            lambda applicant, min_age: applicant["age"] >= min_age,
            {"applicant": {"name": "John", "age": 25, "tags": ["premium", "verified"]}},
            """
            validate_eligibility(applicant, 18) and
            'verified' in applicant.tags and
            applicant.age >= 21
            """,
            True,
        ),
        (
            """
            struct user {
                username: Str,
                permissions: List[Str],
                level: Int
            }

            check_access: (u: user, required_perm: Str) -> bool
            """,
            lambda user, required_perm: required_perm in user["permissions"] and user["level"] >= 1,
            {"user": {"username": "alice", "permissions": ["read", "write", "admin"], "level": 2}},
            "check_access(user, 'admin') and user.level > 1",
            True,
        ),
    ],
)
def test_comprehensive_phase2_integration(schema_def, function_impl, test_data, rule_expr, expected_result):
    """Test complex scenarios combining all Phase 2 features."""
    amn = amino.load_schema(schema_def)

    ast = parse_schema(schema_def)
    func_name = ast.functions[0].name

    amn.add_function(func_name, function_impl)
    result = amn.eval(rule_expr, test_data)
    assert result == expected_result
