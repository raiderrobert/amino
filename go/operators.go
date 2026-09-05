package amino

import "sort"

// OperatorFunc implements an operator on the in-process target. Prefix
// operators receive one argument, infix two.
type OperatorFunc func(args ...any) (any, error)

// OperatorDef registers an operator with the parser. Exactly one of Symbol or
// Keyword is set. InputTypes and ReturnType drive type checking; a "*" input
// type accepts anything. Fn may be nil for and/or/not, which the evaluator
// implements itself.
type OperatorDef struct {
	Symbol        string
	Keyword       string
	Kind          string // "infix" or "prefix"
	Fn            OperatorFunc
	BindingPower  int
	Associativity string // "left" or "right"
	InputTypes    []string
	ReturnType    string
}

// Token returns the text the operator is written as.
func (d *OperatorDef) Token() string {
	if d.Symbol != "" {
		return d.Symbol
	}
	return d.Keyword
}

type operatorRegistry struct {
	byToken  map[string][]*OperatorDef
	symbols  map[string]bool
	keywords map[string]bool
}

func newOperatorRegistry() *operatorRegistry {
	return &operatorRegistry{byToken: map[string][]*OperatorDef{}, symbols: map[string]bool{}, keywords: map[string]bool{}}
}

func (r *operatorRegistry) register(d OperatorDef) error {
	if (d.Symbol == "") == (d.Keyword == "") {
		return newError(CodeConfig, "operator needs exactly one of Symbol or Keyword")
	}
	if d.Kind == "" {
		d.Kind = "infix"
	}
	if d.Kind != "infix" && d.Kind != "prefix" {
		return newError(CodeConfig, "operator %q: kind must be infix or prefix, got %q", d.Token(), d.Kind)
	}
	if d.Associativity == "" {
		d.Associativity = "left"
	}
	if d.InputTypes == nil {
		if d.Kind == "prefix" {
			d.InputTypes = []string{"*"}
		} else {
			d.InputTypes = []string{"*", "*"}
		}
	}
	if d.ReturnType == "" {
		d.ReturnType = "Bool"
	}
	tok := d.Token()
	for _, existing := range r.byToken[tok] {
		if sameTypes(existing.InputTypes, d.InputTypes) {
			return newError(CodeOperatorConflict, "operator %q with input types %v already registered", tok, d.InputTypes)
		}
	}
	def := d
	r.byToken[tok] = append(r.byToken[tok], &def)
	if d.Symbol != "" {
		r.symbols[d.Symbol] = true
	} else {
		r.keywords[d.Keyword] = true
	}
	return nil
}

func sameTypes(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func (r *operatorRegistry) candidates(tok string) []*OperatorDef { return r.byToken[tok] }

func (r *operatorRegistry) bindingPower(tok string) (int, bool) {
	c := r.byToken[tok]
	if len(c) == 0 {
		return 0, false
	}
	return c[0].BindingPower, true
}

func (r *operatorRegistry) prefix(tok string) *OperatorDef {
	for _, d := range r.byToken[tok] {
		if d.Kind == "prefix" {
			return d
		}
	}
	return nil
}

func (r *operatorRegistry) symbolList() []string {
	out := make([]string, 0, len(r.symbols))
	for s := range r.symbols {
		out = append(out, s)
	}
	sort.Slice(out, func(i, j int) bool { return len(out[i]) > len(out[j]) })
	return out
}

// Built-in operators. and/or/not are the irreducible minimum and are always
// present. Their InputTypes are what the type checker enforces.
var alwaysOperators = map[string]bool{"or": true, "and": true, "not": true}

func standardOperators() []OperatorDef {
	cmp := func(f func(int) bool) OperatorFunc {
		return func(args ...any) (any, error) {
			c, err := compareValues(args[0], args[1])
			if err != nil {
				return nil, err
			}
			return f(c), nil
		}
	}
	return []OperatorDef{
		{Keyword: "or", BindingPower: 10, InputTypes: []string{"Bool", "Bool"}},
		{Keyword: "and", BindingPower: 20, InputTypes: []string{"Bool", "Bool"}},
		{Keyword: "not", Kind: "prefix", BindingPower: 30, InputTypes: []string{"Bool"}},
		{Keyword: "in", BindingPower: 40, InputTypes: []string{"*", "List"}, Fn: func(args ...any) (any, error) {
			return inList(args[0], args[1])
		}},
		{Keyword: "not in", BindingPower: 40, InputTypes: []string{"*", "List"}, Fn: func(args ...any) (any, error) {
			in, err := inList(args[0], args[1])
			if err != nil {
				return nil, err
			}
			return !in, nil
		}},
		{Symbol: "=", BindingPower: 40, Fn: func(args ...any) (any, error) { return equalValues(args[0], args[1]) }},
		{Symbol: "!=", BindingPower: 40, Fn: func(args ...any) (any, error) {
			eq, err := equalValues(args[0], args[1])
			if err != nil {
				return nil, err
			}
			return !eq, nil
		}},
		{Symbol: ">", BindingPower: 40, Fn: cmp(func(c int) bool { return c > 0 })},
		{Symbol: "<", BindingPower: 40, Fn: cmp(func(c int) bool { return c < 0 })},
		{Symbol: ">=", BindingPower: 40, Fn: cmp(func(c int) bool { return c >= 0 })},
		{Symbol: "<=", BindingPower: 40, Fn: cmp(func(c int) bool { return c <= 0 })},
		{Keyword: "contains", BindingPower: 40, InputTypes: []string{"Str", "Str"}, Fn: func(args ...any) (any, error) {
			hay, ok1 := args[0].(string)
			needle, ok2 := args[1].(string)
			if !ok1 || !ok2 {
				return nil, newError(CodeEvaluation, "contains needs two strings")
			}
			return containsString(hay, needle), nil
		}},
	}
}

func buildOperatorRegistry(preset string, names []string) (*operatorRegistry, error) {
	all := standardOperators()
	var chosen []OperatorDef
	switch {
	case names != nil:
		enabled := map[string]bool{}
		for _, n := range names {
			enabled[n] = true
		}
		for _, d := range all {
			if enabled[d.Token()] || alwaysOperators[d.Token()] {
				chosen = append(chosen, d)
			}
		}
	case preset == "" || preset == "standard":
		chosen = all
	case preset == "minimal":
		for _, d := range all {
			if alwaysOperators[d.Token()] {
				chosen = append(chosen, d)
			}
		}
	default:
		return nil, newError(CodeConfig, "unknown operator preset %q", preset)
	}
	r := newOperatorRegistry()
	for _, d := range chosen {
		if err := r.register(d); err != nil {
			return nil, err
		}
	}
	return r, nil
}
