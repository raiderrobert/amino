package amino

import (
	"encoding/json"
	"math"
	"strings"
)

// toFloat converts any Go numeric (and json.Number) to float64.
func toFloat(v any) (float64, bool) {
	switch x := v.(type) {
	case int:
		return float64(x), true
	case int8:
		return float64(x), true
	case int16:
		return float64(x), true
	case int32:
		return float64(x), true
	case int64:
		return float64(x), true
	case uint:
		return float64(x), true
	case uint8:
		return float64(x), true
	case uint16:
		return float64(x), true
	case uint32:
		return float64(x), true
	case uint64:
		return float64(x), true
	case float32:
		return float64(x), true
	case float64:
		return x, true
	case json.Number:
		f, err := x.Float64()
		return f, err == nil
	}
	return 0, false
}

func isInteger(v any) bool {
	switch x := v.(type) {
	case int, int8, int16, int32, int64, uint, uint8, uint16, uint32, uint64:
		return true
	case json.Number:
		_, err := x.Int64()
		return err == nil
	case float64:
		return x == math.Trunc(x) && !math.IsInf(x, 0)
	}
	return false
}

func isNumber(v any) bool {
	_, ok := toFloat(v)
	return ok
}

// equalValues implements "=" with Python's cross-type rules for the types the
// language can produce: numbers compare numerically, strings, bools and lists
// compare structurally, anything else is an error (which makes the rule false).
func equalValues(a, b any) (bool, error) {
	if isNumber(a) && isNumber(b) {
		fa, _ := toFloat(a)
		fb, _ := toFloat(b)
		return fa == fb, nil
	}
	switch x := a.(type) {
	case string:
		y, ok := b.(string)
		return ok && x == y, nil
	case bool:
		y, ok := b.(bool)
		return ok && x == y, nil
	case []any:
		y, ok := b.([]any)
		if !ok || len(x) != len(y) {
			return false, nil
		}
		for i := range x {
			eq, err := equalValues(x[i], y[i])
			if err != nil || !eq {
				return false, nil
			}
		}
		return true, nil
	case nil:
		return b == nil, nil
	}
	return false, newError(CodeEvaluation, "cannot compare %T with %T", a, b)
}

// compareValues orders two numbers or two strings.
func compareValues(a, b any) (int, error) {
	if isNumber(a) && isNumber(b) {
		fa, _ := toFloat(a)
		fb, _ := toFloat(b)
		switch {
		case fa < fb:
			return -1, nil
		case fa > fb:
			return 1, nil
		}
		return 0, nil
	}
	if sa, ok := a.(string); ok {
		if sb, ok := b.(string); ok {
			return strings.Compare(sa, sb), nil
		}
	}
	return 0, newError(CodeEvaluation, "cannot order %T and %T", a, b)
}

func inList(v, list any) (bool, error) {
	items, ok := list.([]any)
	if !ok {
		return false, newError(CodeEvaluation, "right side of 'in' is not a list")
	}
	for _, item := range items {
		if eq, err := equalValues(v, item); err == nil && eq {
			return true, nil
		}
	}
	return false, nil
}

func containsString(hay, needle string) bool { return strings.Contains(hay, needle) }

// truthy follows Python truthiness for the values the evaluator can see.
func truthy(v any) bool {
	switch x := v.(type) {
	case nil:
		return false
	case bool:
		return x
	case string:
		return x != ""
	case []any:
		return len(x) > 0
	case map[string]any:
		return len(x) > 0
	}
	if f, ok := toFloat(v); ok {
		return f != 0
	}
	return true
}
