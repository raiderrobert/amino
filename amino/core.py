"""Main Amino API implementation."""

from typing import Dict, Any, List, Callable, Union
from .schema.parser import parse_schema
from .schema.ast import SchemaAST
from .schema.validator import SchemaValidator
from .runtime.engine import RuleEngine, RuleDefinition
from .runtime.compiled_rules import CompiledRules
from .types.registry import TypeRegistry
from .types.builtin import register_builtin_types
from .utils.errors import SchemaParseError


class Schema:
    """Main schema class providing the public API."""
    
    def __init__(self, schema_content: str, type_registry: TypeRegistry | None = None, 
                 funcs: Dict[str, Callable] | None = None, strict: bool = False):
        """Initialize schema from content string."""
        if type_registry is None:
            type_registry = TypeRegistry()
            register_builtin_types(type_registry)
        self.type_registry = type_registry
        
        known_custom_types = set(self.type_registry.get_registered_types()) if strict else None
        
        try:
            self.ast = parse_schema(schema_content, strict=strict, 
                                  known_custom_types=known_custom_types)
        except Exception as e:
            raise SchemaParseError(f"Failed to parse schema: {e}")
        
        validator = SchemaValidator(self.ast)
        errors = validator.validate()
        if errors:
            raise SchemaParseError(f"Schema validation failed: {', '.join(errors)}")
        
        self.engine = RuleEngine(self.ast, funcs or {})
    
    def eval(self, rule: str, data: Dict[str, Any]) -> bool:
        """Evaluate a single rule against data."""
        return self.engine.eval_single_rule(rule, data)
    
    def compile(self, rules: List[Union[Dict[str, Any], RuleDefinition]], 
                **options) -> CompiledRules:
        """Compile rules for batch evaluation."""
        return self.engine.compile_rules(rules, options)
    
    def add_function(self, name: str, func: Callable):
        """Add a function to the evaluation context."""
        self.engine.add_function(name, func)
    
    def register_type(self, name: str, base_type: str, validator: Callable | None = None, **constraints):
        """Register a custom type."""
        self.type_registry.register_type(name, base_type, validator, **constraints)


def load_schema(schema_file_or_content: str, type_registry: TypeRegistry | None = None, 
                funcs: Dict[str, Callable] | None = None, strict: bool = False) -> Schema:
    """Load schema from file path or content string."""
    try:
        with open(schema_file_or_content, 'r') as f:
            content = f.read()
    except (FileNotFoundError, OSError):
        content = schema_file_or_content
    
    return Schema(content, type_registry, funcs, strict)


def parse_schema_content(content: str) -> SchemaAST:
    """Parse schema content into AST."""
    return parse_schema(content)


def compile_rules(schema_ast: SchemaAST, rules: List[Union[RuleDefinition, Dict[str, Any]]]) -> CompiledRules:
    """Compile rules against a schema AST."""
    engine = RuleEngine(schema_ast)
    return engine.compile_rules(rules)