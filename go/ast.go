package amino

// Node is one node of a parsed expression. Every node carries the type the
// parser resolved for it: "Bool", "Int", "Float", "Str", "List", a custom type
// name, or a struct name. Targets walk this tree.
type Node interface {
	TypeName() string
}

// Literal is a constant. Value is int64, float64, string, bool, or []any for
// a list literal (whose elements are themselves int64, float64, string, bool,
// or nested []any).
type Literal struct {
	Value any
	Type  string
}

// Variable is a field reference, possibly dotted.
type Variable struct {
	Name string
	Type string
}

// Unary is a prefix operator applied to one operand.
type Unary struct {
	Op      string
	Operand Node
	Type    string
	Def     *OperatorDef
}

// Binary is an infix operator applied to two operands.
type Binary struct {
	Op    string
	Left  Node
	Right Node
	Type  string
	Def   *OperatorDef
}

// Call is a call to a schema-declared function.
type Call struct {
	Name string
	Args []Node
	Type string
}

func (n *Literal) TypeName() string  { return n.Type }
func (n *Variable) TypeName() string { return n.Type }
func (n *Unary) TypeName() string    { return n.Type }
func (n *Binary) TypeName() string   { return n.Type }
func (n *Call) TypeName() string     { return n.Type }
