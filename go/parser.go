package amino

import (
	"regexp"
	"strconv"
	"strings"
)

// ── tokenizer ──────────────────────────────────────────────────────────────

var fixedSymbols = []string{">=", "<=", "!=", ">", "<", "=", "(", ")", "[", "]", ",", "."}

var (
	tokFloatRe = regexp.MustCompile(`^-?\d+\.\d+`)
	tokIntRe   = regexp.MustCompile(`^-?\d+`)
	tokStrRe   = regexp.MustCompile(`^'[^']*'`)
	tokIdentRe = regexp.MustCompile(`^[a-zA-Z_][a-zA-Z0-9_]*`)
)

func tokenize(text string, opSymbols []string) ([]string, error) {
	symbols := append([]string{}, opSymbols...)
	symbols = append(symbols, fixedSymbols...)
	// Longest match first.
	for i := 1; i < len(symbols); i++ {
		for j := i; j > 0 && len(symbols[j]) > len(symbols[j-1]); j-- {
			symbols[j], symbols[j-1] = symbols[j-1], symbols[j]
		}
	}
	var tokens []string
	i := 0
	for i < len(text) {
		ch := text[i]
		if ch == ' ' || ch == '\t' {
			i++
			continue
		}
		rest := text[i:]
		if strings.HasPrefix(rest, "not in") {
			tokens = append(tokens, "not in")
			i += 6
			continue
		}
		if m := tokStrRe.FindString(rest); m != "" {
			tokens = append(tokens, m)
			i += len(m)
			continue
		}
		if m := tokFloatRe.FindString(rest); m != "" {
			tokens = append(tokens, m)
			i += len(m)
			continue
		}
		if m := tokIntRe.FindString(rest); m != "" {
			tokens = append(tokens, m)
			i += len(m)
			continue
		}
		if m := tokIdentRe.FindString(rest); m != "" {
			tokens = append(tokens, m)
			i += len(m)
			continue
		}
		matched := false
		for _, sym := range symbols {
			if strings.HasPrefix(rest, sym) {
				tokens = append(tokens, sym)
				i += len(sym)
				matched = true
				break
			}
		}
		if !matched {
			return nil, newError(CodeSyntax, "unexpected character %q at position %d", string(ch), i)
		}
	}
	return tokens, nil
}

// ── parser ─────────────────────────────────────────────────────────────────

type parser struct {
	tokens   []string
	pos      int
	schema   *Schema
	ops      *operatorRegistry
	types    *typeRegistry
	depth    int
	maxDepth int
	builtin  map[string]bool // every built-in operator token, enabled or not
}

func (p *parser) peek() (string, bool) {
	if p.pos < len(p.tokens) {
		return p.tokens[p.pos], true
	}
	return "", false
}

func (p *parser) advance() (string, error) {
	if p.pos >= len(p.tokens) {
		return "", newError(CodeSyntax, "unexpected end of expression")
	}
	t := p.tokens[p.pos]
	p.pos++
	return t, nil
}

func (p *parser) leftBP(tok string) int {
	bp, ok := p.ops.bindingPower(tok)
	if !ok {
		return 0
	}
	return bp
}

func (p *parser) parse() (Node, error) {
	node, err := p.parseExpr(0)
	if err != nil {
		return nil, err
	}
	if tok, ok := p.peek(); ok {
		if p.builtin[tok] {
			return nil, newError(CodeUnknownOperator, "operator %q is not enabled", tok)
		}
		return nil, newError(CodeSyntax, "unexpected token %q", tok)
	}
	return node, nil
}

func (p *parser) enter() error {
	p.depth++
	if p.depth > p.maxDepth {
		return newError(CodeDepthExceeded, "expression nesting exceeds %d", p.maxDepth)
	}
	return nil
}

func (p *parser) parseExpr(minBP int) (Node, error) {
	if err := p.enter(); err != nil {
		return nil, err
	}
	defer func() { p.depth-- }()

	left, err := p.nud()
	if err != nil {
		return nil, err
	}
	for {
		tok, ok := p.peek()
		if !ok || tok == ")" || tok == "]" || tok == "," {
			break
		}
		twoTokenNotIn := tok == "not" && p.pos+1 < len(p.tokens) && p.tokens[p.pos+1] == "in"
		if twoTokenNotIn {
			tok = "not in"
		}
		bp := p.leftBP(tok)
		if bp <= minBP {
			break
		}
		p.pos++
		if twoTokenNotIn {
			p.pos++
		}
		left, err = p.led(tok, left)
		if err != nil {
			return nil, err
		}
	}
	return left, nil
}

