# amino

A toolkit and DSL for classification rules engines—sometimes called expert systems. Much focus has been given toward AI and machine learning tooling to help take humans out of the loop. However, there are exist a wide variety of current and future applications for custom rules engines.

Amino inverts the problem space by placing a schema at the center, not unlike how GraphQL has done so for APIs.

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
git clone https://github.com/yourusername/amino.git
cd amino
pip install -e .[dev]
```

**Requirements**: Python 3.10+

## Quick Start

Create a schema file `user_policy.amn`:
```
struct user {
    age: Int,
    location: Str,
    verified: Bool
}

can_access_premium: (age: Int) -> Bool
```

Use it in Python:
```python
import amino

# Load schema with custom function
amn = amino.load_schema("user_policy.amn", funcs={
    'can_access_premium': lambda age: age >= 18
})

# Evaluate a rule
result = amn.eval(
    "user.age > 21 and user.location = 'CA' and can_access_premium(user.age)",
    {"user": {"age": 25, "location": "CA", "verified": True}}
)
print(result)  # True
```

## Multiple Rules and Priority

For production systems, compile multiple rules for batch evaluation:

```python
# First define schema with needed structs
schema = """
struct customer {
    tier: Str
}
struct order {
    total: Float,
    item_count: Int  
}
struct product {
    inventory_count: Int
}
"""

# Then compile rules
pricing_rules = amn.compile([
    {"id": "gold_discount", "rule": "customer.tier = 'gold' and order.total > 100", "ordering": 1},
    {"id": "bulk_discount", "rule": "order.item_count > 10", "ordering": 2},
    {"id": "clearance", "rule": "product.inventory_count < 5", "ordering": 3}
])

# Evaluate against multiple orders
results = pricing_rules.eval([
    {"id": "order_1", "customer": {"tier": "gold"}, "order": {"total": 150, "item_count": 3}},
    {"id": "order_2", "customer": {"tier": "silver"}, "order": {"total": 50, "item_count": 15}}
])
# Returns: [{"id": "order_1", "results": ["gold_discount"]}, {"id": "order_2", "results": ["bulk_discount"]}]
```

### First Match Priority

Use `match="first"` to return only the highest priority rule:

```python
# Schema includes content struct and toxicity function
schema = """
struct content {
    text: Str
}
toxicity_score: (text: Str) -> Float
"""

safety_rules = amn.compile([
    {"id": "immediate_block", "rule": "toxicity_score(content.text) > 0.9", "ordering": 1},
    {"id": "flag_review", "rule": "toxicity_score(content.text) > 0.7", "ordering": 2}
], match={"option": "first", "key": "ordering", "ordering": "asc"})
```


## Schema Reference

### Comments
Use `#` for comments - everything after is ignored:

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

## Real-World Examples

Amino supports rule engines across use cases:

- **[E-commerce Pricing](examples/ecommerce/)** - Dynamic discounts and promotions
- **[Content Moderation](examples/content_moderation/)** - Safety systems  
- **[IoT Automation](examples/iot_automation/)** - Smart home device coordination

Each example includes complete schemas, Python implementations, and tests.

## Documentation

- [Examples](examples/README.md) - Complete working examples and use cases
- [Development Guide](DEVELOPMENT.md) - Setup, testing, and contribution guidelines
