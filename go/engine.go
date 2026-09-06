// Package amino is the Go host implementation of the amino expression
// language: a small, fixed grammar for conditions users write over a
// developer's data, checked against a schema and compiled to targets.
//
// An Engine is built once from a schema and options and is then immutable
// and safe for concurrent use. Parse turns expression text into a typed
// Expression that any target can consume; Compile and Eval are the
// in-process target.
package amino

// Engine holds a validated schema plus the registered types, operators, and
// functions an expression may use.
type Engine struct {
	schema        *Schema
	types         *typeRegistry
	ops           *operatorRegistry
	funcs         map[string]Func
	decisionsMode string
	maxDepth      int
	maxLength     int
}

// Option configures LoadSchema.
type Option func(*config) error

type config struct {
	preset        string
	opList        []string
	operators     []OperatorDef
	types         []TypeDef
	funcs         map[string]Func
	decisionsMode string
	maxDepth      int
	maxLength     int
}

// WithOperators selects a built-in operator preset: "standard" (default) or "minimal".
func WithOperators(preset string) Option {
	return func(c *config) error { c.preset = preset; return nil }
}

// WithOperatorList enables only the named built-in operators. and, or, and
// not are always enabled.
func WithOperatorList(names ...string) Option {
	return func(c *config) error { c.opList = append([]string{}, names...); return nil }
}

// WithOperator registers a custom operator.
func WithOperator(def OperatorDef) Option {
	return func(c *config) error { c.operators = append(c.operators, def); return nil }
}

// WithType registers a custom type, or overrides a built-in one.
func WithType(name, base string, validator func(any) bool) Option {
	return func(c *config) error {
		c.types = append(c.types, TypeDef{Name: name, Base: base, Validator: validator})
		return nil
	}
}

// WithFunction supplies the implementation for a schema-declared function.
func WithFunction(name string, fn Func) Option {
	return func(c *config) error { c.funcs[name] = fn; return nil }
}

// WithDecisionsMode sets how non-conforming records are handled: "loose"
// (default) drops the field with a warning, "strict" returns an error.
func WithDecisionsMode(mode string) Option {
	return func(c *config) error {
		if mode != "strict" && mode != "loose" {
			return newError(CodeConfig, "decisions mode must be strict or loose, got %q", mode)
		}
		c.decisionsMode = mode
		return nil
	}
}

// WithMaxDepth caps expression nesting. Default 100.
func WithMaxDepth(n int) Option { return func(c *config) error { c.maxDepth = n; return nil } }

// WithMaxLength caps expression length in bytes. Default 10000.
func WithMaxLength(n int) Option { return func(c *config) error { c.maxLength = n; return nil } }

// LoadSchema parses and validates schema text and builds an Engine.
func LoadSchema(schemaText string, opts ...Option) (*Engine, error) {
	cfg := &config{funcs: map[string]Func{}, decisionsMode: "loose", maxDepth: 100, maxLength: 10000}
	for _, o := range opts {
		if err := o(cfg); err != nil {
			return nil, err
		}
	}
	types := newTypeRegistry()
	for _, t := range cfg.types {
		if err := types.register(t); err != nil {
			return nil, err
		}
	}
	ops, err := buildOperatorRegistry(cfg.preset, cfg.opList)
	if err != nil {
		return nil, err
	}
	for _, d := range cfg.operators {
		if err := ops.register(d); err != nil {
			return nil, err
		}
	}
	schema, err := ParseSchema(schemaText)
	if err != nil {
		return nil, err
	}
	if err := schema.validate(types.names()); err != nil {
		return nil, err
	}
	return &Engine{
		schema: schema, types: types, ops: ops, funcs: cfg.funcs,
		decisionsMode: cfg.decisionsMode, maxDepth: cfg.maxDepth, maxLength: cfg.maxLength,
	}, nil
}

// Schema returns the validated schema.
func (e *Engine) Schema() *Schema { return e.schema }

// ExportSchema renders the schema as .amn text.
func (e *Engine) ExportSchema() string { return e.schema.Export() }

// Expression is a parsed, type-checked expression ready for any target.
type Expression struct {
	Root   Node
	Type   string // the root's type: "Bool" for a predicate
	engine *Engine
}

// Schema returns the schema the expression was parsed against.
func (x *Expression) Schema() *Schema { return x.engine.schema }

// BaseType reduces a type name to its primitive: "email" -> "Str". Primitives
// and List return themselves.
func (x *Expression) BaseType(name string) string { return x.engine.types.base(name) }

// Parse parses and type-checks one expression.
func (e *Engine) Parse(text string) (*Expression, error) {
	root, err := parseExpression(text, e)
	if err != nil {
		return nil, err
	}
	return &Expression{Root: root, Type: root.TypeName(), engine: e}, nil
}

// Rule is one expression in a rule set for the in-process target.
type Rule struct {
	ID   string
	Expr string
	Meta map[string]any // e.g. {"ordering": 1} for first-match mode
}

type compiledRule struct {
	id string
	fn evalFn
}

// CompiledRules is a rule set compiled once for repeated evaluation. It is
// immutable; to change rules, compile again.
type CompiledRules struct {
	engine *Engine
	rules  []compiledRule
	meta   map[string]map[string]any
	cfg    MatchConfig
}

// Compile parses every rule and returns a reusable rule set.
func (e *Engine) Compile(rules []Rule, match *MatchConfig) (*CompiledRules, error) {
	c := &CompiledRules{engine: e, meta: map[string]map[string]any{}}
	if match != nil {
		c.cfg = *match
	}
	seen := map[string]bool{}
	for _, r := range rules {
		if seen[r.ID] {
			return nil, newError(CodeConfig, "duplicate rule id %q", r.ID)
		}
		seen[r.ID] = true
		root, err := parseExpression(r.Expr, e)
		if err != nil {
			return nil, err
		}
		c.rules = append(c.rules, compiledRule{id: r.ID, fn: compileNode(root)})
		c.meta[r.ID] = r.Meta
	}
	return c, nil
}

// Eval compiles and evaluates in one call.
func (e *Engine) Eval(rules []Rule, decision map[string]any, match *MatchConfig) (MatchResult, error) {
	c, err := e.Compile(rules, match)
	if err != nil {
		return MatchResult{}, err
	}
	return c.EvalOne(decision)
}

// EvalOne evaluates the rule set against one record. An error is returned
// only for a strict-mode validation failure; a rule that fails during
// evaluation is simply false.
func (c *CompiledRules) EvalOne(decision map[string]any) (MatchResult, error) {
	cleaned, warnings, err := c.engine.validateDecision(decision)
	if err != nil {
		return MatchResult{}, err
	}
	results := make([]ruleResult, 0, len(c.rules))
	for _, r := range c.rules {
		v, err := r.fn(cleaned, c.engine.funcs)
		if err != nil {
			v = false
		}
		results = append(results, ruleResult{id: r.id, value: v})
	}
	return c.match(decision["id"], results, warnings)
}

// Eval evaluates the rule set against many records.
func (c *CompiledRules) Eval(decisions []map[string]any) ([]MatchResult, error) {
	out := make([]MatchResult, 0, len(decisions))
	for _, d := range decisions {
		r, err := c.EvalOne(d)
		if err != nil {
			return nil, err
		}
		out = append(out, r)
	}
	return out, nil
}
