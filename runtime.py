from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from type_system import (
    Type, TypeChecker, Expression, BinaryOp, Identifier, 
    Literal, FunctionCall, TypeError
)

# ---- Runtime Value System ----

@dataclass
class Value:
    """Represents a runtime value with its type"""
    type: Type
    value: Any

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Value):
            return NotImplemented
        return self.value == other.value

class RuntimeError(Exception):
    pass

# ---- Runtime Environment ----

@dataclass
class Environment:
    """Runtime environment holding variable bindings and functions"""
    variables: Dict[str, Value]
    functions: Dict[str, callable]
    parent: Optional['Environment'] = None

    def get(self, name: str) -> Value:
        """Get a variable value from the environment"""
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.get(name)
        raise RuntimeError(f"Unknown variable: {name}")

    def get_function(self, name: str) -> callable:
        """Get a function from the environment"""
        if name in self.functions:
            return self.functions[name]
        if self.parent:
            return self.parent.get_function(name)
        raise RuntimeError(f"Unknown function: {name}")

# ---- Evaluator ----

class Evaluator:
    """Evaluates expressions in a given environment"""
    
    def __init__(self, type_checker: TypeChecker):
        self.type_checker = type_checker

    def eval(self, expr: Expression, env: Environment) -> Value:
        """Evaluate an expression in the given environment"""
        # Type check first
        result_type = self.type_checker.check_expression(expr)
        
        if isinstance(expr, Literal):
            return Value(result_type, expr.value)
        
        elif isinstance(expr, Identifier):
            return env.get(expr.name)
        
        elif isinstance(expr, BinaryOp):
            left = self.eval(expr.left, env)
            right = self.eval(expr.right, env)
            
            if expr.op in {'and', 'or'}:
                return self._eval_logical_op(expr.op, left, right)
            elif expr.op in {'=', '!=', '>', '<', '>=', '<='}:
                return self._eval_comparison_op(expr.op, left, right)
            elif expr.op in {'in', 'not in'}:
                return self._eval_membership_op(expr.op, left, right)
            else:
                raise RuntimeError(f"Unknown operator: {expr.op}")
        
        elif isinstance(expr, FunctionCall):
            func = env.get_function(expr.name)
            args = [self.eval(arg, env) for arg in expr.args]
            result = func(*[arg.value for arg in args])
            return Value(result_type, result)
        
        raise RuntimeError(f"Cannot evaluate: {expr}")

    def _eval_logical_op(self, op: str, left: Value, right: Value) -> Value:
        if op == 'and':
            result = left.value and right.value
        else:  # or
            result = left.value or right.value
        return Value(self.type_checker.schema_types['bool'], result)

    def _eval_comparison_op(self, op: str, left: Value, right: Value) -> Value:
        ops = {
            '=': lambda x, y: x == y,
            '!=': lambda x, y: x != y,
            '>': lambda x, y: x > y,
            '<': lambda x, y: x < y,
            '>=': lambda x, y: x >= y,
            '<=': lambda x, y: x <= y,
        }
        result = ops[op](left.value, right.value)
        return Value(self.type_checker.schema_types['bool'], result)

    def _eval_membership_op(self, op: str, left: Value, right: Value) -> Value:
        result = (left.value in right.value) if op == 'in' else (left.value not in right.value)
        return Value(self.type_checker.schema_types['bool'], result)

# ---- Rule Engine ----

@dataclass
class Rule:
    """Represents a rule in the system"""
    id: int
    expression: Expression
    ordering: Optional[int] = None

@dataclass
class RuleMatch:
    """Represents a rule match configuration"""
    option: str  # 'all' or 'first'
    key: Optional[str] = None  # for ordering when option='first'
    ordering: Optional[str] = None  # 'asc' or 'desc'

