package amino

import "strings"

// Func implements a schema-declared function on the in-process target.
type Func func(args ...any) (any, error)

type evalFn func(rec map[string]any, fns map[string]Func) (any, error)

// compileNode turns the typed AST into a closure. Errors during evaluation
// make the rule false; see CompiledRules.
func compileNode(n Node) evalFn {
	switch node := n.(type) {
	case *Literal:
		v := node.Value
		return func(map[string]any, map[string]Func) (any, error) { return v, nil }

	case *Variable:
		parts := strings.Split(node.Name, ".")
		name := node.Name
		return func(rec map[string]any, _ map[string]Func) (any, error) {
			var cur any = rec
			for _, part := range parts {
				m, ok := cur.(map[string]any)
				if !ok {
					return nil, fieldError(CodeEvaluation, name, "field %q not found", name)
				}
				v, ok := m[part]
				if !ok {
					return nil, fieldError(CodeEvaluation, name, "field %q not found", name)
				}
				cur = v
			}
			return cur, nil
		}

	case *Unary:
		operand := compileNode(node.Operand)
		if node.Op == "not" {
			return func(rec map[string]any, fns map[string]Func) (any, error) {
				v, err := operand(rec, fns)
				if err != nil {
					return nil, err
				}
				return !truthy(v), nil
			}
		}
		fn := node.Def.Fn
		return func(rec map[string]any, fns map[string]Func) (any, error) {
			v, err := operand(rec, fns)
			if err != nil {
				return nil, err
			}
			return fn(v)
		}

	case *Binary:
		left := compileNode(node.Left)
		right := compileNode(node.Right)
		switch node.Op {
		case "and":
			return func(rec map[string]any, fns map[string]Func) (any, error) {
				lv, err := left(rec, fns)
				if err != nil {
					return false, nil
				}
				if !truthy(lv) {
					return false, nil
				}
				rv, err := right(rec, fns)
				if err != nil {
					return nil, err
				}
				return truthy(rv), nil
			}
		case "or":
			return func(rec map[string]any, fns map[string]Func) (any, error) {
				lv, err := left(rec, fns)
				if err == nil && truthy(lv) {
					return true, nil
				}
				rv, err := right(rec, fns)
				if err != nil {
					return false, nil
				}
				return truthy(rv), nil
			}
		}
		fn := node.Def.Fn
		return func(rec map[string]any, fns map[string]Func) (any, error) {
			lv, err := left(rec, fns)
			if err != nil {
				return nil, err
			}
			rv, err := right(rec, fns)
			if err != nil {
				return nil, err
			}
			return fn(lv, rv)
		}

	case *Call:
		args := make([]evalFn, len(node.Args))
		for i, a := range node.Args {
			args[i] = compileNode(a)
		}
		name := node.Name
		return func(rec map[string]any, fns map[string]Func) (any, error) {
			fn, ok := fns[name]
			if !ok {
				return nil, newError(CodeEvaluation, "function %q has no implementation", name)
			}
			vals := make([]any, len(args))
			for i, a := range args {
				v, err := a(rec, fns)
				if err != nil {
					return nil, err
				}
				vals[i] = v
			}
			return fn(vals...)
		}
	}
	panic("unreachable node type")
}
