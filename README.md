# amino

A toolkit and DSL for classification rules engines—sometimes called expert systems. Much focus has been given toward AI and machine learning tooling to help take humans out of the loop. However, there are exist a wide variety of current and future applications for custom rules engines.

Amino inverts the problem space by placing a schema at the center, not unlike how GraphQL has done so for APIs.

## Motivation

Amino is designed to be a safe, flexible, and extensible rules engine that can be easily integrated into existing systems. It provides a simple and intuitive way to define and evaluate rules against data sets, making it a great choice for applications that require end users to create custom logic and decision-making.

## Features

Amino has three key components:
- **Schema definition**: Like GraphQL or Protobuf for the data space it operates on
- **DSL**: A pre-built, small and extensible domain-specific language for conditional logic
- **Runtime**: Fast evaluation of rules against data sets

## Installation

```bash
pip install amino
```

### Development Installation

```bash
git clone https://github.com/raiderrobert/amino.git
cd amino
pip install -e .[dev]
```

**Requirements**: Python 3.10+

## Quick Start

Create a schema file `auto_loan.amn`:
```
amount: Int
state_code: Str
credit_score: Int
income: Int
```

Use it in Python:
```python
import amino

# Load schema
amn = amino.load_schema("auto_loan.amn")

# Check if loan should be auto-declined
decline = amn.eval(
    "amount > 80000 or credit_score < 600 or income < 30000", 
    {"amount": 75000, "state_code": "CA", "credit_score": 580, "income": 45000}
)
print(decline)  # True - declined due to low credit score
```

## Multiple Rules and Priority

For production systems, compile multiple rules:

```python
# Auto loan decline rules with different priorities
decline_rules = amn.compile([
    {"id": "high_risk", "rule": "credit_score < 500", "ordering": 1},
    {"id": "ca_income", "rule": "state_code = 'CA' and income < 50000", "ordering": 2}, 
    {"id": "tx_amount", "rule": "state_code = 'TX' and amount > 60000", "ordering": 3},
    {"id": "general_risk", "rule": "credit_score < 650 and amount > 40000", "ordering": 4}
])

# Evaluate multiple loan applications
applications = [
    {"id": "app_1", "amount": 45000, "state_code": "CA", "credit_score": 480, "income": 55000},
    {"id": "app_2", "amount": 65000, "state_code": "TX", "credit_score": 720, "income": 80000},  
    {"id": "app_3", "amount": 35000, "state_code": "NY", "credit_score": 640, "income": 45000}
]

results = decline_rules.eval(applications)
# Returns: [
#   {"id": "app_1", "results": ["high_risk"]},
#   {"id": "app_2", "results": ["tx_amount"]}, 
#   {"id": "app_3", "results": []}
# ]
```

### First Match Priority

Use `match="first"` to return only the highest priority decline reason:

```python
decline_rules = amn.compile([
    {"id": "fraud_risk", "rule": "credit_score < 400", "ordering": 1},
    {"id": "income_risk", "rule": "income < 25000", "ordering": 2},
    {"id": "amount_risk", "rule": "amount > 100000", "ordering": 3}
], match={"option": "first", "key": "ordering", "ordering": "asc"})

# Returns only the first matching decline reason per application
```


## Schema Reference

### Comments
Use `#` for comments. Everything one the same line after the `#` is ignored:

```
# Schema for user validation
user_age: Int  # Must be positive
location: Str
```

### Data Structures

**Basic types**: `Int`, `Float`, `Str`, `Bool`

**Structs** organize related data:
```
struct customer {
    id: Str,
    tier: Str,    # "gold", "silver", "bronze"  
    verified: Bool
}

struct order {
    total: Float,
    item_count: Int
}
```

Usage:
```python
data = {
    "customer": {"id": "123", "tier": "gold", "verified": True},
    "order": {"total": 150.0, "item_count": 3}
}
rule = "customer.tier = 'gold' and order.total > 100"
```

**Lists** support homogeneous or mixed types:
```
recent_purchases: List[Float]
mixed_data: List[Int|Str|Bool]
```

### Functions

Declare external functions to integrate business logic, ML models, or APIs:

```
# ML integration
toxicity_score: (text: Str) -> Float
sentiment_analysis: (content: Str, language: Str) -> Str

# Business logic  
calculate_discount: (tier: Str, amount: Float) -> Float
is_holiday_season: (date: Str) -> Bool
```

Implement in Python:
```python
def calculate_shipping(zip_code: str, weight: float) -> float:
    # Your shipping logic here
    return base_rate * weight * zone_multiplier(zip_code)

amn = amino.load_schema("schema.amn", funcs={
    'calculate_shipping': calculate_shipping,
    'toxicity_score': ml_model.predict
})
```

## Operators

**Comparison**: `=`, `!=`, `>`, `<`, `>=`, `<=`  
**Logical**: `and`, `or`, `not`  
**Membership**: `in`, `not in`

```python
# Examples
"customer.tier in ['gold', 'platinum']"
"order.total >= 100 and not customer.new_user" 
"product.category != 'restricted'"
```

## FAQ

** Why would I use this instead of a programming language?**
 
Programming languages are designed for general purposes tasks. Rules engines are for end users to customize a system. It's the bridge between a few configuration options and a full-fledged programming language.

If you find yourself in a situation where users want to write complex rules to govern system behavior, and you expect those rules to be frequently updated by end users, then it's likely that a rules engine is a better fit than a programming language.


## Real-World Examples

Amino supports rule engines across use cases:

- **[E-commerce Pricing](examples/ecommerce/)** - Dynamic discounts and promotions
- **[Content Moderation](examples/content_moderation/)** - Safety systems  
- **[IoT Automation](examples/iot_automation/)** - Smart home device coordination

Each example includes complete schemas, Python implementations, and tests.

## Documentation

- [Examples](examples/README.md) - Complete working examples and use cases
- [Development Guide](DEVELOPMENT.md) - Setup, testing, and contribution guidelines
