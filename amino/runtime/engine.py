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
                 function_registry: Dict[str, Callable] = None):
        self.schema_ast = schema_ast
        self.function_registry = function_registry or {}
        self.compiler = RuleCompiler()
        self.optimizer = RuleOptimizer()
    
    def compile_rules(self, rule_definitions: List[Union[RuleDefinition, Dict[str, Any]]], 
                     match_options: Dict[str, Any] = None) -> CompiledRules:
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
        if match_options:
            if "match" in match_options:
                match_config = match_options["match"]
                if match_config.get("option") == "first":
                    options.mode = MatchMode.FIRST
                    options.ordering_key = match_config.get("key")
                    options.ordering_direction = match_config.get("ordering", "asc")
        
        # Create compiled rules container
        compiled = CompiledRules(compiled_rules, self.function_registry, options)
        
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