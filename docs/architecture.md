# Architecture

## What amino is

Amino is a schema-first classification rules engine. The schema defines the type system — fields, types, structs, and functions. Rules are conditional expressions compiled against that schema. Decisions are data items (dicts) evaluated against compiled rules. The engine enforces a clean separation between these three concerns, provides a correct type system with two enforcement modes, and supports an extensible operator and type model.

## Pipeline

```
Schema text  ──▶  Schema Parser  ──▶  SchemaAST  ──▶  Schema Validator
                  (static PEG)                         (refs, circularity,
                                                        duplicate names)
                                                             │
                                                             ▼
                                                       SchemaRegistry
                                                       (fast lookup,
                                                        export)
                                                             │
                  ┌──────────────────────────────────────────┤
                  │ fixed for engine lifetime                 │
                  ▼                                           │
           OperatorRegistry  ◀── register_operator()         │
           TypeRegistry      ◀── register_type()             │
           FunctionRegistry  ◀── add_function()              │
                  │ (all frozen after first compile/eval)     │
                  ▼                                           │
Rule text  ──▶  Rule Parser  ──▶  RuleAST  ──▶  TypedCompiler  ──▶  CompiledRule
               (Pratt parser,                    (type resolution
                dynamic op table)                + optimization
                                                 + codegen,
                                                 one AST walk)

Decision dict  ──▶  DecisionValidator  ──▶  Evaluator  ──▶  Matcher  ──▶  MatchResult
                     (schema + constraints,    (runs              (all / first /
                      strict / loose mode)     CompiledRules)      inverse / score)
```

## Three data groups

The system is modeled around three data groups with fundamentally different lifecycles:

- **Schema** — defines the type system: fields, types, structs, function signatures. Fixed for the lifetime of an engine instance.
- **Rules** — conditional logic compiled against the schema. Hot-swappable at runtime without restarting the process.
- **Decisions** — input data items evaluated against compiled rules. Always dynamic; never cached.

These are treated as separate concerns in the implementation because they have different stability characteristics. Schema changes are structural changes to the data model — a field removal or type change invalidates all compiled rules that reference that field, so schema and rules cannot be independently hot-swapped in the general case. Treating schema as fixed eliminates a class of correctness bugs and allows types to be resolved at rule compile time against a stable schema.

Rules are dynamic by design. Policies change, thresholds are tuned, and seasonal logic is toggled. The engine supports hot-swapping rules without reinitializing the schema or the operator/type registries.

Decisions are always dynamic: they are evaluated on arrival and not retained.

## Engine lifecycle

```
Construction  │  load_schema() parses schema, builds SchemaRegistry, sets modes and preset
              │
Registration  │  register_type(), register_operator(), add_function()
              │  All registrations must complete before first compile/eval
              │
  ┌── Freeze ─┘  First compile() or eval() freezes all registries
  │
  │  Hot-swap │  update_rules() atomically replaces compiled rules;
  │           │  schema and registries remain unchanged
  │
  └── Replace │  For schema changes: caller spins up a new Engine,
              │  drains in-flight decisions against old engine, discards it
```

The engine transitions through four phases:

1. **Construction** — `load_schema()` parses the schema text, runs the schema validator, and builds the `SchemaRegistry`. Type enforcement modes and the operator preset are set here and do not change.
2. **Registration** — the caller registers custom types, operators, and functions. All registrations must complete before any `compile()` or `eval()` call.
3. **Freeze** — the first `compile()` or `eval()` call freezes all registries. Any subsequent registration attempt raises `EngineAlreadyFrozenError`.
4. **Hot-swap / Replace** — see below.

## Zero-downtime via atomic engine replacement

For rule updates, `update_rules()` atomically replaces the compiled rule set. Schema and registries remain unchanged.

