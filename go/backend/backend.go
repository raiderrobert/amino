// Package backend compiles amino expressions to parameterised SQL predicates.
//
// A Dialect supplies only what differs between databases: identifier quoting,
// parameter style, list membership, and substring search. Compile does the
// shared tree walk. Every literal the user wrote becomes a bound parameter;
// nothing is interpolated.
package backend

import (
	"fmt"
	"strings"

	amino "github.com/raiderrobert/amino/go"
)

// Query is a SQL fragment suitable for a WHERE clause plus its bound
// parameters. Params is a []any for positional dialects and a
// map[string]any for named ones.
type Query struct {
	SQL    string
	Params any
}

// ParamSink collects bound parameters for one Compile call.
type ParamSink interface {
	// Add binds a value and returns the placeholder to splice into the SQL.
	// baseType is "Int", "Float", "Str", "Bool", or "List[T]".
	Add(value any, baseType string) string
	// Result returns the collected parameters in the dialect's shape.
	Result() any
}

// Dialect is what a SQL target must supply.
type Dialect interface {
	QuoteIdent(name string) string
	NewParams() ParamSink
	RenderIn(column, placeholder string) string
	RenderNotIn(column, placeholder string) string
	RenderContains(haystack, needle string) string
	Name() string
}

// Unsupported is returned when a dialect cannot render part of an expression.
// It wraps an *amino.Error with CodeUnsupported.
func Unsupported(format string, args ...any) error {
	return &amino.Error{Code: amino.CodeUnsupported, Message: fmt.Sprintf(format, args...)}
}

var comparisons = map[string]string{"=": "=", "!=": "<>", ">": ">", "<": "<", ">=": ">=", "<=": "<="}

// Compile renders expr for the dialect. columns maps a field path to a SQL
// fragment rendered verbatim; it is required for nested struct fields and
// is trusted developer input, never user input.
func Compile(d Dialect, expr *amino.Expression, columns map[string]string) (Query, error) {
	c := &compiler{d: d, expr: expr, columns: columns, sink: d.NewParams()}
	sql, err := c.render(expr.Root)
	if err != nil {
		return Query{}, err
	}
	return Query{SQL: sql, Params: c.sink.Result()}, nil
}

type compiler struct {
	d       Dialect
	expr    *amino.Expression
	columns map[string]string
	sink    ParamSink
}

func (c *compiler) render(n amino.Node) (string, error) {
	switch node := n.(type) {
	case *amino.Literal:
		if node.Type == "List" {
			return "", Unsupported("list literals are only supported on the right of 'in' / 'not in'")
		}
		return c.sink.Add(node.Value, c.expr.BaseType(node.Type)), nil
	case *amino.Variable:
		if mapped, ok := c.columns[node.Name]; ok {
			return mapped, nil
		}
		if strings.Contains(node.Name, ".") {
			return "", Unsupported("nested field %q has no column mapping", node.Name)
		}
		return c.d.QuoteIdent(node.Name), nil
	case *amino.Unary:
		if node.Op != "not" {
			return "", Unsupported("operator %q is not supported by %s", node.Op, c.d.Name())
		}
		inner, err := c.render(node.Operand)
		if err != nil {
			return "", err
		}
		return "(NOT " + inner + ")", nil
	case *amino.Binary:
		return c.renderBinary(node)
	case *amino.Call:
		args := make([]string, len(node.Args))
		for i, a := range node.Args {
			s, err := c.render(a)
			if err != nil {
				return "", err
			}
			args[i] = s
		}
		return node.Name + "(" + strings.Join(args, ", ") + ")", nil
	}
	return "", Unsupported("unknown node type %T", n)
}

func (c *compiler) renderBinary(node *amino.Binary) (string, error) {
	switch node.Op {
	case "and", "or":
		l, err := c.render(node.Left)
		if err != nil {
			return "", err
		}
		r, err := c.render(node.Right)
		if err != nil {
			return "", err
		}
		return "(" + l + " " + strings.ToUpper(node.Op) + " " + r + ")", nil
	case "in", "not in":
		return c.renderMembership(node)
	case "contains":
		hay, err := c.render(node.Left)
		if err != nil {
			return "", err
		}
		needle, err := c.render(node.Right)
		if err != nil {
			return "", err
		}
		return "(" + c.d.RenderContains(hay, needle) + ")", nil
	}
	if op, ok := comparisons[node.Op]; ok {
		l, err := c.render(node.Left)
		if err != nil {
			return "", err
		}
		r, err := c.render(node.Right)
		if err != nil {
			return "", err
		}
		return "(" + l + " " + op + " " + r + ")", nil
	}
	return "", Unsupported("operator %q is not supported by %s", node.Op, c.d.Name())
}

func (c *compiler) renderMembership(node *amino.Binary) (string, error) {
	lit, ok := node.Right.(*amino.Literal)
	if !ok || lit.Type != "List" {
		return "", Unsupported("'in' / 'not in' require a list literal on the right")
	}
	items, _ := lit.Value.([]any)
	negated := node.Op == "not in"
	if len(items) == 0 {
		if negated {
			return "TRUE", nil
		}
		return "FALSE", nil
	}
	left, err := c.render(node.Left)
	if err != nil {
		return "", err
	}
	elem, err := elementBase(items)
	if err != nil {
		return "", err
	}
	ph := c.sink.Add(items, "List["+elem+"]")
	if negated {
		return "(" + c.d.RenderNotIn(left, ph) + ")", nil
	}
	return "(" + c.d.RenderIn(left, ph) + ")", nil
}

func elementBase(items []any) (string, error) {
	switch items[0].(type) {
	case bool:
		return "Bool", nil
	case int64:
		return "Int", nil
	case float64:
		return "Float", nil
	case string:
		return "Str", nil
	}
	return "", Unsupported("cannot bind list element of type %T", items[0])
}
