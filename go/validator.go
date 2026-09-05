package amino

import (
	"fmt"
	"regexp"
	"strings"
)

// validateDecision checks a record against the schema. In loose mode
// non-conforming fields are dropped and reported as warnings; in strict mode
// the first problem is returned as an error.
func (e *Engine) validateDecision(decision map[string]any) (map[string]any, []string, error) {
	cleaned := map[string]any{}
	var warnings []string
	strict := e.decisionsMode == "strict"

	fail := func(f *Field, msg string) error {
		if strict {
			return fieldError(CodeDecisionValidation, f.Name, "%s", msg)
		}
		warnings = append(warnings, msg)
		return nil
	}

	for i := range e.schema.Fields {
		f := &e.schema.Fields[i]
		value, present := decision[f.Name]
		if !present {
			if f.Optional {
				continue
			}
			if err := fail(f, fmt.Sprintf("required field %q is missing", f.Name)); err != nil {
				return nil, nil, err
			}
			continue
		}
		if value == nil {
			if f.Optional {
				continue
			}
			if err := fail(f, fmt.Sprintf("field %q expected %s, got null", f.Name, f.TypeName)); err != nil {
				return nil, nil, err
			}
			continue
		}
		if !e.checkType(value, f) {
			if err := fail(f, fmt.Sprintf("field %q expected %s, got %T", f.Name, f.TypeName, value)); err != nil {
				return nil, nil, err
			}
			continue
		}
		if len(f.Constraints) > 0 {
			if v := checkConstraints(value, f.Constraints); v != "" {
				if err := fail(f, fmt.Sprintf("field %q constraint violation: %s", f.Name, v)); err != nil {
					return nil, nil, err
				}
				continue
			}
		}
		cleaned[f.Name] = value
	}
	for k, v := range decision {
		if _, ok := cleaned[k]; !ok && e.schema.Lookup(k) == nil {
			cleaned[k] = v
		}
	}
	return cleaned, warnings, nil
}

func (e *Engine) checkType(value any, f *Field) bool {
	switch f.Kind {
	case KindInt:
		if _, isBool := value.(bool); isBool {
			return false
		}
		return isInteger(value)
	case KindFloat:
		if _, isBool := value.(bool); isBool {
			return false
		}
		return isNumber(value)
	case KindStr:
		_, ok := value.(string)
		return ok
	case KindBool:
		_, ok := value.(bool)
		return ok
	case KindList:
		_, ok := value.([]any)
		return ok
	case KindCustom:
		if e.schema.IsStruct(f.TypeName) {
			_, ok := value.(map[string]any)
			return ok
		}
		if t, ok := e.types.types[f.TypeName]; ok {
			return checkBase(value, t.Base) && e.types.validate(f.TypeName, value)
		}
		return true
	}
	return true
}

func checkBase(value any, base string) bool {
	switch base {
	case "Int":
		_, isBool := value.(bool)
		return !isBool && isInteger(value)
	case "Float":
		_, isBool := value.(bool)
		return !isBool && isNumber(value)
	case "Str":
		_, ok := value.(string)
		return ok
	case "Bool":
		_, ok := value.(bool)
		return ok
	}
	return true
}

func checkConstraints(value any, constraints map[string]any) string {
	num, isNum := toFloat(value)
	str, isStr := value.(string)
	list, isList := value.([]any)
	length := -1
	if isStr {
		length = len([]rune(str))
	} else if isList {
		length = len(list)
	}
	for key, cv := range constraints {
		bound, boundIsNum := toFloat(cv)
		switch key {
		case "min":
			if isNum && boundIsNum && num < bound {
				return fmt.Sprintf("value %v below min %v", value, cv)
			}
		case "max":
			if isNum && boundIsNum && num > bound {
				return fmt.Sprintf("value %v above max %v", value, cv)
			}
		case "exclusiveMin":
			if isNum && boundIsNum && num <= bound {
				return fmt.Sprintf("value %v not above exclusiveMin %v", value, cv)
			}
		case "exclusiveMax":
			if isNum && boundIsNum && num >= bound {
				return fmt.Sprintf("value %v not below exclusiveMax %v", value, cv)
			}
		case "minLength":
			if length >= 0 && boundIsNum && float64(length) < bound {
				return fmt.Sprintf("length %d below minLength %v", length, cv)
			}
		case "maxLength":
			if length >= 0 && boundIsNum && float64(length) > bound {
				return fmt.Sprintf("length %d above maxLength %v", length, cv)
			}
		case "exactLength":
			if length >= 0 && boundIsNum && float64(length) != bound {
				return fmt.Sprintf("length must be %v", cv)
			}
		case "pattern":
			pat, ok := cv.(string)
			if ok && isStr {
				re, err := regexp.Compile("^(?:" + pat + ")$")
				if err != nil || !re.MatchString(str) {
					return fmt.Sprintf("value does not match pattern %q", pat)
				}
			}
		case "oneOf":
			opts, ok := cv.([]any)
			if ok {
				found := false
				for _, o := range opts {
					if eq, err := equalValues(value, o); err == nil && eq {
						found = true
						break
					}
				}
				if !found {
					return fmt.Sprintf("value %v not in %v", value, cv)
				}
			}
		case "const":
			if eq, err := equalValues(value, cv); err != nil || !eq {
				return fmt.Sprintf("value must equal %v", cv)
			}
		case "minItems":
			if isList && boundIsNum && float64(len(list)) < bound {
				return fmt.Sprintf("list length %d below minItems %v", len(list), cv)
			}
		case "maxItems":
			if isList && boundIsNum && float64(len(list)) > bound {
				return fmt.Sprintf("list length %d above maxItems %v", len(list), cv)
			}
		case "unique":
			if on, ok := cv.(bool); ok && on && isList {
				seen := map[string]bool{}
				for _, item := range list {
					k := fmt.Sprintf("%T:%v", item, item)
					if seen[k] {
						return "list elements must be unique"
					}
					seen[k] = true
				}
			}
		}
	}
	return ""
}

var _ = strings.TrimSpace
