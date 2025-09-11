"""Debugging and profiling utilities for Amino rule engine."""

import time
import dataclasses
from typing import Dict, List, Any, Optional
from contextlib import contextmanager


@dataclasses.dataclass
class RuleProfile:
    """Profile information for a single rule."""
    rule_id: Any
    rule_text: str
    execution_time: float
    evaluation_count: int
    match_count: int
    error_count: int
    

@dataclasses.dataclass 
class EvaluationProfile:
    """Profile information for a complete evaluation session."""
    total_time: float
    total_rules: int
    total_evaluations: int
    total_matches: int
    rule_profiles: Dict[Any, RuleProfile]
    short_circuit_savings: int = 0


class RuleProfiler:
    """Profiler for rule engine performance analysis."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset all profiling data."""
        self.rule_profiles: Dict[Any, RuleProfile] = {}
        self.session_start_time = None
        self.total_evaluations = 0
        self.total_matches = 0
        self.short_circuit_count = 0
    
    @contextmanager
    def profile_evaluation(self):
        """Context manager for profiling a complete evaluation."""
        self.session_start_time = time.perf_counter()
        try:
            yield self
        finally:
            pass
    
    @contextmanager 
    def profile_rule(self, rule_id: Any, rule_text: str):
        """Context manager for profiling individual rule execution."""
        start_time = time.perf_counter()
        
        if rule_id not in self.rule_profiles:
            self.rule_profiles[rule_id] = RuleProfile(
                rule_id=rule_id,
                rule_text=rule_text,
                execution_time=0.0,
                evaluation_count=0,
                match_count=0,
                error_count=0
            )
        
        profile = self.rule_profiles[rule_id]
        profile.evaluation_count += 1
        self.total_evaluations += 1
        
        error_occurred = False
        matched = False
        
        try:
            yield profile
        except Exception:
            error_occurred = True
            profile.error_count += 1
            raise
        finally:
            execution_time = time.perf_counter() - start_time
            profile.execution_time += execution_time
    
    def record_match(self, rule_id: Any):
        """Record that a rule matched."""
        if rule_id in self.rule_profiles:
            self.rule_profiles[rule_id].match_count += 1
        self.total_matches += 1
    
    def record_short_circuit(self):
        """Record that short-circuit optimization was triggered."""
        self.short_circuit_count += 1
    
    def get_profile_summary(self) -> EvaluationProfile:
        """Get a summary of the current profiling session."""
        total_time = 0.0
        if self.session_start_time:
            total_time = time.perf_counter() - self.session_start_time
        
        return EvaluationProfile(
            total_time=total_time,
            total_rules=len(self.rule_profiles),
            total_evaluations=self.total_evaluations,
            total_matches=self.total_matches,
            rule_profiles=self.rule_profiles.copy(),
            short_circuit_savings=self.short_circuit_count
        )
    
    def print_profile_report(self, show_rules: bool = True):
        """Print a formatted profiling report."""
        profile = self.get_profile_summary()
        
        print("=" * 60)
        print("AMINO RULE ENGINE PERFORMANCE REPORT")
        print("=" * 60)
        print(f"Total evaluation time: {profile.total_time:.4f} seconds")
        print(f"Total rules: {profile.total_rules}")
        print(f"Total rule evaluations: {profile.total_evaluations}")
        print(f"Total matches: {profile.total_matches}")
        print(f"Match rate: {profile.total_matches/max(profile.total_evaluations,1)*100:.1f}%")
        print(f"Short-circuit optimizations: {profile.short_circuit_savings}")
        
        if show_rules and profile.rule_profiles:
            print("\n" + "-" * 60)
            print("PER-RULE PERFORMANCE:")
            print("-" * 60)
            
            sorted_rules = sorted(
                profile.rule_profiles.values(),
                key=lambda r: r.execution_time,
                reverse=True
            )
            
            print(f"{'Rule ID':<15} {'Avg Time (ms)':<15} {'Evaluations':<12} {'Matches':<8} {'Errors':<6}")
            print("-" * 60)
            
            for rule in sorted_rules:
                avg_time_ms = (rule.execution_time / max(rule.evaluation_count, 1)) * 1000
                print(f"{str(rule.rule_id):<15} {avg_time_ms:<15.3f} {rule.evaluation_count:<12} {rule.match_count:<8} {rule.error_count:<6}")
        
        print("=" * 60)


class RuleDebugger:
    """Debugging utilities for rule development."""
    
    @staticmethod
    def explain_rule_execution(rule_text: str, data: Dict[str, Any], 
                             result: bool, variables: Dict[str, Any] = None):
        """Explain why a rule succeeded or failed."""
        print(f"\nRule: {rule_text}")
        print(f"Result: {'MATCHED' if result else 'NO MATCH'}")
        print(f"Data: {data}")
        
        if variables:
            print("Variables available:")
            for var, value in variables.items():
                print(f"  {var} = {value}")
    
    @staticmethod
    def trace_rule_variables(rule_text: str, schema_ast) -> List[str]:
        """Extract and return all variables referenced in a rule."""
        variables = []
        words = rule_text.split()
        
        for word in words:
            if word.replace('.', '').replace('_', '').isalnum() and not word.isdigit():
                if word not in ['and', 'or', 'not', 'in', 'true', 'false']:
                    variables.append(word)
        
        return list(set(variables))


_global_profiler = RuleProfiler()

def get_profiler() -> RuleProfiler:
    """Get the global rule profiler instance."""
    return _global_profiler