import type { Binary, Call, Literal, LiteralValue, Node, Unary, Variable } from "./ast.js";
import { AminoError } from "./errors.js";
import type { OperatorRegistry, ResolvedOperator } from "./operators.js";
import { builtinTokens } from "./operators.js";
import type { Schema } from "./schema.js";
import type { TypeRegistry } from "./types.js";

const FIXED_SYMBOLS = [">=", "<=", "!=", ">", "<", "=", "(", ")", "[", "]", ",", "."];
const FLOAT = /^-?\d+\.\d+/;
const INT = /^-?\d+/;
const STR = /^'[^']*'/;
const IDENT = /^[a-zA-Z_][a-zA-Z0-9_]*/;
const FULL_FLOAT = /^-?\d+\.\d+$/;
const FULL_INT = /^-?\d+$/;
const FULL_IDENT = /^[a-zA-Z_][a-zA-Z0-9_]*$/;

export function tokenize(text: string, opSymbols: string[]): string[] {
  const symbols = [...opSymbols, ...FIXED_SYMBOLS].sort((a, b) => b.length - a.length);
  const tokens: string[] = [];
  let i = 0;
  while (i < text.length) {
    const ch = text[i] as string;
    if (ch === " " || ch === "\t") {
      i++;
      continue;
    }
    const rest = text.slice(i);
    if (rest.startsWith("not in")) {
      tokens.push("not in");
      i += 6;
      continue;
    }
    const m = STR.exec(rest) ?? FLOAT.exec(rest) ?? INT.exec(rest) ?? IDENT.exec(rest);
    if (m) {
      tokens.push(m[0]);
      i += m[0].length;
      continue;
    }
    const sym = symbols.find((s) => rest.startsWith(s));
    if (sym === undefined) throw new AminoError("syntax", `unexpected character "${ch}" at position ${i}`);
    tokens.push(sym);
    i += sym.length;
  }
  return tokens;
}

export interface ParserContext {
  schema: Schema;
  ops: OperatorRegistry;
  types: TypeRegistry;
  maxDepth: number;
  maxLength: number;
}

class Parser {
  private pos = 0;
  private depth = 0;
  private readonly builtin = builtinTokens();

  constructor(
    private readonly tokens: string[],
    private readonly ctx: ParserContext,
  ) {}

  private peek(): string | undefined {
    return this.tokens[this.pos];
  }

  private advance(): string {
    const t = this.tokens[this.pos];
    if (t === undefined) throw new AminoError("syntax", "unexpected end of expression");
    this.pos++;
    return t;
  }

  private leftBP(tok: string): number {
    return this.ctx.ops.bindingPower(tok) ?? 0;
  }

  parse(): Node {
    const node = this.parseExpr(0);
    const tok = this.peek();
    if (tok !== undefined) {
      if (this.builtin.has(tok)) throw new AminoError("unknown_operator", `operator "${tok}" is not enabled`);
      throw new AminoError("syntax", `unexpected token "${tok}"`);
    }
    return node;
  }

  private enter(): void {
    this.depth++;
    if (this.depth > this.ctx.maxDepth) {
      throw new AminoError("depth_exceeded", `expression nesting exceeds ${this.ctx.maxDepth}`);
    }
  }

  private parseExpr(minBP: number): Node {
    this.enter();
    try {
      let left = this.nud();
      for (;;) {
        let tok = this.peek();
        if (tok === undefined || tok === ")" || tok === "]" || tok === ",") break;
        const twoTokenNotIn = tok === "not" && this.tokens[this.pos + 1] === "in";
        if (twoTokenNotIn) tok = "not in";
        const bp = this.leftBP(tok);
        if (bp <= minBP) break;
        this.pos += twoTokenNotIn ? 2 : 1;
        left = this.led(tok, left);
      }
      return left;
    } finally {
      this.depth--;
    }
  }

  private nud(): Node {
    const tok = this.advance();

    if (tok === "(") {
      const node = this.parseExpr(0);
      if (this.peek() !== ")") throw new AminoError("syntax", "expected ')'");
      this.pos++;
      return node;
    }

    if (tok === "[") {
      const value = this.parseListBody();
      return { node: "literal", value, type: "List" } satisfies Literal;
    }

    const prefix = this.ctx.ops.prefix(tok);
    if (prefix) {
      const operand = this.parseExpr(prefix.bindingPower);
      const want = prefix.inputTypes[0] ?? "*";
      if (!this.compatible(want, operand.type)) {
        throw new AminoError("type_mismatch", `operator "${tok}" expects ${want}, got ${operand.type}`);
      }
      return { node: "unary", op: tok, operand, type: prefix.returnType, def: prefix } satisfies Unary;
    }

    if (FULL_FLOAT.test(tok)) return { node: "literal", value: parseFloat(tok), type: "Float" };
    if (FULL_INT.test(tok)) return { node: "literal", value: parseInt(tok, 10), type: "Int" };
    if (tok.length >= 2 && tok.startsWith("'") && tok.endsWith("'")) {
      return { node: "literal", value: tok.slice(1, -1), type: "Str" };
    }
    if (tok === "true") return { node: "literal", value: true, type: "Bool" };
    if (tok === "false") return { node: "literal", value: false, type: "Bool" };

    if (FULL_IDENT.test(tok)) {
      if (this.peek() === "(") return this.parseCall(tok);
      let name = tok;
      while (this.peek() === ".") {
        this.pos++;
        name += "." + this.advance();
      }
      const field = this.ctx.schema.lookup(name);
      if (!field) throw new AminoError("unknown_field", `unknown field "${name}"`);
      return { node: "variable", name, type: field.typeName } satisfies Variable;
    }

    if (this.builtin.has(tok)) throw new AminoError("syntax", `operator "${tok}" has no left operand`);
    throw new AminoError("syntax", `unexpected token "${tok}"`);
  }

