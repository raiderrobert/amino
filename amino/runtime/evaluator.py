"""Rule evaluation implementation."""

from typing import List, Dict, Any, Callable
from ..rules.compiler import CompiledRule
from ..utils.errors import RuleEvaluationError


class RuleEvaluator:
    """Evaluates compiled rules against data."""
    
    def __init__(self, function_registry: Dict[str, Callable] | None = None):
        self.function_registry = function_registry or {}
    
    def evaluate_single(self, rule: CompiledRule, data: Dict[str, Any]) -> bool:
        """Evaluate a single rule against data."""
        try:
            return rule.evaluate(data, self.function_registry)
        except Exception as e:
            raise RuleEvaluationError(f"Error evaluating rule {rule.rule_id}: {e}")
    
    def evaluate_batch(self, rules: List[CompiledRule], 
                      data_list: List[Dict[str, Any]]) -> List[List[tuple[Any, bool]]]:
        """Evaluate multiple rules against multiple data items."""
        results = []
        
        for data in data_list:
            data_results = []
            for rule in rules:
                try:
                    matched = self.evaluate_single(rule, data)
                    data_results.append((rule.rule_id, matched))
                except RuleEvaluationError:
                    data_results.append((rule.rule_id, False))
            results.append(data_results)
        
        return results
    
    def evaluate_rules_for_data(self, rules: List[CompiledRule], 
                               data: Dict[str, Any]) -> List[tuple[Any, bool]]:
        """Evaluate all rules for a single data item."""
        results = []
        for rule in rules:
            try:
                matched = self.evaluate_single(rule, data)
                results.append((rule.rule_id, matched))
            except RuleEvaluationError:
                results.append((rule.rule_id, False))
        return results
    
    def add_function(self, name: str, func: Callable):
        """Add a function to the registry."""
        self.function_registry[name] = func
    
    def remove_function(self, name: str):
        """Remove a function from the registry."""
        if name in self.function_registry:
            del self.function_registry[name]