"""Compiled rules container and execution."""

from typing import List, Dict, Any, Callable
from ..rules.compiler import CompiledRule
from .evaluator import RuleEvaluator
from .matcher import RuleMatcher, MatchResult, MatchOptions


class CompiledRules:
    """Container for compiled rules with evaluation methods."""
    
    def __init__(self, rules: List[CompiledRule], 
                 function_registry: Dict[str, Callable] | None = None,
                 match_options: MatchOptions | None = None):
        self.rules = rules
        self.evaluator = RuleEvaluator(function_registry)
        self.matcher = RuleMatcher(match_options)
        self.rule_metadata = {}
    
    def eval(self, data: List[Dict[str, Any]]) -> List[MatchResult]:
        """Evaluate rules against multiple data items."""
        results = []
        
        for item in data:
            item_id = item.get("id")
            if item_id is None:
                raise ValueError("Data items must have an 'id' field")
            
            rule_results = self.evaluator.evaluate_rules_for_data(self.rules, item)
            
            match_result = self.matcher.process_matches(
                item_id, rule_results, self.rule_metadata
            )
            results.append(match_result)
        
        return results
    
    def eval_single(self, data: Dict[str, Any]) -> MatchResult:
        """Evaluate rules against a single data item."""
        results = self.eval([data])
        return results[0] if results else MatchResult(data.get("id"), [])
    
    def add_rule_metadata(self, rule_id: Any, metadata: Dict[str, Any]):
        """Add metadata for a rule (used for ordering, etc.)."""
        self.rule_metadata[rule_id] = metadata
    
    def add_function(self, name: str, func: Callable):
        """Add a function to the evaluation context."""
        self.evaluator.add_function(name, func)
    
    def get_rule_variables(self) -> Dict[Any, List[str]]:
        """Get variables referenced by each rule."""
        return {rule.rule_id: rule.variables for rule in self.rules}
    
    def get_rule_functions(self) -> Dict[Any, List[str]]:
        """Get functions referenced by each rule."""
        return {rule.rule_id: rule.functions for rule in self.rules}