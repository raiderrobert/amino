package amino_test

import (
	"errors"
	"reflect"
	"testing"

	amino "github.com/raiderrobert/amino/go"
)

func mustEngine(t *testing.T, schema string, opts ...amino.Option) *amino.Engine {
	t.Helper()
	e, err := amino.LoadSchema(schema, opts...)
	if err != nil {
		t.Fatal(err)
	}
	return e
}

func code(err error) amino.Code {
	var ae *amino.Error
	if errors.As(err, &ae) {
		return ae.Code
	}
	return ""
}

func TestSchemaParseAndExport(t *testing.T) {
	src := `# comment
struct Address { street: Str, city: Str }
struct Customer {
    id: Str
    billing: Address
    shipping: Address?
}
amount: Int {min: 0, max: 100}
tags: List[Str|Int]
email: Str?
customer: Customer
score: (a: Int, b: Float?) -> Float
`
	e := mustEngine(t, src)
	s := e.Schema()
	if len(s.Structs) != 2 || len(s.Fields) != 4 || len(s.Functions) != 1 {
		t.Fatalf("counts: %d structs %d fields %d functions", len(s.Structs), len(s.Fields), len(s.Functions))
	}
	if f := s.Lookup("customer.billing.city"); f == nil || f.TypeName != "Str" {
		t.Fatalf("nested lookup: %+v", f)
	}
	if f := s.Lookup("tags"); f.Kind != amino.KindList || !reflect.DeepEqual(f.ElementTypes, []string{"Str", "Int"}) {
		t.Fatalf("list: %+v", f)
	}
	if f := s.Lookup("amount"); f.Constraints["min"] != int64(0) {
		t.Fatalf("constraints: %+v", f.Constraints)
	}
	want := "struct Address {street: Str, city: Str}\nstruct Customer {id: Str, billing: Address, shipping: Address?}\namount: Int {max: 100, min: 0}\ntags: List[Str|Int]\nemail: Str?\ncustomer: Customer\nscore: (a: Int, b: Float?) -> Float"
	if got := e.ExportSchema(); got != want {
		t.Fatalf("export:\n%s\nwant:\n%s", got, want)
	}
}

func TestSchemaValidation(t *testing.T) {
	cases := map[string]string{
		"a: Nope":                              "unknown type",
		"a: Int\na: Str":                       "duplicate",
		"struct A { b: B }\nstruct B { a: A }": "circular",
		"struct S { x: Int, x: Str }":          "duplicate field",
		"a Int":                                "expected",
		"struct: Int":                          "reserved",
	}
	for src, want := range cases {
		_, err := amino.LoadSchema(src)
		if err == nil {
			t.Errorf("%q: expected error containing %q", src, want)
			continue
		}
		if c := code(err); c != amino.CodeSchemaParse && c != amino.CodeSchemaValidation {
			t.Errorf("%q: code %s", src, c)
		}
	}
}

func TestEvalAndMatchModes(t *testing.T) {
	e := mustEngine(t, "amount: Int\nstate: Str")
	rules := []amino.Rule{
		{ID: "1", Expr: "amount > 0 and state = 'CA'", Meta: map[string]any{"ordering": 3}},
		{ID: "2", Expr: "amount > 10 and state = 'CA'", Meta: map[string]any{"ordering": 2}},
		{ID: "3", Expr: "amount >= 100", Meta: map[string]any{"ordering": 1}},
	}
	rec := map[string]any{"id": 45, "amount": 100, "state": "CA"}

	r, err := e.Eval(rules, rec, nil)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(r.Matched, []string{"1", "2", "3"}) || r.ID != 45 {
		t.Fatalf("all: %+v", r)
	}

	r, _ = e.Eval(rules, rec, &amino.MatchConfig{Mode: "first", Key: "ordering", Order: "asc"})
	if !reflect.DeepEqual(r.Matched, []string{"3"}) {
		t.Fatalf("first asc: %+v", r)
	}
	r, _ = e.Eval(rules, rec, &amino.MatchConfig{Mode: "first", Key: "ordering", Order: "desc"})
	if !reflect.DeepEqual(r.Matched, []string{"1"}) {
		t.Fatalf("first desc: %+v", r)
	}

	r, _ = e.Eval(rules, map[string]any{"amount": 5, "state": "NY"}, &amino.MatchConfig{Mode: "inverse"})
	if !reflect.DeepEqual(r.Excluded, []string{"1", "2", "3"}) {
		t.Fatalf("inverse: %+v", r)
	}

	scoring := []amino.Rule{{ID: "a", Expr: "amount"}, {ID: "b", Expr: "amount > 0"}}
	th := 50.0
	r, _ = e.Eval(scoring, rec, &amino.MatchConfig{Mode: "score", Threshold: &th})
	if r.Score == nil || *r.Score != 101 || !reflect.DeepEqual(r.Matched, []string{"a", "b"}) {
		t.Fatalf("score: %+v", r)
	}
}

