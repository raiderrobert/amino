package backend

import (
	"strings"

	amino "github.com/raiderrobert/amino/go"
)

// Postgres compiles to a predicate with positional $1, $2 placeholders, the
// style pgx and database/sql's Postgres drivers expect. List membership
// renders as col = ANY($n) so a Go slice binds as one array parameter.
type Postgres struct {
	// Columns maps a field path to a SQL fragment rendered verbatim.
	Columns map[string]string
}

// Compile renders expr for Postgres.
func (p Postgres) Compile(expr *amino.Expression) (Query, error) {
	return Compile(pgDialect{}, expr, p.Columns)
}

type pgDialect struct{}

type pgParams struct{ values []any }

func (s *pgParams) Add(value any, _ string) string {
	s.values = append(s.values, value)
	return "$" + itoa(len(s.values))
}

func (s *pgParams) Result() any {
	if s.values == nil {
		return []any{}
	}
	return s.values
}

func (pgDialect) Name() string { return "Postgres" }
func (pgDialect) QuoteIdent(name string) string {
	return `"` + strings.ReplaceAll(name, `"`, `""`) + `"`
}
func (pgDialect) NewParams() ParamSink              { return &pgParams{} }
func (pgDialect) RenderIn(col, ph string) string    { return col + " = ANY(" + ph + ")" }
func (pgDialect) RenderNotIn(col, ph string) string { return "NOT (" + col + " = ANY(" + ph + "))" }
func (pgDialect) RenderContains(hay, needle string) string {
	return "position(" + needle + " IN " + hay + ") > 0"
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	var b [20]byte
	i := len(b)
	for n > 0 {
		i--
		b[i] = byte('0' + n%10)
		n /= 10
	}
	return string(b[i:])
}
