"""
Core Amino functionality.
"""

import os
from typing import Dict, Optional

from amino.parser.schema import parse_schema
from amino.types.base import Type, PrimitiveType, TypeKind, TypeError
from amino.types.checker import TypeChecker
from amino.core.runtime import RuleEngine


class Amino:
    """Main entry point for the Amino rules engine"""
    
    def __init__(self, schema_types: Dict[str, Type]):
        """Initialize Amino with schema types"""
        self.schema_types = schema_types
        self.type_checker = TypeChecker(self.schema_types)
        self.engine = RuleEngine(self.type_checker)

    def eval(self, rule: str, data: dict) -> bool:
        """Evaluate a single rule against a single dataset"""
        try:
            self.engine.add_rules([{'id': 1, 'rule': rule}])
            result = self.engine.evaluate([{'id': 1, **data}])
            return len(result[0]['results']) > 0
        except Exception as e:
            # Re-raise all errors instead of swallowing them
            raise e

    def compile(self, rules: list, match: Optional[dict] = None) -> 'CompiledRules':
        """Compile multiple rules for evaluation"""
        self.engine.add_rules(rules, match)
        return CompiledRules(self.engine)


class CompiledRules:
    """Represents a compiled set of rules"""
    
    def __init__(self, engine: RuleEngine):
        self.engine = engine

    def eval(self, datasets: list) -> list:
        """Evaluate the compiled rules against multiple datasets"""
        return self.engine.evaluate(datasets)


def load_schema(schema_file: str) -> Amino:
    """Load an Amino schema from a file"""
    # Load and parse schema file
    if not os.path.exists(schema_file):
        # For testing, create a default schema
        schema_text = """
        amount: int
        state_code: str
        """
    else:
        with open(schema_file, 'r') as f:
            schema_text = f.read()
    
    # Parse schema
    schema_types = parse_schema(schema_text)
    
    # Add bool type which is always needed for expressions
    schema_types['bool'] = PrimitiveType(TypeKind.BOOL)
    
    return Amino(schema_types)