func (p *parser) nud() (Node, error) {
	tok, err := p.advance()
	if err != nil {
		return nil, err
	}

	if tok == "(" {
		node, err := p.parseExpr(0)
		if err != nil {
			return nil, err
		}
		if t, ok := p.peek(); !ok || t != ")" {
			return nil, newError(CodeSyntax, "expected ')'")
		}
		p.pos++
		return node, nil
	}

	if tok == "[" {
		items, err := p.parseListBody()
		if err != nil {
			return nil, err
		}
		return &Literal{Value: items, Type: "List"}, nil
	}

	if def := p.ops.prefix(tok); def != nil {
		operand, err := p.parseExpr(def.BindingPower)
		if err != nil {
			return nil, err
		}
		if !p.compatible(def.InputTypes[0], operand.TypeName()) {
			return nil, newError(CodeTypeMismatch, "operator %q expects %s, got %s", tok, def.InputTypes[0], operand.TypeName())
		}
		return &Unary{Op: tok, Operand: operand, Type: def.ReturnType, Def: def}, nil
	}

	if tokFloatRe.MatchString(tok) && len(tokFloatRe.FindString(tok)) == len(tok) {
		f, _ := strconv.ParseFloat(tok, 64)
		return &Literal{Value: f, Type: "Float"}, nil
	}
	if tokIntRe.MatchString(tok) && len(tokIntRe.FindString(tok)) == len(tok) {
		i, err := strconv.ParseInt(tok, 10, 64)
		if err != nil {
			return nil, newError(CodeSyntax, "integer literal out of range: %s", tok)
		}
		return &Literal{Value: i, Type: "Int"}, nil
	}
	if len(tok) >= 2 && tok[0] == '\'' && tok[len(tok)-1] == '\'' {
		return &Literal{Value: tok[1 : len(tok)-1], Type: "Str"}, nil
	}
	if tok == "true" {
		return &Literal{Value: true, Type: "Bool"}, nil
	}
	if tok == "false" {
		return &Literal{Value: false, Type: "Bool"}, nil
	}

	if tokIdentRe.MatchString(tok) && len(tokIdentRe.FindString(tok)) == len(tok) {
		if t, ok := p.peek(); ok && t == "(" {
			return p.parseCall(tok)
		}
		name := tok
		for {
			t, ok := p.peek()
			if !ok || t != "." {
				break
			}
			p.pos++
			part, err := p.advance()
			if err != nil {
				return nil, err
			}
			name += "." + part
		}
		f := p.schema.Lookup(name)
		if f == nil {
			return nil, newError(CodeUnknownField, "unknown field %q", name)
		}
		return &Variable{Name: name, Type: f.TypeName}, nil
	}

	if p.builtin[tok] {
		return nil, newError(CodeSyntax, "operator %q has no left operand", tok)
	}
	return nil, newError(CodeSyntax, "unexpected token %q", tok)
}

func (p *parser) led(tok string, left Node) (Node, error) {
	right, err := p.parseExpr(p.leftBP(tok))
	if err != nil {
		return nil, err
	}
	def, err := p.resolve(tok, left, right)
	if err != nil {
		return nil, err
	}
	return &Binary{Op: tok, Left: left, Right: right, Type: def.ReturnType, Def: def}, nil
}

// resolve picks the operator definition for the operand types, or reports a
// type mismatch. Exact type-name matches win; then definitions whose declared
// input types are compatible by base type; wildcard definitions apply the
// built-in compatibility rules.
func (p *parser) resolve(tok string, left, right Node) (*OperatorDef, error) {
	lt, rt := left.TypeName(), right.TypeName()
	cands := p.ops.candidates(tok)
	if len(cands) == 0 {
		return nil, newError(CodeUnknownOperator, "no operator %q", tok)
	}
	for _, d := range cands {
		if len(d.InputTypes) == 2 && d.InputTypes[0] == lt && d.InputTypes[1] == rt {
			return d, nil
		}
	}
	for _, d := range cands {
		if len(d.InputTypes) != 2 {
			continue
		}
		if p.compatible(d.InputTypes[0], lt) && p.compatible(d.InputTypes[1], rt) {
			if d.InputTypes[0] == "*" && d.InputTypes[1] == "*" {
				if err := p.checkBuiltin(tok, lt, rt, right); err != nil {
					return nil, err
				}
			}
			if d.InputTypes[1] == "List" {
				if err := p.checkMembership(tok, lt, right); err != nil {
					return nil, err
				}
			}
			return d, nil
		}
	}
	return nil, newError(CodeTypeMismatch, "no operator %q for types (%s, %s)", tok, lt, rt)
}

// compatible reports whether a value of type actual can be passed where the
// operator declares want.
func (p *parser) compatible(want, actual string) bool {
	if want == "*" {
		return true
	}
	wb, ab := p.baseOf(want), p.baseOf(actual)
	if wb == ab {
		return true
	}
	return isNumericBase(wb) && isNumericBase(ab)
}

func (p *parser) baseOf(name string) string {
	if strings.HasPrefix(name, "List[") || name == "List" {
		return "List"
	}
	return p.types.base(name)
}

func isNumericBase(b string) bool { return b == "Int" || b == "Float" }

