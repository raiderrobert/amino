# amino
A toolkit for custom rules engines

Amino has three parts:
- a schema definition like graphql or protobuf for the data space it operates on
- a pre-built small and extensible DSL for conditional logic to operate on these schemas
- a runtime to evaluate the rules against the data set


## How to Use


### Basic Example

Declare a schema

schema.amn
```
amount: int
state_code: str
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
amount: int
state_code: str
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
amount: int  # this is too
state_code: str
```


### Structs
We support C-like structs with the `struct` keyword

schema.amn
```
struct applicant {
    state_code: str,
}

struct loan {
    amount: int
}

```


```
>>> data = {"loan": {"amount": 100}, "applicant": "state_code": "CA"
>>> rule = "loan.amount > 0 and applicant.state_code = 'CA'"
>>> amn.eval(rule, data)
True
```


### Functions
We support function declarations with the keyword `func`, wherein you declare the inputs and output, and you 
implement the function in your own language. These aren't true functions. It may be more appropriate to call it a 
foreign function interface declaration. That is, amino is the host language, and your implementation language in your
project (e.g. Python, TypeScript, etc.) is the guest language.



schema.amn
```
amount: int
state_code: str

smallest_number: func(int, int) -> int

```


```
>>> data = {"amount": 100, "state_code": "CA"}
>>> rule = "biggest_number(amount, 1000) < 1000 and state_code = 'CA'"
>>> amn.eval(rule, data)
True
```

#### Default Arguments

Functions also support more complex cases, such as referencing other variables in the schema:

schema.amn
```
COMPANY_MAX_LOAN_AMT: int = 100_000

loan_amount: int
approved_amount: int
state_code: str

within_tolerances: func(COMPANY_MAX_LOAN_AMT, loan_amount, approved_amount)()

```


```
>>> data = {"amount": 100, "state_code": "CA"}
>>> rule = "within_tolerances(_,_,90_000) and state_code = 'CA'"
>>> amn.eval(rule, data)
True
```



### Lists

We support homogenous or heterogeneous arrays with the `list` keyword

schema.amn
```
state_code: str
amounts: list[int]
things: list[int|str|float]
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


### Examples of Built-In Behavior

We support homogenous or heterogeneous arrays with the `list` keyword

schema.amn
```
amount: int
state_code: str
```



```
>>> data = {"amount": 100, "state_code": "CA", "things": ["CA", 1, 1.0] }
>>> rule = "amount > 0 and state_code = 'CA' or state_code in things"
>>> amn.eval(rule, data)
True
```
