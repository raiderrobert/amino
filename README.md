# amino

A schema-first classification rules engine. 

Amino is for deterministic, auditable, human-authored rules that need to be frequently updated by end users.

Amino puts a typed schema at the center of the rules pipeline, not unlike how GraphQL does for APIs, so rules are compiled against a stable type system rather than evaluated against raw, untyped data.


## Features

- **Schema definition**: `.amn` files define fields, types, structs, constraints, and function signatures
- **Typed DSL**: a small, extensible expression language with compile-time type checking
- **Four match modes**: all, first, inverse, score
- **Extensible**: register custom types and operators before first use
- **Hot-swappable rules**: `update_rules()` atomically replaces compiled rules without restarting

## Installation

```bash
pip install amino
```

### Development Installation

```bash
git clone https://github.com/raiderrobert/amino.git
cd amino
uv sync
uv run pytest
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

Evaluate a rule against a decision:

```python
import amino

engine = amino.load_schema("auto_loan.amn")

result = engine.eval(
    rules=[{"id": "decline", "rule": "credit_score < 600 or income < 30000"}],
    decision={"amount": 75000, "state_code": "CA", "credit_score": 580, "income": 45000},
)
print(result.matched)  # ['decline']
```

## Compiling Rules for Repeated Evaluation

For production systems, compile a rule set once and evaluate it against many decisions:

```python
compiled = engine.compile(
    rules=[
        {"id": "high_risk",   "rule": "credit_score < 500",                          "ordering": 1},
        {"id": "ca_income",   "rule": "state_code = 'CA' and income < 50000",         "ordering": 2},
        {"id": "amount_risk", "rule": "credit_score < 650 and amount > 40000",        "ordering": 3},
    ],
    match={"mode": "first", "key": "ordering", "order": "asc"},
)

results = compiled.eval([
    {"id": "app_1", "amount": 45000, "state_code": "CA", "credit_score": 480, "income": 55000},
    {"id": "app_2", "amount": 65000, "state_code": "TX", "credit_score": 720, "income": 80000},
])
# app_1 → matched: ['high_risk']  (first match, ordering 1)
# app_2 → matched: []
```

## Match Modes

The `match` dict controls how rule results are aggregated into a `MatchResult`:

- **`all`** (default) — return every rule that matches: `{'mode': 'all'}`
- **`first`** — return only the first match by ordering: `{'mode': 'first', 'key': 'ordering', 'order': 'asc'}`
- **`inverse`** — return every rule that does NOT match: `{'mode': 'inverse'}`
- **`score`** — aggregate numeric or boolean rule results: `{'mode': 'score', 'aggregate': 'sum', 'threshold': 0.7}`

See [docs/rule-expression.md](docs/rule-expression.md) for the full match mode reference.

## Extensibility

Custom types and operators are registered before the first `compile()` or `eval()` call. After first use, the engine is frozen and further registration raises `EngineAlreadyFrozenError`.

```python
engine = amino.load_schema("schema.amn")

# Register a custom type — usable as a field type in the schema
engine.register_type('ipv4', base='Str', validator=is_valid_ipv4)

# Register a custom keyword operator with compile-time type checking
engine.register_operator(
    keyword='precedes',
    fn=event_precedes,
    binding_power=40,
    input_types=('Str', 'Str'),
    return_type='Bool',
)

# Now compile or eval — registries are frozen from this point on
compiled = engine.compile(rules=[...])
```

See [docs/rule-expression.md](docs/rule-expression.md) for symbolic operators, presets, and binding powers.

## Schema Reference

Schema files use the `.amn` extension. Fields are declared as `name: Type`. Comments use `#`.

```
# Auto loan application schema
amount: Int
state_code: Str
credit_score: Int {min: 300, max: 850}
income: Int
tags: List[Str]
email: Str?   # optional field
```

**Primitive types**: `Int`, `Float`, `Str`, `Bool`

**Structs** organize nested data (PascalCase by convention):

```
struct Address {
    street: Str,
    city: Str,
    country: Str
}

struct Customer {
    id: Str,
    name: Str,
    billing_address: Address,
    shipping_address: Address?
}
```

Struct fields are accessed in rules with dot notation: `customer.billing_address.city = 'Austin'`

**Constraints** are declared inline and enforced at evaluation time:

```
age: Int {min: 18, max: 120}
username: Str {minLength: 3, maxLength: 20}
status: Str {oneOf: ["active", "inactive", "pending"]}
```

**Function declarations** integrate external logic, ML models, or APIs:

```
toxicity_score: (text: Str) -> Float
calculate_discount: (tier: Str, amount: Float) -> Float
```

Implement and register them in Python:

```python
engine = amino.load_schema("schema.amn", funcs={
    'toxicity_score': ml_model.predict,
    'calculate_discount': calculate_discount,
})
```

See [docs/schema-language.md](docs/schema-language.md) for the full schema reference including optional fields, union-typed lists, constraints, and custom types.

## FAQ

**Why would I use this instead of a programming language?**

Programming languages are designed for general-purpose tasks. Rules engines are for end users to customize a system — the bridge between a few configuration options and a full-fledged programming language.

If you find yourself in a situation where users need to write complex rules to govern system behavior, and you expect those rules to be frequently updated by non-engineers, a rules engine is a better fit than a programming language.

## Real-World Examples

- **[E-commerce Pricing](examples/ecommerce/)** — Dynamic discounts and promotions
- **[Content Moderation](examples/content_moderation/)** — Safety systems
- **[IoT Automation](examples/iot_automation/)** — Smart home device coordination

Each example includes complete schemas, Python implementations, and tests.

## Documentation

- [Architecture](docs/architecture.md) — pipeline, engine lifecycle, design intent
- [Schema Language](docs/schema-language.md) — field types, structs, constraints
- [Rule Expression Language](docs/rule-expression.md) — operators, match modes, extensibility
- [API Reference](docs/api.md) — full public API
- [Examples](examples/README.md) — complete working examples
- [Development Guide](DEVELOPMENT.md) — setup, testing, contribution guidelines
