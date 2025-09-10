#!/usr/bin/env python3
"""Basic test script for amino functionality."""

def test_schema_parsing():
    """Test basic schema parsing."""
    from amino.schema.parser import SchemaParser
    
    try:
        parser = SchemaParser('amount: int')
        ast = parser.parse()
        print("✅ Schema parsing works")
        print(f"   Fields: {[f.name + ':' + f.field_type.value for f in ast.fields]}")
    except Exception as e:
        print(f"❌ Schema parsing failed: {e}")
        import traceback
        traceback.print_exc()

def test_amino_import():
    """Test amino module import."""
    try:
        import amino
        print("✅ Amino import works")
    except Exception as e:
        print(f"❌ Amino import failed: {e}")
        import traceback
        traceback.print_exc()

def test_basic_usage():
    """Test basic amino usage."""
    try:
        import amino
        amn = amino.load_schema('amount: int\nstate_code: str')
        result = amn.eval('amount > 0', {'amount': 100, 'state_code': 'CA'})
        print(f"✅ Basic usage works: {result}")
        
        # Test complex rule
        result2 = amn.eval('amount > 0 and state_code = "CA"', {'amount': 100, 'state_code': 'CA'})
        print(f"✅ Complex rule works: {result2}")
        
        # Test false case
        result3 = amn.eval('amount > 0 and state_code = "CA"', {'amount': 0, 'state_code': 'CA'})
        print(f"✅ False case works: {result3}")
        
    except Exception as e:
        print(f"❌ Basic usage failed: {e}")
        import traceback
        traceback.print_exc()

def test_batch_processing():
    """Test batch processing like README examples."""
    try:
        import amino
        amn = amino.load_schema('amount: int\nstate_code: str')
        compiled = amn.compile([
            {"id": 1, "rule": "amount > 0 and state_code = 'CA'"},
            {"id": 2, "rule": "amount > 10 and state_code = 'CA'"},
            {"id": 3, "rule": "amount >= 100"},
        ])
        
        results = compiled.eval([
            {"id": 45, "amount": 100, "state_code": "CA"},
            {"id": 46, "amount": 50, "state_code": "CA"},
            {"id": 47, "amount": 100, "state_code": "NY"},
            {"id": 48, "amount": 10, "state_code": "NY"},
        ])
        
        print("✅ Batch processing works:")
        for result in results:
            print(f"   {result}")
            
    except Exception as e:
        print(f"❌ Batch processing failed: {e}")
        import traceback
        traceback.print_exc()

def test_ordering():
    """Test ordering feature from README."""
    try:
        import amino
        amn = amino.load_schema('amount: int\nstate_code: str')
        compiled = amn.compile([
            {"id": 1, "rule": "amount > 0 and state_code = 'CA'", "ordering": 3},
            {"id": 2, "rule": "amount > 10 and state_code = 'CA'", "ordering": 2},
            {"id": 3, "rule": "amount >= 100", "ordering": 1},
        ], match={"option": "first", "key": "ordering", "ordering": "asc"})
        
        results = compiled.eval([
            {"id": 100, "amount": 100, "state_code": "CA"},
            {"id": 101, "amount": 50, "state_code": "CA"},
            {"id": 102, "amount": 50, "state_code": "NY"},
        ])
        
        print("✅ Ordering works:")
        for result in results:
            print(f"   {result}")
            
    except Exception as e:
        print(f"❌ Ordering failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Testing Amino implementation...")
    test_amino_import()
    test_schema_parsing() 
    test_basic_usage()
    test_batch_processing()
    test_ordering()