package backend

import (
	"strings"

	amino "github.com/raiderrobert/amino/go"
)

// ClickHouse compiles to a predicate with server-side typed {p0:Int64}
// placeholders. Params is a map[string]any for the clickhouse-go client's
// named parameters. The type comes from the schema, so nothing is guessed
// from the value at bind time.
type ClickHouse struct {
	Columns map[string]string
}

// Compile renders expr for ClickHouse.
func (c ClickHouse) Compile(expr *amino.Expression) (Query, error) {
	return Compile(chDialect{}, expr, c.Columns)
}

var chScalar = map[string]string{"Int": "Int64", "Float": "Float64", "Str": "String", "Bool": "Bool"}

func chType(base string) string {
	if strings.HasPrefix(base, "List[") && strings.HasSuffix(base, "]") {
		return "Array(" + chType(base[5:len(base)-1]) + ")"
	}
	if t, ok := chScalar[base]; ok {
		return t
	}
	return "String"
}

type chDialect struct{}

type chParams struct{ values map[string]any }

func (s *chParams) Add(value any, base string) string {
	if s.values == nil {
		s.values = map[string]any{}
	}
	name := "p" + itoa(len(s.values))
	s.values[name] = value
	return "{" + name + ":" + chType(base) + "}"
}

func (s *chParams) Result() any {
	if s.values == nil {
		return map[string]any{}
	}
	return s.values
}

func (chDialect) Name() string { return "ClickHouse" }
func (chDialect) QuoteIdent(name string) string {
	return "`" + strings.ReplaceAll(strings.ReplaceAll(name, `\`, `\\`), "`", "\\`") + "`"
}
func (chDialect) NewParams() ParamSink              { return &chParams{} }
func (chDialect) RenderIn(col, ph string) string    { return col + " IN " + ph }
func (chDialect) RenderNotIn(col, ph string) string { return col + " NOT IN " + ph }
func (chDialect) RenderContains(hay, needle string) string {
	return "position(" + hay + ", " + needle + ") > 0"
}
