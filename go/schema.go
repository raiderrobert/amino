package amino

import (
	"fmt"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

// Kind classifies a field's declared type.
type Kind int

const (
	KindInt Kind = iota
	KindFloat
	KindStr
	KindBool
	KindList
	KindCustom // a struct name or a registered custom type
)

// Field is one declared field, at the top level or inside a struct.
type Field struct {
	Name         string
	Kind         Kind
	TypeName     string         // "Int", "List[Str]", "Address", "email"
	ElementTypes []string       // for lists
	Constraints  map[string]any // {min: 300, oneOf: [...]}
	Optional     bool
}

// Struct is a named group of fields usable as a type.
type Struct struct {
	Name   string
	Fields []Field
}

// Param is one declared function parameter.
type Param struct {
	Name     string
	TypeName string
	Optional bool
}

// Function is a declared function signature. The implementation is supplied
// with WithFunction.
type Function struct {
	Name       string
	Params     []Param
	ReturnType string
}

// Schema is a parsed and validated .amn document.
type Schema struct {
	Fields    []Field
	Structs   []Struct
	Functions []Function

	structs map[string]*Struct
	paths   map[string]*Field // "customer.billing.city" -> field
	funcs   map[string]*Function
}

var primitives = map[string]Kind{"Int": KindInt, "Float": KindFloat, "Str": KindStr, "Bool": KindBool}

var reserved = map[string]bool{"struct": true, "List": true}

// ParseSchema parses .amn text. Validation against custom types happens in
// LoadSchema, which knows which custom types are registered.
func ParseSchema(text string) (*Schema, error) {
	p := &schemaParser{text: text, line: 1}
	return p.parse()
}

type schemaParser struct {
	text string
	pos  int
	line int
}

func (p *schemaParser) peek() (byte, bool) {
	if p.pos < len(p.text) {
		return p.text[p.pos], true
	}
	return 0, false
}

func (p *schemaParser) advance() byte {
	ch := p.text[p.pos]
	if ch == '\n' {
		p.line++
	}
	p.pos++
	return ch
}

func (p *schemaParser) skipWS(newlines bool) {
	for p.pos < len(p.text) {
		ch := p.text[p.pos]
		switch {
		case ch == '#':
			for p.pos < len(p.text) && p.text[p.pos] != '\n' {
				p.pos++
			}
		case ch == ' ' || ch == '\t':
			p.pos++
		case newlines && (ch == '\n' || ch == '\r'):
			if ch == '\n' {
				p.line++
			}
			p.pos++
		default:
			return
		}
	}
}

func (p *schemaParser) skipH() {
	for p.pos < len(p.text) && (p.text[p.pos] == ' ' || p.text[p.pos] == '\t') {
		p.pos++
	}
}

var identRe = regexp.MustCompile(`^[a-zA-Z_][a-zA-Z0-9_]*`)

func (p *schemaParser) readIdent() (string, error) {
	m := identRe.FindString(p.text[p.pos:])
	if m == "" {
		return "", newError(CodeSchemaParse, "expected identifier at line %d", p.line)
	}
	p.pos += len(m)
	return m, nil
}

func (p *schemaParser) expect(ch byte) error {
	p.skipH()
	got, ok := p.peek()
	if !ok || got != ch {
		return newError(CodeSchemaParse, "expected %q at line %d", string(ch), p.line)
	}
	p.advance()
	return nil
}

func (p *schemaParser) parseStrLiteral() (string, error) {
	p.advance() // opening '
	start := p.pos
	for {
		ch, ok := p.peek()
		if !ok {
			return "", newError(CodeSchemaParse, "unterminated string at line %d", p.line)
		}
		if ch == '\'' {
			break
		}
		p.advance()
	}
	s := p.text[start:p.pos]
	p.advance()
	return s, nil
}

func (p *schemaParser) parseListLit() ([]any, error) {
	p.advance() // [
	items := []any{}
	p.skipH()
	for {
		ch, ok := p.peek()
		if !ok {
			return nil, newError(CodeSchemaParse, "unterminated list at line %d", p.line)
		}
		if ch == ']' {
			break
		}
		v, err := p.parseConstraintVal()
		if err != nil {
			return nil, err
		}
		items = append(items, v)
		p.skipH()
		if ch, _ := p.peek(); ch == ',' {
			p.advance()
			p.skipH()
		}
	}
	p.advance() // ]
	return items, nil
}

var (
	floatRe = regexp.MustCompile(`^-?\d+\.\d+`)
	intRe   = regexp.MustCompile(`^-?\d+`)
	boolRe  = regexp.MustCompile(`^(true|false)`)
)

func (p *schemaParser) parseConstraintVal() (any, error) {
	p.skipH()
	ch, ok := p.peek()
	if !ok {
		return nil, newError(CodeSchemaParse, "expected constraint value at line %d", p.line)
	}
	if ch == '\'' {
		return p.parseStrLiteral()
	}
	if ch == '[' {
		return p.parseListLit()
	}
	rest := p.text[p.pos:]
	if m := floatRe.FindString(rest); m != "" {
		p.pos += len(m)
		f, _ := strconv.ParseFloat(m, 64)
		return f, nil
	}
	if m := intRe.FindString(rest); m != "" {
		p.pos += len(m)
		i, _ := strconv.ParseInt(m, 10, 64)
		return i, nil
	}
	if m := boolRe.FindString(rest); m != "" {
		p.pos += len(m)
		return m == "true", nil
	}
	return nil, newError(CodeSchemaParse, "expected constraint value at line %d", p.line)
}

func (p *schemaParser) parseConstraints() (map[string]any, error) {
	p.advance() // {
	out := map[string]any{}
	p.skipH()
	for {
		ch, ok := p.peek()
		if !ok {
			return nil, newError(CodeSchemaParse, "unterminated constraint block at line %d", p.line)
		}
		if ch == '}' {
			break
		}
		key, err := p.readIdent()
		if err != nil {
			return nil, err
		}
		if err := p.expect(':'); err != nil {
			return nil, err
		}
		v, err := p.parseConstraintVal()
		if err != nil {
			return nil, err
		}
		out[key] = v
		p.skipH()
		if ch, _ := p.peek(); ch == ',' {
			p.advance()
			p.skipH()
		}
	}
	p.advance() // }
	return out, nil
}

func (p *schemaParser) parseTypeExpr() (Kind, string, []string, error) {
	p.skipH()
	name, err := p.readIdent()
	if err != nil {
		return 0, "", nil, err
	}
	if name == "List" {
		if err := p.expect('['); err != nil {
			return 0, "", nil, err
		}
		first, err := p.readIdent()
		if err != nil {
			return 0, "", nil, err
		}
		elems := []string{first}
		for {
			ch, _ := p.peek()
			if ch != '|' {
				break
			}
			p.advance()
			e, err := p.readIdent()
			if err != nil {
				return 0, "", nil, err
			}
			elems = append(elems, e)
		}
		if err := p.expect(']'); err != nil {
			return 0, "", nil, err
		}
		return KindList, "List[" + strings.Join(elems, "|") + "]", elems, nil
	}
	if k, ok := primitives[name]; ok {
		return k, name, nil, nil
	}
	return KindCustom, name, nil, nil
}

func (p *schemaParser) parseField() (Field, error) {
	p.skipH()
	name, err := p.readIdent()
	if err != nil {
		return Field{}, err
	}
	if reserved[name] {
		return Field{}, newError(CodeSchemaParse, "reserved word %q used as field name at line %d", name, p.line)
	}
	if err := p.expect(':'); err != nil {
		return Field{}, err
	}
	kind, tname, elems, err := p.parseTypeExpr()
	if err != nil {
		return Field{}, err
	}
	f := Field{Name: name, Kind: kind, TypeName: tname, ElementTypes: elems, Constraints: map[string]any{}}
	p.skipH()
	if ch, _ := p.peek(); ch == '?' {
		f.Optional = true
		p.advance()
	}
	p.skipH()
	if ch, _ := p.peek(); ch == '{' {
		c, err := p.parseConstraints()
		if err != nil {
			return Field{}, err
		}
		f.Constraints = c
	}
	return f, nil
}

func (p *schemaParser) parseStruct() (Struct, error) {
	if _, err := p.readIdent(); err != nil { // 'struct'
		return Struct{}, err
	}
	p.skipH()
	name, err := p.readIdent()
	if err != nil {
		return Struct{}, err
	}
	p.skipWS(true)
	if err := p.expect('{'); err != nil {
		return Struct{}, err
	}
	s := Struct{Name: name}
	for {
		p.skipWS(true)
		ch, ok := p.peek()
		if !ok {
			return Struct{}, newError(CodeSchemaParse, "unterminated struct %q", name)
		}
		if ch == '}' {
			break
		}
		f, err := p.parseField()
		if err != nil {
			return Struct{}, err
		}
		s.Fields = append(s.Fields, f)
		p.skipH()
		if ch, _ := p.peek(); ch == ',' {
			p.advance()
		}
	}
	p.advance() // }
	return s, nil
}

func (p *schemaParser) isFunction() bool {
	savedPos, savedLine := p.pos, p.line
	defer func() { p.pos, p.line = savedPos, savedLine }()
	if _, err := p.readIdent(); err != nil {
		return false
	}
	p.skipH()
	if ch, _ := p.peek(); ch != ':' {
		return false
	}
	p.advance()
	p.skipH()
	ch, _ := p.peek()
	return ch == '('
}

func (p *schemaParser) parseFunction() (Function, error) {
	name, err := p.readIdent()
	if err != nil {
		return Function{}, err
	}
	if err := p.expect(':'); err != nil {
		return Function{}, err
	}
	if err := p.expect('('); err != nil {
		return Function{}, err
	}
	fn := Function{Name: name}
	p.skipH()
	for {
		ch, ok := p.peek()
		if !ok {
			return Function{}, newError(CodeSchemaParse, "unterminated parameter list at line %d", p.line)
		}
		if ch == ')' {
			break
		}
		pname, err := p.readIdent()
		if err != nil {
			return Function{}, err
		}
		if err := p.expect(':'); err != nil {
			return Function{}, err
		}
		_, tname, _, err := p.parseTypeExpr()
		if err != nil {
			return Function{}, err
		}
		param := Param{Name: pname, TypeName: tname}
		p.skipH()
		if ch, _ := p.peek(); ch == '?' {
			param.Optional = true
			p.advance()
		}
		fn.Params = append(fn.Params, param)
		p.skipH()
		if ch, _ := p.peek(); ch == ',' {
			p.advance()
			p.skipH()
		}
	}
	p.advance() // )
	p.skipH()
	if !strings.HasPrefix(p.text[p.pos:], "->") {
		return Function{}, newError(CodeSchemaParse, "expected '->' at line %d", p.line)
	}
	p.pos += 2
	p.skipH()
	ret, err := p.readIdent()
	if err != nil {
		return Function{}, err
	}
	p.skipH()
	if ch, _ := p.peek(); ch == '?' {
		p.advance()
	}
	fn.ReturnType = ret
	return fn, nil
}

var structKeywordRe = regexp.MustCompile(`^struct(?:[^a-zA-Z0-9_]|$)`)

func (p *schemaParser) parse() (*Schema, error) {
	s := &Schema{}
	for {
		p.skipWS(true)
		if p.pos >= len(p.text) {
			break
		}
		switch {
		case structKeywordRe.MatchString(p.text[p.pos:]):
			st, err := p.parseStruct()
			if err != nil {
				return nil, err
			}
			s.Structs = append(s.Structs, st)
		case p.isFunction():
			fn, err := p.parseFunction()
			if err != nil {
				return nil, err
			}
			s.Functions = append(s.Functions, fn)
		default:
			f, err := p.parseField()
			if err != nil {
				return nil, err
			}
			s.Fields = append(s.Fields, f)
		}
	}
	return s, nil
}

// validate checks references, duplicates, and cycles, then builds the lookup
// indexes. customTypes are the registered custom type names.
func (s *Schema) validate(customTypes map[string]bool) error {
	s.structs = map[string]*Struct{}
	for i := range s.Structs {
		s.structs[s.Structs[i].Name] = &s.Structs[i]
	}
	known := map[string]bool{"Int": true, "Float": true, "Str": true, "Bool": true, "List": true}
	for name := range s.structs {
		known[name] = true
	}
	for name := range customTypes {
		known[name] = true
	}

	seen := map[string]bool{}
	check := func(name string) error {
		if seen[name] {
			return newError(CodeSchemaValidation, "duplicate name %q", name)
		}
		seen[name] = true
		return nil
	}
	for _, f := range s.Fields {
		if err := check(f.Name); err != nil {
			return err
		}
	}
	for _, st := range s.Structs {
		if err := check(st.Name); err != nil {
			return err
		}
	}
	for _, fn := range s.Functions {
		if err := check(fn.Name); err != nil {
			return err
		}
	}

	for _, f := range s.Fields {
		if f.Kind == KindCustom && !known[f.TypeName] {
			return fieldError(CodeSchemaValidation, f.Name, "unknown type %q", f.TypeName)
		}
	}
	for _, st := range s.Structs {
		fieldSeen := map[string]bool{}
		for _, f := range st.Fields {
			if fieldSeen[f.Name] {
				return newError(CodeSchemaValidation, "duplicate field %q in struct %q", f.Name, st.Name)
			}
			fieldSeen[f.Name] = true
			if f.Kind == KindCustom && !known[f.TypeName] {
				return newError(CodeSchemaValidation, "unknown type %q in struct %q", f.TypeName, st.Name)
			}
		}
	}

	var dfs func(name string, visiting map[string]bool) error
	dfs = func(name string, visiting map[string]bool) error {
		if visiting[name] {
			return newError(CodeSchemaValidation, "circular struct reference involving %q", name)
		}
		st, ok := s.structs[name]
		if !ok {
			return nil
		}
		next := map[string]bool{name: true}
		for k := range visiting {
			next[k] = true
		}
		for _, f := range st.Fields {
			if f.Kind == KindCustom {
				if _, isStruct := s.structs[f.TypeName]; isStruct {
					if err := dfs(f.TypeName, next); err != nil {
						return err
					}
				}
			}
		}
		return nil
	}
	names := make([]string, 0, len(s.structs))
	for name := range s.structs {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		if err := dfs(name, map[string]bool{}); err != nil {
			return err
		}
	}

	s.paths = map[string]*Field{}
	for i := range s.Fields {
		f := &s.Fields[i]
		s.paths[f.Name] = f
		if _, isStruct := s.structs[f.TypeName]; isStruct {
			s.indexStruct(f.Name, f.TypeName)
		}
	}
	s.funcs = map[string]*Function{}
	for i := range s.Functions {
		s.funcs[s.Functions[i].Name] = &s.Functions[i]
	}
	return nil
}

func (s *Schema) indexStruct(prefix, structName string) {
	st, ok := s.structs[structName]
	if !ok {
		return
	}
	for i := range st.Fields {
		f := &st.Fields[i]
		key := prefix + "." + f.Name
		s.paths[key] = f
		if _, isStruct := s.structs[f.TypeName]; isStruct {
			s.indexStruct(key, f.TypeName)
		}
	}
}

// Lookup returns the field at a dotted path, or nil.
func (s *Schema) Lookup(path string) *Field { return s.paths[path] }

// LookupFunction returns the declared function, or nil.
func (s *Schema) LookupFunction(name string) *Function { return s.funcs[name] }

// IsStruct reports whether name is a declared struct.
func (s *Schema) IsStruct(name string) bool { _, ok := s.structs[name]; return ok }

// Export renders the schema back to .amn text: structs, then fields, then functions.
func (s *Schema) Export() string {
	var b strings.Builder
	fieldStr := func(f Field) string {
		q := ""
		if f.Optional {
			q = "?"
		}
		c := ""
		if len(f.Constraints) > 0 {
			keys := make([]string, 0, len(f.Constraints))
			for k := range f.Constraints {
				keys = append(keys, k)
			}
			sort.Strings(keys)
			parts := make([]string, 0, len(keys))
			for _, k := range keys {
				parts = append(parts, fmt.Sprintf("%s: %s", k, exportValue(f.Constraints[k])))
			}
			c = " {" + strings.Join(parts, ", ") + "}"
		}
		return f.Name + ": " + f.TypeName + q + c
	}
	for _, st := range s.Structs {
		parts := make([]string, 0, len(st.Fields))
		for _, f := range st.Fields {
			parts = append(parts, fieldStr(f))
		}
		fmt.Fprintf(&b, "struct %s {%s}\n", st.Name, strings.Join(parts, ", "))
	}
	for _, f := range s.Fields {
		b.WriteString(fieldStr(f))
		b.WriteByte('\n')
	}
	for _, fn := range s.Functions {
		params := make([]string, 0, len(fn.Params))
		for _, p := range fn.Params {
			q := ""
			if p.Optional {
				q = "?"
			}
			params = append(params, p.Name+": "+p.TypeName+q)
		}
		fmt.Fprintf(&b, "%s: (%s) -> %s\n", fn.Name, strings.Join(params, ", "), fn.ReturnType)
	}
	return strings.TrimRight(b.String(), "\n")
}

func exportValue(v any) string {
	switch x := v.(type) {
	case string:
		return "'" + x + "'"
	case []any:
		parts := make([]string, len(x))
		for i, e := range x {
			parts[i] = exportValue(e)
		}
		return "[" + strings.Join(parts, ", ") + "]"
	case bool:
		if x {
			return "true"
		}
		return "false"
	default:
		return fmt.Sprint(x)
	}
}
