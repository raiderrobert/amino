#!/usr/bin/env python3
"""
Example validation runner for Amino examples.

This script validates that all examples work correctly by:
1. Running their main functionality to ensure no crashes
2. Running comprehensive test suites
3. Reporting results and any issues found
"""

import sys
import os
import subprocess
import importlib.util
from pathlib import Path


class ExampleValidator:
    """Validates Amino examples through execution and testing."""
    
    def __init__(self):
        self.examples_dir = Path(__file__).parent
        self.results = {
            'passed': [],
            'failed': [],
            'errors': []
        }
    
    def validate_example_execution(self, example_name: str) -> bool:
        """Test that an example can be executed without crashing."""
        example_path = self.examples_dir / example_name
        main_file = self._find_main_file(example_path)
        
        if not main_file:
            self.results['errors'].append(f"{example_name}: No main file found")
            return False
        
        try:
            # Run the example using uv run and add the project root to Python path
            relative_main = f"examples/{example_name}/{main_file.name}"
            project_root = str(self.examples_dir.parent)
            
            # Set PYTHONPATH to include the project root so 'amino' can be imported
            env = os.environ.copy()
            pythonpath = env.get('PYTHONPATH', '')
            if pythonpath:
                env['PYTHONPATH'] = f"{project_root}:{pythonpath}"
            else:
                env['PYTHONPATH'] = project_root
            
            result = subprocess.run([
                "uv", "run", "python3", relative_main
            ], capture_output=True, text=True, cwd=project_root, timeout=30, env=env)
            
            if result.returncode == 0:
                self.results['passed'].append(f"{example_name}: Execution successful")
                return True
            else:
                # Extract error message from stderr
                error_msg = result.stderr.strip() if result.stderr else "Unknown execution error"
                self.results['failed'].append(f"{example_name}: Execution failed - {error_msg}")
                return False
            
        except subprocess.TimeoutExpired:
            self.results['failed'].append(f"{example_name}: Execution timed out")
            return False
        except Exception as e:
            self.results['failed'].append(f"{example_name}: Execution error - {str(e)}")
            return False
    
    def _find_main_file(self, example_path: Path) -> Path | None:
        """Find the main Python file for an example."""
        # Common main file patterns
        patterns = [
            f"{example_path.name}.py",
            "main.py", 
            f"{example_path.name.replace('_', '')}.py"
        ]
        
        # Look for specific files based on example name
        if example_path.name == "ecommerce":
            patterns.insert(0, "pricing_engine.py")
        elif example_path.name == "content_moderation":
            patterns.insert(0, "moderation_system.py")
        elif example_path.name == "iot_automation":
            patterns.insert(0, "smart_home.py")
        
        for pattern in patterns:
            candidate = example_path / pattern
            if candidate.exists():
                return candidate
        
        return None
    
    def run_example_tests(self, example_name: str) -> bool:
        """Run pytest tests for an example."""
        example_dir = self.examples_dir / example_name
        test_files = list(example_dir.glob("test_*.py"))
        
        if not test_files:
            self.results['errors'].append(f"{example_name}: No test files found")
            return False
        
        try:
            # Run pytest for all test files in the example directory using uv
            relative_path = f"examples/{example_name}"
            result = subprocess.run([
                "uv", "run", "python3", "-m", "pytest", 
                relative_path, 
                "-v", "--tb=short", "-q"
            ], capture_output=True, text=True, cwd=str(self.examples_dir.parent))
            
            if result.returncode == 0:
                # Count passed tests from the summary line
                lines = result.stdout.split('\n')
                import re
                passed_count = 0
                for line in lines:
                    if 'passed in' in line and re.search(r'(\d+) passed', line):
                        match = re.search(r'(\d+) passed', line)
                        passed_count = int(match.group(1))
                        break
                
                if passed_count == 0:
                    # Fallback: count individual PASSED lines  
                    passed_count = len([line for line in lines if '::' in line and 'PASSED' in line])
                
                self.results['passed'].append(f"{example_name}: {passed_count} tests passed")
                return True
            else:
                # Extract error information
                error_msg = result.stdout + "\n" + result.stderr
                self.results['failed'].append(f"{example_name}: Tests failed\n{error_msg}")
                return False
                
        except Exception as e:
            self.results['failed'].append(f"{example_name}: Test execution error - {str(e)}")
            return False
    
    def validate_schema_files(self) -> bool:
        """Validate that schema files are present and parseable."""
        schema_issues = []
        
        for example_dir in self.examples_dir.iterdir():
            if not example_dir.is_dir() or example_dir.name.startswith('.'):
                continue
            
            schema_file = example_dir / "schema.amino"
            if not schema_file.exists():
                schema_issues.append(f"{example_dir.name}: Missing schema.amino file")
                continue
            
            try:
                # Basic syntax check - just try to read the file
                content = schema_file.read_text()
                if len(content.strip()) == 0:
                    schema_issues.append(f"{example_dir.name}: Empty schema file")
                else:
                    # Check for basic schema elements
                    if 'struct' not in content and 'fn' not in content:
                        schema_issues.append(f"{example_dir.name}: Schema file appears incomplete")
            except Exception as e:
                schema_issues.append(f"{example_dir.name}: Schema file read error - {str(e)}")
        
        if schema_issues:
            self.results['errors'].extend(schema_issues)
            return False
        
        self.results['passed'].append("Schema validation: All schema files present and readable")
        return True
    
    def validate_all_examples(self) -> dict:
        """Run full validation on all examples."""
        print("🧪 Validating Amino Examples")
        print("=" * 50)
        
        # Find all example directories
        example_dirs = [
            d for d in self.examples_dir.iterdir() 
            if d.is_dir() and not d.name.startswith('.')
        ]
        
        if not example_dirs:
            print("❌ No example directories found")
            return self.results
        
        print(f"Found {len(example_dirs)} examples: {[d.name for d in example_dirs]}")
        print()
        
        # Validate schemas first
        print("1️⃣ Validating schema files...")
        self.validate_schema_files()
        print()
        
        # Validate each example
        for example_dir in example_dirs:
            example_name = example_dir.name
            print(f"2️⃣ Validating {example_name} execution...")
            self.validate_example_execution(example_name)
            
            print(f"3️⃣ Running {example_name} tests...")
            self.run_example_tests(example_name)
            print()
        
        return self.results
    
    def print_results(self):
        """Print validation results in a readable format."""
        print("📋 Validation Results")
        print("=" * 50)
        
        if self.results['passed']:
            print("✅ PASSED:")
            for item in self.results['passed']:
                print(f"   • {item}")
            print()
        
        if self.results['errors']:
            print("⚠️ ERRORS:")
            for item in self.results['errors']:
                print(f"   • {item}")
            print()
        
        if self.results['failed']:
            print("❌ FAILED:")
            for item in self.results['failed']:
                print(f"   • {item}")
            print()
        
        # Summary
        total_passed = len(self.results['passed'])
        total_failed = len(self.results['failed']) 
        total_errors = len(self.results['errors'])
        
        print("📊 SUMMARY:")
        print(f"   ✅ Passed: {total_passed}")
        print(f"   ❌ Failed: {total_failed}")
        print(f"   ⚠️ Errors: {total_errors}")
        
        if total_failed == 0 and total_errors == 0:
            print("\n🎉 All examples validated successfully!")
            return True
        else:
            print(f"\n💥 {total_failed + total_errors} issues found")
            return False


def main():
    """Main validation entry point."""
    validator = ExampleValidator()
    
    # Check if specific example was requested
    if len(sys.argv) > 1:
        example_name = sys.argv[1]
        print(f"🎯 Validating specific example: {example_name}")
        print("=" * 50)
        
        validator.validate_example_execution(example_name)
        validator.run_example_tests(example_name)
        validator.print_results()
    else:
        # Validate all examples
        validator.validate_all_examples()
        success = validator.print_results()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()