For schema changes, the zero-downtime mechanism is **atomic engine replacement**: the caller spins up a new engine instance with the new schema and rules, drains in-flight decisions against the old instance, then discards it. Amino is responsible for making a single engine well-encapsulated and safely replaceable. The application is responsible for managing the swap — deciding when to swap, draining in-flight work, and discarding the old instance. This pattern handles schema changes cleanly because the schema is fixed per engine instance; replacing the schema means replacing the engine.

## Multi-context is application-level

A decision context is a (schema, rules, validation modes) tuple. Running multiple contexts simultaneously — for example, different tenants with different schemas — is handled by the application instantiating multiple engine instances and routing decisions accordingly.

Amino does not manage context naming, lifecycle, or routing. These are orchestration concerns outside the package boundary. Building multi-context management into amino would require naming, routing, and lifecycle APIs that have nothing to do with rules evaluation; applications are better positioned to own this logic.

## DSL text as interchange format

Rule expressions are stored and transmitted as text strings — not as serialized ASTs or binary formats. Each runtime implementation parses and compiles the DSL independently.

The portable unit for a rule is the **(schema, DSL text) pair**, not the DSL text in isolation. A rule referencing `credit_score < 600` has no meaning without knowing that `credit_score` is an `Int` field. Services that receive and compile rules must also have access to the schema.

Python is the initial reference implementation — the authoritative specification against which future language implementations must produce identical results for identical (schema, rule, decision) inputs. Client-side SDKs in other languages start as rule composers (libraries that produce DSL text) before implementing full runtimes.

Schema introspection is a first-class operation. `engine.export_schema()` returns the current schema in `.amn` format, enabling client SDKs to fetch the schema and perform local preflight validation before submitting rules to a runtime.

## Error hierarchy

```
AminoError
├── SchemaParseError           # Syntax error in .amn schema file
├── SchemaValidationError      # Semantic error: unknown type ref, circular struct, duplicate name
├── RuleParseError             # Syntax error in rule expression string
├── TypeMismatchError          # Type error caught at rule compile time
├── DecisionValidationError    # Decision data fails schema/constraint validation (strict mode)
├── RuleEvaluationError        # Runtime error during rule evaluation
├── OperatorConflictError      # Duplicate operator registration
└── EngineAlreadyFrozenError   # Registration attempted after first use
```

All errors carry a `message: str` and, where applicable, `field: str`, `expected: str`, and `got: str` for structured error handling.

## File structure

```
amino/
├── __init__.py              # Public API: load_schema()
├── engine.py                # Engine class: orchestrates registries, enforces freeze-before-use
├── schema/
│   ├── __init__.py
│   ├── parser.py            # PEG parser for .amn schema files (static grammar)
│   ├── ast.py               # Schema AST nodes + SchemaType enum
│   └── registry.py          # SchemaRegistry: field/struct lookup + schema export
│   └── validator.py         # Schema self-consistency: refs, circular structs, duplicates
├── rules/
│   ├── __init__.py
│   ├── parser.py            # Pratt parser for rule expressions (dynamic operator table)
│   ├── ast.py               # Rule AST nodes, annotated with resolved types + return type
│   └── compiler.py          # TypedCompiler: type resolution + optimization + codegen
├── operators/
│   ├── __init__.py
│   ├── registry.py          # OperatorRegistry: symbol/keyword → OperatorDef
│   └── standard.py          # 'standard' and 'minimal' preset definitions
├── types/
│   ├── __init__.py
│   ├── registry.py          # TypeRegistry: name → TypeDef (base type + validator)
│   └── builtin.py           # Pre-defined types: ipv4, ipv6, cidr, email, uuid, etc.
├── runtime/
│   ├── __init__.py
│   ├── compiled_rules.py    # CompiledRules: returned by compile(), owns match config
│   ├── validator.py         # DecisionValidator: validates decisions against schema + constraints
│   ├── evaluator.py         # Executes compiled rules against a validated decision
│   └── matcher.py           # Applies match mode to rule results → MatchResult
└── errors.py                # Exception hierarchy
```
