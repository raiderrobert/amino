"""
Runtime evaluation engine for Amino.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from amino.types.base import Type, TypeError
from amino.types.checker import TypeChecker
from amino.types.expressions import Expression, BinaryOp, Identifier, FunctionCall, Literal
from amino.parser.rules import parse_rule


class RuntimeError(Exception):
    pass


@dataclass
class Value:
    """Represents a runtime value with its type"""
    type: Type
    value: Any

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Value):
            return NotImplemented
        return self.value == other.value


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
        # First parse and type check all rules
        parsed_rules = []
        for rule_dict in rules:
            try:
                expr = parse_rule(rule_dict['rule'])
                # Type check will raise TypeError if there's an issue
                self.type_checker.check_expression(expr)
                rule = Rule(
                    id=rule_dict['id'],
                    expression=expr,
                    ordering=rule_dict.get('ordering')
                )
                parsed_rules.append(rule)
            except Exception as e:
                # Re-raise TypeError, wrap others
                if isinstance(e, TypeError):
                    raise e
                raise RuntimeError(f"Error parsing rule {rule_dict['id']}: {e}")
        
        # If all rules parse and type check, update the engine
        self.rules = parsed_rules
        
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
                except Exception as e:
                    # Re-raise TypeError, wrap others
                    if isinstance(e, TypeError):
                        raise e
                    raise RuntimeError(f"Error evaluating rule {rule.id}: {e}")

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
                if name in self.type_checker.schema_types:
                    variables[name] = Value(self.type_checker.schema_types[name], value)
        
        return Environment(variables=variables, functions={})