# amino
A framework to build domain specific languages


## How to Use


### Basic Examples

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


##

schema.amn
```
amount: int
state_code: str
```