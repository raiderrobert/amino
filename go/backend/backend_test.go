package backend_test

import (
	"errors"
	"reflect"
	"testing"

	amino "github.com/raiderrobert/amino/go"
	"github.com/raiderrobert/amino/go/backend"
)

const schema = `
struct Customer { id: Str, tier: Int }
score: Int
ratio: Float
name: Str
active: Bool
contact: email
customer: Customer
lower: (s: Str) -> Str
`

func engine(t *testing.T, opts ...amino.Option) *amino.Engine {
	t.Helper()
	e, err := amino.LoadSchema(schema, opts...)
	if err != nil {
		t.Fatal(err)
	}
	return e
}

func parse(t *testing.T, e *amino.Engine, text string) *amino.Expression {
	t.Helper()
	x, err := e.Parse(text)
	if err != nil {
		t.Fatalf("parse %q: %v", text, err)
	}
	return x
}

// The expected SQL matches the Python reference implementation's tests
// exactly, except that Postgres placeholders are $n rather than psycopg's %s.
func TestPostgres(t *testing.T) {
	e := engine(t)
	cases := []struct {
		text   string
		sql    string
		params []any
	}{
		{"score = 5", `("score" = $1)`, []any{int64(5)}},
		{"score != 5", `("score" <> $1)`, []any{int64(5)}},
		{"score > 5", `("score" > $1)`, []any{int64(5)}},
		{"ratio > 0.5", `("ratio" > $1)`, []any{0.5}},
		{"name = 'bob'", `("name" = $1)`, []any{"bob"}},
		{"active = true", `("active" = $1)`, []any{true}},
		{"contact = 'a@b.co'", `("contact" = $1)`, []any{"a@b.co"}},
		{"name in ['a', 'b']", `("name" = ANY($1))`, []any{[]any{"a", "b"}}},
		{"name not in ['a', 'b']", `(NOT ("name" = ANY($1)))`, []any{[]any{"a", "b"}}},
		{"score in [1, 2, 3]", `("score" = ANY($1))`, []any{[]any{int64(1), int64(2), int64(3)}}},
		{"name in []", `FALSE`, []any{}},
		{"name not in []", `TRUE`, []any{}},
		{"name contains 'ob'", `(position($1 IN "name") > 0)`, []any{"ob"}},
		{"not active = true", `(NOT ("active" = $1))`, []any{true}},
		{"score > 1 and name = 'x'", `(("score" > $1) AND ("name" = $2))`, []any{int64(1), "x"}},
		{"score > 1 or name = 'x' and active = false", `(("score" > $1) OR (("name" = $2) AND ("active" = $3)))`, []any{int64(1), "x", false}},
		{"(score > 1 or name = 'x') and active = false", `((("score" > $1) OR ("name" = $2)) AND ("active" = $3))`, []any{int64(1), "x", false}},
		{"lower(name) = 'x'", `(lower("name") = $1)`, []any{"x"}},
	}
	for _, c := range cases {
		q, err := backend.Postgres{}.Compile(parse(t, e, c.text))
		if err != nil {
			t.Errorf("%q: %v", c.text, err)
			continue
		}
		if q.SQL != c.sql {
			t.Errorf("%q: sql\n got %s\nwant %s", c.text, q.SQL, c.sql)
		}
		if !reflect.DeepEqual(q.Params, c.params) {
			t.Errorf("%q: params got %#v want %#v", c.text, q.Params, c.params)
		}
	}
}

