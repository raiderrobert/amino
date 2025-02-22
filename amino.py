from type_system import TypeChecker, PrimitiveType
from runtime import RuleEngine
import json

class Amino:
    """Main entry point for the Amino rules engine"""
    
    def __init__(self, schema_file: str):
        """Initialize Amino with a schema file"""
        # For now, hardcode the types - in a real implementation,
        # you would parse the schema file
        self.schema_types = {
            'amount': PrimitiveType.INT(),
            'state_code': PrimitiveType.STR(),
            'bool': PrimitiveType.BOOL(),
        }
        self.type_checker = TypeChecker(self.schema_types)
        self.engine = RuleEngine(self.type_checker)

    def eval(self, rule: str, data: dict) -> bool:
        """Evaluate a single rule against a single dataset"""
        self.engine.add_rules([{'id': 1, 'rule': rule}])
        result = self.engine.evaluate([{'id': 1, **data}])
        return len(result[0]['results']) > 0

    def compile(self, rules: list, match: dict = None) -> 'CompiledRules':
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
    return Amino(schema_file)