  private led(tok: string, left: Node): Node {
    const right = this.parseExpr(this.leftBP(tok));
    const def = this.resolve(tok, left, right);
    return { node: "binary", op: tok, left, right, type: def.returnType, def } satisfies Binary;
  }

  private resolve(tok: string, left: Node, right: Node): ResolvedOperator {
    const lt = left.type;
    const rt = right.type;
    const cands = this.ctx.ops.candidates(tok);
    if (cands.length === 0) throw new AminoError("unknown_operator", `no operator "${tok}"`);
    for (const d of cands) {
      if (d.inputTypes.length === 2 && d.inputTypes[0] === lt && d.inputTypes[1] === rt) return d;
    }
    for (const d of cands) {
      if (d.inputTypes.length !== 2) continue;
      const [w0, w1] = d.inputTypes as [string, string];
      if (this.compatible(w0, lt) && this.compatible(w1, rt)) {
        if (w0 === "*" && w1 === "*") this.checkBuiltin(tok, lt, rt);
        if (w1 === "List") this.checkMembership(tok, lt, right);
        return d;
      }
    }
    throw new AminoError("type_mismatch", `no operator "${tok}" for types (${lt}, ${rt})`);
  }

  private compatible(want: string, actual: string): boolean {
    if (want === "*") return true;
    const wb = this.baseOf(want);
    const ab = this.baseOf(actual);
    return wb === ab || (isNumericBase(wb) && isNumericBase(ab));
  }

  private baseOf(name: string): string {
    if (name === "List" || name.startsWith("List[")) return "List";
    return this.ctx.types.base(name);
  }

  private checkBuiltin(tok: string, lt: string, rt: string): void {
    const lb = this.baseOf(lt);
    const rb = this.baseOf(rt);
    const numeric = isNumericBase(lb) && isNumericBase(rb);
    switch (tok) {
      case "=":
      case "!=":
        if (lb === rb || numeric) return;
        break;
      case ">":
      case "<":
      case ">=":
      case "<=":
        if (numeric || (lb === "Str" && rb === "Str")) return;
        break;
      default:
        return;
    }
    throw new AminoError("type_mismatch", `cannot apply "${tok}" to ${lt} and ${rt}`);
  }

  private checkMembership(tok: string, lt: string, right: Node): void {
    if (right.node !== "literal" || right.type !== "List") {
      throw new AminoError("type_mismatch", `"${tok}" needs a list literal on the right`);
    }
    const items = right.value as LiteralValue[];
    const first = items[0];
    if (first === undefined) return;
    const eb = literalBase(first);
    const lb = this.baseOf(lt);
    if (lb === eb || (isNumericBase(lb) && isNumericBase(eb))) return;
    throw new AminoError("type_mismatch", `cannot test ${lt} membership in a list of ${eb}`);
  }

  private parseCall(name: string): Call {
    this.pos++;
    const args: Node[] = [];
    for (;;) {
      const t = this.peek();
      if (t === undefined) throw new AminoError("syntax", `unexpected end of expression in call to "${name}"`);
      if (t === ")") break;
      args.push(this.parseExpr(0));
      if (this.peek() === ",") this.pos++;
    }
    this.pos++;
    const fn = this.ctx.schema.lookupFunction(name);
    if (!fn) throw new AminoError("unknown_function", `unknown function "${name}"`);
    const required = fn.params.filter((p) => !p.optional).length;
    if (args.length < required || args.length > fn.params.length) {
      throw new AminoError("type_mismatch", `function "${name}" takes ${required} to ${fn.params.length} arguments, got ${args.length}`);
    }
    args.forEach((arg, i) => {
      const param = fn.params[i] as (typeof fn.params)[number];
      if (!this.compatible(param.typeName, arg.type)) {
        throw new AminoError("type_mismatch", `function "${name}" argument ${i + 1} expects ${param.typeName}, got ${arg.type}`);
      }
    });
    return { node: "call", name, args, type: fn.returnType };
  }

  private parseListBody(): LiteralValue[] {
    const items: LiteralValue[] = [];
    for (;;) {
      const t = this.peek();
      if (t === undefined) throw new AminoError("syntax", "unterminated list literal");
      if (t === "]") break;
      items.push(this.parseLiteralValue());
      if (this.peek() === ",") this.pos++;
    }
    this.pos++;
    return items;
  }

  private parseLiteralValue(): LiteralValue {
    const tok = this.advance();
    if (tok === "[") {
      this.enter();
      try {
        return this.parseListBody();
      } finally {
        this.depth--;
      }
    }
    if (tok.length >= 2 && tok.startsWith("'") && tok.endsWith("'")) return tok.slice(1, -1);
    if (tok === "true") return true;
    if (tok === "false") return false;
    if (FULL_FLOAT.test(tok)) return parseFloat(tok);
    if (FULL_INT.test(tok)) return parseInt(tok, 10);
    throw new AminoError("syntax", `expected literal, got "${tok}"`);
  }
}

function isNumericBase(b: string): boolean {
  return b === "Int" || b === "Float";
}

function literalBase(v: LiteralValue): string {
  if (typeof v === "boolean") return "Bool";
  if (typeof v === "number") return Number.isInteger(v) ? "Int" : "Float";
  if (typeof v === "string") return "Str";
  return "List";
}

export function parseExpression(text: string, ctx: ParserContext): Node {
  if (text.length > ctx.maxLength) {
    throw new AminoError("syntax", `expression longer than ${ctx.maxLength} characters`);
  }
  const tokens = tokenize(text.trim(), ctx.ops.symbols());
  return new Parser(tokens, ctx).parse();
}