func TestClickHouse(t *testing.T) {
	e := engine(t)
	cases := []struct {
		text   string
		sql    string
		params map[string]any
	}{
		{"score = 5", "(`score` = {p0:Int64})", map[string]any{"p0": int64(5)}},
		{"score != 5", "(`score` <> {p0:Int64})", map[string]any{"p0": int64(5)}},
		{"ratio > 0.5", "(`ratio` > {p0:Float64})", map[string]any{"p0": 0.5}},
		{"name = 'bob'", "(`name` = {p0:String})", map[string]any{"p0": "bob"}},
		{"active = true", "(`active` = {p0:Bool})", map[string]any{"p0": true}},
		{"contact = 'a@b.co'", "(`contact` = {p0:String})", map[string]any{"p0": "a@b.co"}},
		{"name in ['a', 'b']", "(`name` IN {p0:Array(String)})", map[string]any{"p0": []any{"a", "b"}}},
		{"name not in ['a', 'b']", "(`name` NOT IN {p0:Array(String)})", map[string]any{"p0": []any{"a", "b"}}},
		{"score in [1, 2, 3]", "(`score` IN {p0:Array(Int64)})", map[string]any{"p0": []any{int64(1), int64(2), int64(3)}}},
		{"ratio in [0.5, 1.5]", "(`ratio` IN {p0:Array(Float64)})", map[string]any{"p0": []any{0.5, 1.5}}},
		{"name in []", "FALSE", map[string]any{}},
		{"name contains 'ob'", "(position(`name`, {p0:String}) > 0)", map[string]any{"p0": "ob"}},
		{"not active = true", "(NOT (`active` = {p0:Bool}))", map[string]any{"p0": true}},
		{"score > 1 and name = 'x'", "((`score` > {p0:Int64}) AND (`name` = {p1:String}))", map[string]any{"p0": int64(1), "p1": "x"}},
		{"lower(name) = 'x'", "(lower(`name`) = {p0:String})", map[string]any{"p0": "x"}},
	}
	for _, c := range cases {
		q, err := backend.ClickHouse{}.Compile(parse(t, e, c.text))
		if err != nil {
			t.Errorf("%q: %v", c.text, err)
			continue
		}
		if q.SQL != c.sql {
			t.Errorf("%q: sql\n got %s\nwant %s", c.text, q.SQL, c.sql)
		}
		if !reflect.DeepEqual(q.Params, c.params) {
			t.Errorf("%q: params got %#v want %#v", c.text, q.Params, c.params)
		}
	}
}

func TestColumnMapping(t *testing.T) {
	e := engine(t)
	q, err := backend.Postgres{Columns: map[string]string{"customer.tier": "customer_tier"}}.Compile(parse(t, e, "customer.tier > 2"))
	if err != nil {
		t.Fatal(err)
	}
	if q.SQL != "(customer_tier > $1)" {
		t.Errorf("got %s", q.SQL)
	}
	q, err = backend.ClickHouse{Columns: map[string]string{"score": "s.score"}}.Compile(parse(t, e, "score > 2"))
	if err != nil {
		t.Fatal(err)
	}
	if q.SQL != "(s.score > {p0:Int64})" {
		t.Errorf("got %s", q.SQL)
	}
}

func TestUnsupported(t *testing.T) {
	e := engine(t, amino.WithOperator(amino.OperatorDef{
		Keyword: "near", BindingPower: 40, InputTypes: []string{"Int", "Int"}, ReturnType: "Bool",
		Fn: func(args ...any) (any, error) { return true, nil },
	}))
	for _, text := range []string{"customer.tier > 2", "score near 3"} {
		_, err := backend.Postgres{}.Compile(parse(t, e, text))
		var ae *amino.Error
		if !errors.As(err, &ae) || ae.Code != amino.CodeUnsupported {
			t.Errorf("%q: expected unsupported error, got %v", text, err)
		}
	}
}

func TestQuoting(t *testing.T) {
	e, err := amino.LoadSchema("a: Int")
	if err != nil {
		t.Fatal(err)
	}
	x := parse(t, e, "a = 1")
	q, _ := backend.Postgres{Columns: map[string]string{"a": `"we""ird"`}}.Compile(x)
	if q.SQL != `("we""ird" = $1)` {
		t.Errorf("got %s", q.SQL)
	}
}
