# amino/engine.py
from collections.abc import Callable
from typing import Any

from amino.errors import EngineAlreadyFrozenError
from amino.operators.registry import OperatorDef, OperatorRegistry
from amino.operators.standard import build_operator_registry
from amino.rules.compiler import TypedCompiler
from amino.rules.parser import parse_rule
from amino.runtime.compiled_rules import CompiledRules
from amino.runtime.matcher import MatchResult
from amino.runtime.validator import DecisionValidator
from amino.schema.parser import parse_schema
from amino.schema.registry import SchemaRegistry
from amino.types.builtin import register_builtin_types
from amino.types.registry import TypeRegistry


class Engine:
    def __init__(
        self,
        schema_text: str,
        *,
        funcs: dict[str, Callable] | None = None,
        rules_mode: str = "strict",
        decisions_mode: str = "loose",
        operators: "str | list[str]" = "standard",
    ):
        ast = parse_schema(schema_text)
        self._type_registry = TypeRegistry()
        register_builtin_types(self._type_registry)
        self._op_registry: OperatorRegistry = build_operator_registry(operators)
        self._schema_registry = SchemaRegistry(
            ast, known_custom_types=self._type_registry.registered_names()
        )
        self._functions: dict[str, Callable] = dict(funcs or {})
        self._rules_mode = rules_mode
        self._decisions_mode = decisions_mode
        self._frozen = False

    # ── Registration ──────────────────────────────────────────────────

    def _check_frozen(self) -> None:
        if self._frozen:
            raise EngineAlreadyFrozenError(
                "Cannot register after first compile() or eval()"
            )

    def add_function(self, name: str, fn: Callable) -> None:
        self._check_frozen()
        self._functions[name] = fn

    def register_type(self, name: str, base: str, validator: Callable) -> None:
        self._check_frozen()
        # Allow overwriting existing types (e.g. user overrides a builtin).
        self._type_registry.register_type(name, base, validator, overwrite=True)

    def register_operator(
        self,
        *,
        symbol: str | None = None,
        keyword: str | None = None,
        kind: str = "infix",
        fn: Callable,
        binding_power: int,
        associativity: str = "left",
        input_types: tuple[str, ...] = ("*", "*"),
        return_type: str = "Bool",
    ) -> None:
        self._check_frozen()
        op = OperatorDef(
            symbol=symbol, keyword=keyword, kind=kind, fn=fn,
            binding_power=binding_power, associativity=associativity,
            input_types=input_types, return_type=return_type,
        )
        self._op_registry.register(op)

    # ── Compilation ───────────────────────────────────────────────────

    def _freeze(self) -> None:
        self._frozen = True

    def compile(
        self, rules: list[dict[str, Any]], match: dict | None = None
    ) -> CompiledRules:
        self._freeze()
        compiler = TypedCompiler(rules_mode=self._rules_mode)
        compiled_list = []
        for raw in rules:
            rule_id = raw["id"]
            ast = parse_rule(raw["rule"], self._schema_registry, self._op_registry)
            compiled = compiler.compile(rule_id, ast)
            compiled_list.append((rule_id, compiled, raw))
        validator = DecisionValidator(self._schema_registry, self._decisions_mode)
        return CompiledRules(
            compiled_list, validator,
            match_config=match,
            function_registry=self._functions,
        )

    def eval(
        self,
        rules: list[dict[str, Any]],
        decision: dict[str, Any],
        match: dict | None = None,
    ) -> MatchResult:
        compiled = self.compile(rules, match)
        return compiled.eval_single(decision)

    def export_schema(self) -> str:
        return self._schema_registry.export_schema()
