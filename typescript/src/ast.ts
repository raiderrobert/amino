import type { ResolvedOperator } from "./operators.js";

/**
 * One node of a parsed expression. Every node carries the type the parser
 * resolved for it: "Bool", "Int", "Float", "Str", "List", a custom type name,
 * or a struct name. Targets walk this tree.
 */
export type Node = Literal | Variable | Unary | Binary | Call;

/** A list literal's elements: numbers, strings, booleans, or nested lists. */
export type LiteralValue = number | string | boolean | LiteralValue[];

export interface Literal {
  node: "literal";
  value: LiteralValue;
  type: string;
}

export interface Variable {
  node: "variable";
  name: string;
  type: string;
}

export interface Unary {
  node: "unary";
  op: string;
  operand: Node;
  type: string;
  def: ResolvedOperator;
}

export interface Binary {
  node: "binary";
  op: string;
  left: Node;
  right: Node;
  type: string;
  def: ResolvedOperator;
}

export interface Call {
  node: "call";
  name: string;
  args: Node[];
  type: string;
}
