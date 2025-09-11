"""Main rule evaluation engine."""

from typing import List, Dict, Any, Callable, Optional, Union
from ..schema.ast import SchemaAST
from ..rules.ast import RuleAST
from ..rules.parser import parse_rule
from ..rules.compiler import RuleCompiler
from ..rules.optimizer import RuleOptimizer
from .compiled_rules import CompiledRules
from .matcher import MatchOptions, MatchMode
from ..utils.errors import RuleParseError, RuleEvaluationError


class RuleDefinition:
    """Definition of a single rule."""
    
    def __init__(self, id: Any, rule: str, ordering: Optional[int] = None, 
                 metadata: Optional[Dict[str, Any]] = None):
        self.id = id
        self.rule = rule
        self.ordering = ordering
        self.metadata = metadata or {}


class RuleEngine:
    """Main rule evaluation engine."""
    
    def __init__(self, schema_ast: SchemaAST, 
                 function_registry: Dict[str, Callable] | None = None):
        self.schema_ast = schema_ast
        self.function_registry = function_registry or {}
        self.compiler = RuleCompiler()
        self.optimizer = RuleOptimizer()
    
    def compile_rules(self, rule_definitions: List[Union[RuleDefinition, Dict[str, Any]]], 
                     match: Dict[str, Any] | None = None) -> CompiledRules:
        """Compile a list of rule definitions."""
        # Normalize rule definitions
        rules = []
        for rule_def in rule_definitions:
            if isinstance(rule_def, dict):
                rules.append(RuleDefinition(
                    id=rule_def["id"],
                    rule=rule_def["rule"],
                    ordering=rule_def.get("ordering"),
                    metadata=rule_def.get("metadata", {})
                ))
            else:
                rules.append(rule_def)
        
        # Parse and compile rules
        compiled_rules = []
        rule_metadata = {}
        
        for rule_def in rules:
            try:
                # Parse rule
                ast = parse_rule(rule_def.rule, self.schema_ast)
                
                # Optimize AST
                optimized_ast = self.optimizer.optimize(ast)
                
                # Compile rule
                compiled_rule = self.compiler.compile_rule(rule_def.id, optimized_ast)
                compiled_rules.append(compiled_rule)
                
                # Store metadata
                metadata = rule_def.metadata.copy()
                if rule_def.ordering is not None:
                    metadata["ordering"] = rule_def.ordering
                rule_metadata[rule_def.id] = metadata
                
            except Exception as e:
                raise RuleParseError(f"Error compiling rule {rule_def.id}: {e}")
        
        # Create match options
        options = MatchOptions()
        if match:
            # Handle both direct match config and nested match config
            match_config = match.get("match", match)
            if match_config.get("option") == "first":
                options.mode = MatchMode.FIRST
                options.ordering_key = match_config.get("key")
                options.ordering_direction = match_config.get("ordering", "asc")
        
        # Optimize rule order for performance
        optimized_rules = self._optimize_rule_order(compiled_rules, options)
        
        # Create compiled rules container
        compiled = CompiledRules(optimized_rules, self.function_registry, options)
        
        # Add rule metadata
        for rule_id, metadata in rule_metadata.items():
            compiled.add_rule_metadata(rule_id, metadata)
        
        return compiled
    
    def eval_single_rule(self, rule: str, data: Dict[str, Any]) -> bool:
        """Evaluate a single rule against data."""
        try:
            ast = parse_rule(rule, self.schema_ast)
            optimized_ast = self.optimizer.optimize(ast)
            compiled_rule = self.compiler.compile_rule("temp", optimized_ast)
            
            from .evaluator import RuleEvaluator
            evaluator = RuleEvaluator(self.function_registry)
            return evaluator.evaluate_single(compiled_rule, data)
            
        except Exception as e:
            raise RuleEvaluationError(f"Error evaluating rule: {e}")
    
    def add_function(self, name: str, func: Callable):
        """Add a function to the registry."""
        self.function_registry[name] = func
    
    def remove_function(self, name: str):
        """Remove a function from the registry."""
        if name in self.function_registry:
            del self.function_registry[name]
    
    def _optimize_rule_order(self, rules: List, options: MatchOptions) -> List:
        """Optimize rule order for performance.
        
        Orders rules by complexity (simpler rules first) for better performance.
        In FIRST mode, this can significantly reduce evaluation time.
        """
        if not rules:
            return rules
        
        # For FIRST mode with explicit ordering, don't optimize (user ordering takes precedence)
        if options.mode == MatchMode.FIRST and options.ordering_key:
            return rules  # Keep original order for explicit ordering
        
        # For FIRST mode without explicit ordering, sort by complexity (simpler rules first)
        if options.mode == MatchMode.FIRST:
            return sorted(rules, key=self._estimate_rule_complexity)
        
        # For ALL mode, keep original order (no optimization benefit)
        return rules
    
    def _estimate_rule_complexity(self, rule) -> int:
        """Estimate the computational complexity of a rule.
        
        Returns a complexity score (lower = simpler/faster).
        """
        complexity = 0
        
        # Base complexity for any rule
        complexity += 1
        
        # Add complexity for operators and functions in the rule string
        rule_text = getattr(rule, 'rule_text', str(rule))
        
        # Count logical operators (AND/OR add complexity)
        complexity += rule_text.lower().count(' and ') * 2
        complexity += rule_text.lower().count(' or ') * 2
        
        # Count function calls (expensive operations)
        complexity += rule_text.count('(') * 3
        
        # Count field references
        complexity += rule_text.count('.') * 1
        
        # Longer rules are generally more complex
        complexity += len(rule_text) // 20
        
        return complexity