// checkBuiltin applies the rules for the wildcard-typed comparison operators.
func (p *parser) checkBuiltin(tok, lt, rt string, right Node) error {
	lb, rb := p.baseOf(lt), p.baseOf(rt)
	numeric := isNumericBase(lb) && isNumericBase(rb)
	switch tok {
	case "=", "!=":
		if lb == rb || numeric {
			return nil
		}
	case ">", "<", ">=", "<=":
		if numeric || (lb == "Str" && rb == "Str") {
			return nil
		}
	default:
		return nil
	}
	return newError(CodeTypeMismatch, "cannot apply %q to %s and %s", tok, lt, rt)
}

// checkMembership requires a list literal on the right whose elements match
// the left operand's type.
func (p *parser) checkMembership(tok, lt string, right Node) error {
	lit, ok := right.(*Literal)
	if !ok || lit.Type != "List" {
		return newError(CodeTypeMismatch, "%q needs a list literal on the right", tok)
	}
	items, _ := lit.Value.([]any)
	if len(items) == 0 {
		return nil
	}
	eb := literalBase(items[0])
	lb := p.baseOf(lt)
	if lb == eb || (isNumericBase(lb) && isNumericBase(eb)) {
		return nil
	}
	return newError(CodeTypeMismatch, "cannot test %s membership in a list of %s", lt, eb)
}

func literalBase(v any) string {
	switch v.(type) {
	case bool:
		return "Bool"
	case int64:
		return "Int"
	case float64:
		return "Float"
	case string:
		return "Str"
	case []any:
		return "List"
	}
	return "?"
}

func (p *parser) parseCall(name string) (Node, error) {
	p.pos++ // (
	var args []Node
	for {
		t, ok := p.peek()
		if !ok {
			return nil, newError(CodeSyntax, "unexpected end of expression in call to %q", name)
		}
		if t == ")" {
			break
		}
		arg, err := p.parseExpr(0)
		if err != nil {
			return nil, err
		}
		args = append(args, arg)
		if t, ok := p.peek(); ok && t == "," {
			p.pos++
		}
	}
	p.pos++ // )
	fn := p.schema.LookupFunction(name)
	if fn == nil {
		return nil, newError(CodeUnknownFunction, "unknown function %q", name)
	}
	required := 0
	for _, prm := range fn.Params {
		if !prm.Optional {
			required++
		}
	}
	if len(args) < required || len(args) > len(fn.Params) {
		return nil, newError(CodeTypeMismatch, "function %q takes %d to %d arguments, got %d", name, required, len(fn.Params), len(args))
	}
	for i, arg := range args {
		if !p.compatible(fn.Params[i].TypeName, arg.TypeName()) {
			return nil, newError(CodeTypeMismatch, "function %q argument %d expects %s, got %s", name, i+1, fn.Params[i].TypeName, arg.TypeName())
		}
	}
	return &Call{Name: name, Args: args, Type: fn.ReturnType}, nil
}

func (p *parser) parseListBody() ([]any, error) {
	items := []any{}
	for {
		t, ok := p.peek()
		if !ok {
			return nil, newError(CodeSyntax, "unterminated list literal")
		}
		if t == "]" {
			break
		}
		v, err := p.parseLiteralValue()
		if err != nil {
			return nil, err
		}
		items = append(items, v)
		if t, ok := p.peek(); ok && t == "," {
			p.pos++
		}
	}
	p.pos++ // ]
	return items, nil
}

func (p *parser) parseLiteralValue() (any, error) {
	tok, err := p.advance()
	if err != nil {
		return nil, err
	}
	if tok == "[" {
		if err := p.enter(); err != nil {
			return nil, err
		}
		defer func() { p.depth-- }()
		return p.parseListBody()
	}
	if len(tok) >= 2 && tok[0] == '\'' && tok[len(tok)-1] == '\'' {
		return tok[1 : len(tok)-1], nil
	}
	if tok == "true" {
		return true, nil
	}
	if tok == "false" {
		return false, nil
	}
	if tokFloatRe.MatchString(tok) && len(tokFloatRe.FindString(tok)) == len(tok) {
		f, _ := strconv.ParseFloat(tok, 64)
		return f, nil
	}
	if tokIntRe.MatchString(tok) && len(tokIntRe.FindString(tok)) == len(tok) {
		i, err := strconv.ParseInt(tok, 10, 64)
		if err != nil {
			return nil, newError(CodeSyntax, "integer literal out of range: %s", tok)
		}
		return i, nil
	}
	return nil, newError(CodeSyntax, "expected literal, got %q", tok)
}

func parseExpression(text string, e *Engine) (Node, error) {
	if len(text) > e.maxLength {
		return nil, newError(CodeSyntax, "expression longer than %d characters", e.maxLength)
	}
	tokens, err := tokenize(strings.TrimSpace(text), e.ops.symbolList())
	if err != nil {
		return nil, err
	}
	p := &parser{tokens: tokens, schema: e.schema, ops: e.ops, types: e.types, maxDepth: e.maxDepth, builtin: builtinTokens()}
	return p.parse()
}

func builtinTokens() map[string]bool {
	out := map[string]bool{}
	for _, d := range standardOperators() {
		out[d.Token()] = true
	}
	return out
}
