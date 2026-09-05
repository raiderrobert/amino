package amino

import (
	"net"
	"net/netip"
	"regexp"
	"strconv"
	"strings"
)

// TypeDef is a custom type: a name usable in schemas, the primitive it is
// stored as, and a validator run against record values.
type TypeDef struct {
	Name      string
	Base      string // "Str", "Int", "Float", "Bool"
	Validator func(any) bool
}

type typeRegistry struct {
	types map[string]TypeDef
}

func newTypeRegistry() *typeRegistry {
	r := &typeRegistry{types: map[string]TypeDef{}}
	for _, t := range builtinTypes() {
		r.types[t.Name] = t
	}
	return r
}

func (r *typeRegistry) register(t TypeDef) error {
	switch t.Base {
	case "Str", "Int", "Float", "Bool":
	default:
		return newError(CodeSchemaValidation, "base type must be Str, Int, Float, or Bool, got %q", t.Base)
	}
	r.types[t.Name] = t
	return nil
}

func (r *typeRegistry) names() map[string]bool {
	out := make(map[string]bool, len(r.types))
	for n := range r.types {
		out[n] = true
	}
	return out
}

// base reduces a type name to its primitive. Primitives and List return
// themselves; unknown names are returned unchanged.
func (r *typeRegistry) base(name string) string {
	if t, ok := r.types[name]; ok {
		return t.Base
	}
	return name
}

func (r *typeRegistry) validate(name string, v any) bool {
	t, ok := r.types[name]
	if !ok {
		return false
	}
	return t.Validator(v)
}

var emailRe = regexp.MustCompile(`^[^@\s]+@[^@\s]+\.[^@\s]+$`)
var uuidRe = regexp.MustCompile(`(?i)^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`)

func builtinTypes() []TypeDef {
	str := func(f func(string) bool) func(any) bool {
		return func(v any) bool {
			s, ok := v.(string)
			return ok && f(s)
		}
	}
	return []TypeDef{
		{Name: "ipv4", Base: "Str", Validator: str(func(s string) bool {
			parts := strings.Split(s, ".")
			if len(parts) != 4 {
				return false
			}
			for _, p := range parts {
				n, err := strconv.Atoi(p)
				if err != nil || n < 0 || n > 255 {
					return false
				}
			}
			return true
		})},
		{Name: "ipv6", Base: "Str", Validator: str(func(s string) bool {
			a, err := netip.ParseAddr(s)
			return err == nil && a.Is6()
		})},
		{Name: "cidr", Base: "Str", Validator: str(func(s string) bool {
			if !strings.Contains(s, "/") {
				return false
			}
			_, _, err := net.ParseCIDR(s)
			return err == nil
		})},
		{Name: "email", Base: "Str", Validator: str(emailRe.MatchString)},
		{Name: "uuid", Base: "Str", Validator: str(uuidRe.MatchString)},
	}
}
