# amino

A toolkit and DSL for classification rules engines—sometimes called expert systems. Much focus has been given toward AI and machine learning tooling to help take humans out of the loop. However, there are exist a wide variety of current and future applications for custom rules engines.

Amino inverts the problem space by placing a schema at the center, not unlike how GraphQL has done so for APIs.

## Features

Amino has three key components:
- **Schema definition**: Like GraphQL or Protobuf for the data space it operates on
- **DSL**: A pre-built, small and extensible domain-specific language for conditional logic
- **Runtime**: Fast evaluation of rules against data sets

## Quick Start

### Installation

```bash
pip install amino
```

### Development Installation

```bash
git clone https://github.com/yourusername/amino.git
cd amino
pip install -e .[dev]
```

### Requirements

- Python 3.10+

### Your First Schema

Create a schema file `schema.amn`:
```
amount: Int
state_code: Str
```

Then use it in Python:
```python
import amino

# Load schema
amn = amino.load_schema("schema.amn")

# Evaluate a simple rule
result = amn.eval("amount > 0 and state_code = 'CA'", {
    "amount": 100, 
    "state_code": "CA"
})
print(result)  # True
```


## How to Use


### Basic Example

Declare a schema

schema.amn
```
amount: Int
state_code: Str
```

Import schema and evaluate a rule to see if it matches the matching variables passed in.

```
>>> import amino
>>> amn = amino.load_schema("schema.amn")
>>> amn.eval("amount > 0 and state_code = 'CA'", {"amount": 100, "state_code": "CA"})
True
>>> amn.eval("amount > 0 and state_code = 'CA'", {"amount": 0, "state_code": "CA"})
False
```


### More likely Runtime Example

Declare a schema

schema.amn
```
amount: Int
state_code: Str
```

Import schema and use it in your code. ( Note: You don't need to specify `id` for just one data set or one rule, but
you do need an `id` for more than one of either, and each `id` must unique. )

```
>>> import amino
>>> amn = amino.load_schema("schema.amn")
>>> compiled = amn.compile(
...    [
...        {"id": 1, "rule":"amount > 0 and state_code = 'CA'"},
...        {"id": 2, "rule":"amount > 10 and state_code = 'CA'"},
...        {"id": 3, "rule":"amount >= 100"},
...    ]
... )
>>> compiled.eval([
...    {"id": 45, "amount": 100, "state_code": "CA"},
...    {"id": 46, "amount": 50, "state_code": "CA"},
...    {"id": 47, "amount": 100, "state_code": "NY"},
...    {"id": 48, "amount": 10, "state_code": "NY"},
... ])

[
    {"id": 45, "results": [1, 2, 3]}, 
    {"id": 46, "results": [1, 2]},
    {"id": 47, "results": [3]},
    {"id": 48, "results": []},
]
```

We also support returning just one match.

```
>>> import amino
>>> amn = amino.load_schema("schema.amn")
>>> compiled = amn.compile(
...    [
...        {"id": 1, "rule":"amount > 0 and state_code = 'CA'", "ordering": 3},
...        {"id": 2, "rule":"amount > 10 and state_code = 'CA'", "ordering": 2},
...        {"id": 3, "rule":"amount >= 100", "ordering": 1},
...    ],
...    match={"option": "first", "key": "ordering", "ordering": "asc"}
... )
>>> compiled.eval([
...    {"id": 100, "amount": 100, "state_code": "CA"},
...    {"id": 101, "amount": 50, "state_code": "CA"},
...    {"id": 102, "amount": 50, "state_code": "NY"},
... ])

[
    {"id": 100, "results": [3]}, 
    {"id": 101, "results": [2]},
    {"id": 102, "results": []}
]
```


## Schema Elaboration


### Comments
We support comments with the `#` symbol. Anything to the right of the comment symbol is disregarded at runtime.

schema.amn
```
# this is a comment
amount: Int  # this is too
state_code: Str
```


### Structs
We support C-like structs with the `struct` keyword

schema.amn
```
struct applicant {
    state_code: Str,
}

struct loan {
    amount: Int
}

```


```
>>> data = {"loan": {"amount": 100}, "applicant": "state_code": "CA"
>>> rule = "loan.amount > 0 and applicant.state_code = 'CA'"
>>> amn.eval(rule, data)
True
```


### Functions
We support function declarations; you declare the inputs and output, and you 
implement the function in your own language. These aren't true functions. It may be more appropriate to call it a 
foreign function interface declaration. That is, amino is the host language, and your implementation language in your
project (e.g. Python, TypeScript, etc.) is the guest language.



schema.amn
```
amount: Int
state_code: Str

smallest_number: (first: Int, second: Int) -> Int

```

Note the passing of `min` and passing it into the `funcs` argument while loading the schema. This provides the DSL host language access to calling out to the guest function `min` while the host function in the DSL uses `smallest_number`.

```
>>> amn = amino.load_schema("schema.amn", funcs={'smallest_number': min})
>>> data = {"amount": 100, "state_code": "CA"}
>>> rule = "smallest_number(amount, 1000) < 1000 and state_code = 'CA'"
>>> amn.eval(rule, data)
True
```

#### Function Parameters

Functions require named parameters that clearly document their purpose:

schema.amn
```
amount: Int
state_code: Str

calculate_tax: (amount: Int, rate: Float) -> Float

```

Note the passing of `calculate_tax` and passing it into the `funcs` argument while loading the schema.

```
>>> def tax_calculator(amount, rate):
...     return amount * rate
>>> amn = amino.load_schema("schema.amn", {'calculate_tax': tax_calculator})
>>> data = {"amount": 100, "state_code": "CA"}
>>> rule = "calculate_tax(amount, 0.08) > 5.0 and state_code = 'CA'"
>>> amn.eval(rule, data)
True
```



### Lists

We support homogenous or heterogeneous arrays with the `list` keyword

schema.amn
```
state_code: Str
amounts: List[Int]
things: List[Int|Str|Float]
```



```
>>> data = {"amount": 100, "state_code": "CA", "things": ["CA", 1, 1.0] }
>>> rule = "amount > 0 and state_code = 'CA' or state_code in things"
>>> amn.eval(rule, data)
True
```

## Operators

Built-in operators.

```
!=
=
>
<
>=
<=
in
not in
not
and
or

```

## Documentation

- [Development Guide](DEVELOPMENT.md) - Setup, testing, and contribution guidelines
- [Examples](examples/README.md) - Additional examples and use cases