func TestMissingFieldMakesRuleFalse(t *testing.T) {
	e := mustEngine(t, "a: Int\nb: Int?")
	r, _ := e.Eval([]amino.Rule{{ID: "r", Expr: "not b = 1"}, {ID: "s", Expr: "b = 1 or a = 1"}}, map[string]any{"a": 1}, nil)
	if !reflect.DeepEqual(r.Matched, []string{"s"}) {
		t.Fatalf("got %+v", r)
	}
}

func TestDecisionValidation(t *testing.T) {
	strict := mustEngine(t, "n: Int {min: 0}\ncontact: email", amino.WithDecisionsMode("strict"))
	_, err := strict.Eval([]amino.Rule{{ID: "r", Expr: "n > 1"}}, map[string]any{"n": "x", "contact": "a@b.co"}, nil)
	if code(err) != amino.CodeDecisionValidation {
		t.Fatalf("strict type: %v", err)
	}
	_, err = strict.Eval([]amino.Rule{{ID: "r", Expr: "n > 1"}}, map[string]any{"n": -1, "contact": "a@b.co"}, nil)
	if code(err) != amino.CodeDecisionValidation {
		t.Fatalf("strict constraint: %v", err)
	}
	_, err = strict.Eval([]amino.Rule{{ID: "r", Expr: "n > 1"}}, map[string]any{"n": 2, "contact": "nope"}, nil)
	if code(err) != amino.CodeDecisionValidation {
		t.Fatalf("strict custom type: %v", err)
	}

	loose := mustEngine(t, "n: Int\ncontact: email")
	r, err := loose.Eval([]amino.Rule{{ID: "r", Expr: "contact = 'nope'"}}, map[string]any{"n": 2, "contact": "nope"}, nil)
	if err != nil || len(r.Matched) != 0 || len(r.Warnings) != 1 {
		t.Fatalf("loose: %+v %v", r, err)
	}
}

func TestFunctionsAndCustomOperators(t *testing.T) {
	e := mustEngine(t, "text: Str\ntoxicity: (t: Str) -> Float\na: Int\nb: Int",
		amino.WithFunction("toxicity", func(args ...any) (any, error) { return 0.9, nil }),
		amino.WithOperator(amino.OperatorDef{
			Keyword: "near", BindingPower: 40, InputTypes: []string{"Int", "Int"}, ReturnType: "Bool",
			Fn: func(args ...any) (any, error) {
				x, _ := args[0].(int64)
				y, _ := args[1].(int64)
				d := x - y
				if d < 0 {
					d = -d
				}
				return d < 5, nil
			},
		}),
	)
	r, err := e.Eval([]amino.Rule{{ID: "t", Expr: "toxicity(text) > 0.5"}, {ID: "n", Expr: "a near b"}},
		map[string]any{"text": "hi", "a": 3, "b": 6}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(r.Matched, []string{"t", "n"}) {
		t.Fatalf("got %+v", r)
	}
	if _, err := e.Parse("toxicity(a) > 0.5"); code(err) != amino.CodeTypeMismatch {
		t.Fatalf("argument type: %v", err)
	}
	if _, err := e.Parse("toxicity()"); code(err) != amino.CodeTypeMismatch {
		t.Fatalf("arity: %v", err)
	}
}

func TestLimits(t *testing.T) {
	e := mustEngine(t, "a: Int", amino.WithMaxDepth(3), amino.WithMaxLength(20))
	if _, err := e.Parse("(((a > 1)))"); code(err) != amino.CodeDepthExceeded {
		t.Fatalf("depth: %v", err)
	}
	if _, err := e.Parse("a > 1 and a > 1 and a > 1"); code(err) != amino.CodeSyntax {
		t.Fatalf("length: %v", err)
	}
}

func TestOperatorConflict(t *testing.T) {
	_, err := amino.LoadSchema("a: Int", amino.WithOperator(amino.OperatorDef{Symbol: "=", BindingPower: 40}))
	if code(err) != amino.CodeOperatorConflict {
		t.Fatalf("got %v", err)
	}
}
