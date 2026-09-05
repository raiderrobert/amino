"""Compiled rules container and execution."""

from typing import Any

from amino.rules.compiler import CompiledRule

from .matcher import Matcher, MatchResult
from .validator import DecisionValidator


class CompiledRules:
    def __init__(
        self,
        rules: list[tuple[Any, CompiledRule, dict]],
        validator: DecisionValidator,
        match_config: dict | None = None,
        function_registry: dict | None = None,
    ):
        # rules: list of (rule_id, CompiledRule, raw_rule_dict)
        self._rules = rules
        self._validator = validator
        self._matcher = Matcher(match_config)
        self._functions = function_registry or {}
        self._metadata = {rule_id: raw for rule_id, _, raw in rules}

    def eval_single(self, decision: dict[str, Any]) -> MatchResult:
        cleaned, warnings = self._validator.validate(decision)
        rule_results: list[tuple[Any, Any]] = []
        for rule_id, compiled, _ in self._rules:
            val = compiled.evaluate(cleaned, self._functions)
            rule_results.append((rule_id, val))
        decision_id = decision.get("id")
        return self._matcher.process(decision_id, rule_results, self._metadata, warnings)

    def eval(self, decisions: list[dict[str, Any]]) -> list[MatchResult]:
        return [self.eval_single(d) for d in decisions]