class RuleEngine:
    """Main rule engine that evaluates rules against datasets"""
    
    def __init__(self, type_checker: TypeChecker):
        self.type_checker = type_checker
        self.evaluator = Evaluator(type_checker)
        self.rules: List[Rule] = []
        self.match_config: Optional[RuleMatch] = None

    def add_rules(self, rules: List[Dict[str, Any]], match: Optional[Dict[str, str]] = None):
        """Add rules to the engine"""
        # Clear existing rules
        self.rules = []
        
        # Parse and add new rules
        for rule_dict in rules:
            rule = Rule(
                id=rule_dict['id'],
                expression=self._parse_expression(rule_dict['rule']),
                ordering=rule_dict.get('ordering')
            )
            self.rules.append(rule)

        # Set match configuration
        if match:
            self.match_config = RuleMatch(
                option=match['option'],
                key=match.get('key'),
                ordering=match.get('ordering')
            )
        else:
            self.match_config = RuleMatch(option='all')

    def evaluate(self, datasets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluate all rules against all datasets"""
        results = []
        
        for data in datasets:
            # Create environment for this dataset
            env = self._create_environment(data)
            
            # Evaluate all rules
            matches = []
            for rule in self.rules:
                try:
                    result = self.evaluator.eval(rule.expression, env)
                    if result.value:  # Rule matched
                        matches.append(rule.id)
                except (RuntimeError, TypeError) as e:
                    print(f"Error evaluating rule {rule.id}: {e}")
                    continue

            # Apply match configuration
            if self.match_config.option == 'first' and matches:
                if self.match_config.key == 'ordering':
                    # Sort rules by ordering
                    ordered_matches = []
                    for match_id in matches:
                        rule = next(r for r in self.rules if r.id == match_id)
                        ordered_matches.append((rule.ordering, match_id))
                    
                    ordered_matches.sort()  # Sort by ordering
                    if self.match_config.ordering == 'desc':
                        ordered_matches.reverse()
                    
                    matches = [ordered_matches[0][1]]  # Take first match

            results.append({
                'id': data['id'],
                'results': matches
            })

        return results

    def _create_environment(self, data: Dict[str, Any]) -> Environment:
        """Create an environment from a dataset"""
        variables = {}
        for name, value in data.items():
            if name != 'id':  # Skip the id field
                # Here we would need to properly convert the value to a Value object
                # with the correct type from the schema
                variables[name] = Value(self.type_checker.schema_types[name], value)
        
        return Environment(variables=variables, functions={})

    def _parse_expression(self, rule_str: str) -> Expression:
        """Parse a rule string into an Expression"""
        # This is a placeholder - you would need to implement a proper parser
        # For now, we'll raise NotImplementedError
        raise NotImplementedError("Expression parsing not implemented")

# ---- Example Usage ----

def example_usage():
    from type_system import PrimitiveType, TypeChecker
    
    # Create type system
    schema_types = {
        'amount': PrimitiveType.INT(),
        'state_code': PrimitiveType.STR(),
        'bool': PrimitiveType.BOOL(),
    }
    
    type_checker = TypeChecker(schema_types)
    
    # Create rule engine
    engine = RuleEngine(type_checker)
    
    # Example rules (in practice, these would be parsed from strings)
    rules = [
        {
            'id': 1,
            'rule': BinaryOp(
                left=BinaryOp(
                    left=Identifier('amount'),
                    op='>',
                    right=Literal(0)
                ),
                op='and',
                right=BinaryOp(
                    left=Identifier('state_code'),
                    op='=',
                    right=Literal('CA')
                )
            )
        },
        {
            'id': 2,
            'rule': BinaryOp(
                left=Identifier('amount'),
                op='>=',
                right=Literal(100)
            )
        }
    ]
    
    # Add rules to engine
    engine.add_rules(rules)
    
    # Example datasets
    datasets = [
        {'id': 45, 'amount': 100, 'state_code': 'CA'},
        {'id': 46, 'amount': 50, 'state_code': 'CA'},
        {'id': 47, 'amount': 100, 'state_code': 'NY'},
    ]
    
    # Evaluate rules
    results = engine.evaluate(datasets)
    print(results)