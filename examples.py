"""
Example Amino usage and tests.
"""

import amino

def main():
    # Load schema
    amn = amino.load_schema("example.amn")

    # Try a simple rule
    data = {
        "amount": 100,
        "state_code": "CA"
    }
    result = amn.eval("amount > 0 and state_code = 'CA'", data)
    print(f"Single rule evaluation: {result}")  # Should print True

    # Try multiple rules
    rules = [
        {
            'id': 1,
            'rule': "amount > 0 and state_code = 'CA'",
            'ordering': 3
        },
        {
            'id': 2,
            'rule': "amount > 10 and state_code = 'CA'",
            'ordering': 2
        },
        {
            'id': 3,
            'rule': "amount >= 100",
            'ordering': 1
        }
    ]

    # Compile rules
    match_config = {
        'option': 'first',
        'key': 'ordering',
        'ordering': 'asc'
    }
    compiled = amn.compile(rules, match_config)

    # Evaluate against multiple datasets
    datasets = [
        {'id': 45, 'amount': 100, 'state_code': 'CA'},
        {'id': 46, 'amount': 50, 'state_code': 'CA'},
        {'id': 47, 'amount': 100, 'state_code': 'NY'},
    ]

    results = compiled.eval(datasets)
    print("\nMultiple rule evaluation:")
    for result in results:
        print(result)

if __name__ == '__main__':
    main()