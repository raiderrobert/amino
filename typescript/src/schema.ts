import { AminoError } from "./errors.js";

export type Kind = "Int" | "Float" | "Str" | "Bool" | "List" | "Custom";

export interface Field {
  name: string;
  kind: Kind;
  /** "Int", "List[Str]", "Address", "email" */
  typeName: string;
  elementTypes: string[];
  constraints: Record<string, unknown>;
  optional: boolean;
}

export interface StructDef {
  name: string;
  fields: Field[];
}

export interface Param {
  name: string;
  typeName: string;
  optional: boolean;
}

export interface FunctionDef {
  name: string;
  params: Param[];
  returnType: string;
}

const PRIMITIVES: Record<string, Kind> = { Int: "Int", Float: "Float", Str: "Str", Bool: "Bool" };
const RESERVED = new Set(["struct", "List"]);
const IDENT = /^[a-zA-Z_][a-zA-Z0-9_]*/;
const FLOAT = /^-?\d+\.\d+/;
const INT = /^-?\d+/;
const BOOL = /^(true|false)/;
const STRUCT_KW = /^struct(?![a-zA-Z0-9_])/;

/** A parsed and validated .amn document. */
export class Schema {
  readonly fields: Field[] = [];
  readonly structs: StructDef[] = [];
  readonly functions: FunctionDef[] = [];

  private structMap = new Map<string, StructDef>();
  private paths = new Map<string, Field>();
  private funcMap = new Map<string, FunctionDef>();

  /** Field at a dotted path, or undefined. */
  lookup(path: string): Field | undefined {
    return this.paths.get(path);
  }

  lookupFunction(name: string): FunctionDef | undefined {
    return this.funcMap.get(name);
  }

  isStruct(name: string): boolean {
    return this.structMap.has(name);
  }

  /** Checks references, duplicates, and cycles, then builds lookup indexes. */
  validate(customTypes: Set<string>): void {
    this.structMap = new Map(this.structs.map((s) => [s.name, s]));
    const known = new Set(["Int", "Float", "Str", "Bool", "List", ...this.structMap.keys(), ...customTypes]);

    const seen = new Set<string>();
    for (const item of [...this.fields, ...this.structs, ...this.functions]) {
      if (seen.has(item.name)) throw new AminoError("schema_validation", `duplicate name "${item.name}"`);
      seen.add(item.name);
    }
    for (const f of this.fields) {
      if (f.kind === "Custom" && !known.has(f.typeName)) {
        throw new AminoError("schema_validation", `unknown type "${f.typeName}"`, f.name);
      }
    }
    for (const s of this.structs) {
      const fieldSeen = new Set<string>();
      for (const f of s.fields) {
        if (fieldSeen.has(f.name)) {
          throw new AminoError("schema_validation", `duplicate field "${f.name}" in struct "${s.name}"`);
        }
        fieldSeen.add(f.name);
        if (f.kind === "Custom" && !known.has(f.typeName)) {
          throw new AminoError("schema_validation", `unknown type "${f.typeName}" in struct "${s.name}"`);
        }
      }
    }

    const dfs = (name: string, visiting: Set<string>): void => {
      if (visiting.has(name)) throw new AminoError("schema_validation", `circular struct reference involving "${name}"`);
      const s = this.structMap.get(name);
      if (!s) return;
      const next = new Set(visiting).add(name);
      for (const f of s.fields) {
        if (f.kind === "Custom" && this.structMap.has(f.typeName)) dfs(f.typeName, next);
      }
    };
    for (const name of [...this.structMap.keys()].sort()) dfs(name, new Set());

    this.paths = new Map();
    for (const f of this.fields) {
      this.paths.set(f.name, f);
      if (this.structMap.has(f.typeName)) this.indexStruct(f.name, f.typeName);
    }
    this.funcMap = new Map(this.functions.map((fn) => [fn.name, fn]));
  }

  private indexStruct(prefix: string, structName: string): void {
    const s = this.structMap.get(structName);
    if (!s) return;
    for (const f of s.fields) {
      const key = `${prefix}.${f.name}`;
      this.paths.set(key, f);
      if (this.structMap.has(f.typeName)) this.indexStruct(key, f.typeName);
    }
  }

  /** Renders the schema as .amn text: structs, then fields, then functions. */
  export(): string {
    const fieldStr = (f: Field): string => {
      const q = f.optional ? "?" : "";
      const keys = Object.keys(f.constraints).sort();
      const c = keys.length ? ` {${keys.map((k) => `${k}: ${exportValue(f.constraints[k])}`).join(", ")}}` : "";
      return `${f.name}: ${f.typeName}${q}${c}`;
    };
    const lines: string[] = [];
    for (const s of this.structs) lines.push(`struct ${s.name} {${s.fields.map(fieldStr).join(", ")}}`);
    for (const f of this.fields) lines.push(fieldStr(f));
    for (const fn of this.functions) {
      const params = fn.params.map((p) => `${p.name}: ${p.typeName}${p.optional ? "?" : ""}`).join(", ");
      lines.push(`${fn.name}: (${params}) -> ${fn.returnType}`);
    }
    return lines.join("\n");
  }
}

function exportValue(v: unknown): string {
  if (typeof v === "string") return `'${v}'`;
  if (Array.isArray(v)) return `[${v.map(exportValue).join(", ")}]`;
  return String(v);
}

class SchemaParser {
  private pos = 0;
  private line = 1;

  constructor(private readonly text: string) {}

  private peek(): string | undefined {
    return this.text[this.pos];
  }

  private advance(): string {
    const ch = this.text[this.pos] as string;
    if (ch === "\n") this.line++;
    this.pos++;
    return ch;
  }

  private skipWS(newlines: boolean): void {
    while (this.pos < this.text.length) {
      const ch = this.text[this.pos];
      if (ch === "#") {
        while (this.pos < this.text.length && this.text[this.pos] !== "\n") this.pos++;
      } else if (ch === " " || ch === "\t") {
        this.pos++;
      } else if (newlines && (ch === "\n" || ch === "\r")) {
        if (ch === "\n") this.line++;
        this.pos++;
      } else {
        return;
      }
    }
  }

  private skipH(): void {
    while (this.text[this.pos] === " " || this.text[this.pos] === "\t") this.pos++;
  }

  private readIdent(): string {
    const m = IDENT.exec(this.text.slice(this.pos));
    if (!m) throw new AminoError("schema_parse", `expected identifier at line ${this.line}`);
    this.pos += m[0].length;
    return m[0];
  }

  private expect(ch: string): void {
    this.skipH();
    if (this.peek() !== ch) {
      throw new AminoError("schema_parse", `expected "${ch}" at line ${this.line}`);
    }
    this.advance();
  }

  private parseStrLiteral(): string {
    this.advance();
    const start = this.pos;
    while (this.peek() !== undefined && this.peek() !== "'") this.advance();
    if (this.peek() !== "'") throw new AminoError("schema_parse", `unterminated string at line ${this.line}`);
    const s = this.text.slice(start, this.pos);
    this.advance();
    return s;
  }

  private parseListLit(): unknown[] {
    this.advance();
    const items: unknown[] = [];
    this.skipH();
    while (this.peek() !== undefined && this.peek() !== "]") {
      items.push(this.parseConstraintVal());
      this.skipH();
      if (this.peek() === ",") {
        this.advance();
        this.skipH();
      }
    }
    if (this.peek() !== "]") throw new AminoError("schema_parse", `unterminated list at line ${this.line}`);
    this.advance();
    return items;
  }

  private parseConstraintVal(): unknown {
    this.skipH();
    const ch = this.peek();
    if (ch === "'") return this.parseStrLiteral();
    if (ch === "[") return this.parseListLit();
    const rest = this.text.slice(this.pos);
    let m = FLOAT.exec(rest);
    if (m) {
      this.pos += m[0].length;
      return parseFloat(m[0]);
    }
    m = INT.exec(rest);
    if (m) {
      this.pos += m[0].length;
      return parseInt(m[0], 10);
    }
    m = BOOL.exec(rest);
    if (m) {
      this.pos += m[0].length;
      return m[0] === "true";
    }
    throw new AminoError("schema_parse", `expected constraint value at line ${this.line}`);
  }

  private parseConstraints(): Record<string, unknown> {
    this.advance();
    const out: Record<string, unknown> = {};
    this.skipH();
    while (this.peek() !== "}") {
      if (this.peek() === undefined) throw new AminoError("schema_parse", `unterminated constraint block at line ${this.line}`);
      const key = this.readIdent();
      this.expect(":");
      out[key] = this.parseConstraintVal();
      this.skipH();
      if (this.peek() === ",") {
        this.advance();
        this.skipH();
      }
    }
    this.advance();
    return out;
  }

  private parseTypeExpr(): { kind: Kind; typeName: string; elementTypes: string[] } {
    this.skipH();
    const name = this.readIdent();
    if (name === "List") {
      this.expect("[");
      const elems = [this.readIdent()];
      while (this.peek() === "|") {
        this.advance();
        elems.push(this.readIdent());
      }
      this.expect("]");
      return { kind: "List", typeName: `List[${elems.join("|")}]`, elementTypes: elems };
    }
    const prim = PRIMITIVES[name];
    if (prim) return { kind: prim, typeName: name, elementTypes: [] };
    return { kind: "Custom", typeName: name, elementTypes: [] };
  }

  private parseField(): Field {
    this.skipH();
    const name = this.readIdent();
    if (RESERVED.has(name)) throw new AminoError("schema_parse", `reserved word "${name}" used as field name at line ${this.line}`);
    this.expect(":");
    const t = this.parseTypeExpr();
    const f: Field = { name, ...t, constraints: {}, optional: false };
    this.skipH();
    if (this.peek() === "?") {
      f.optional = true;
      this.advance();
    }
    this.skipH();
    if (this.peek() === "{") f.constraints = this.parseConstraints();
    return f;
  }

  private parseStruct(): StructDef {
    this.readIdent();
    this.skipH();
    const name = this.readIdent();
    this.skipWS(true);
    this.expect("{");
    const fields: Field[] = [];
    for (;;) {
      this.skipWS(true);
      if (this.peek() === undefined) throw new AminoError("schema_parse", `unterminated struct "${name}"`);
      if (this.peek() === "}") break;
      fields.push(this.parseField());
      this.skipH();
      if (this.peek() === ",") this.advance();
    }
    this.advance();
    return { name, fields };
  }

  private isFunction(): boolean {
    const saved = { pos: this.pos, line: this.line };
    try {
      this.readIdent();
      this.skipH();
      if (this.peek() !== ":") return false;
      this.advance();
      this.skipH();
      return this.peek() === "(";
    } catch {
      return false;
    } finally {
      this.pos = saved.pos;
      this.line = saved.line;
    }
  }

  private parseFunction(): FunctionDef {
    const name = this.readIdent();
    this.expect(":");
    this.expect("(");
    const params: Param[] = [];
    this.skipH();
    while (this.peek() !== ")") {
      if (this.peek() === undefined) throw new AminoError("schema_parse", `unterminated parameter list at line ${this.line}`);
      const pname = this.readIdent();
      this.expect(":");
      const { typeName } = this.parseTypeExpr();
      const param: Param = { name: pname, typeName, optional: false };
      this.skipH();
      if (this.peek() === "?") {
        param.optional = true;
        this.advance();
      }
      params.push(param);
      this.skipH();
      if (this.peek() === ",") {
        this.advance();
        this.skipH();
      }
    }
    this.advance();
    this.skipH();
    if (!this.text.startsWith("->", this.pos)) throw new AminoError("schema_parse", `expected "->" at line ${this.line}`);
    this.pos += 2;
    this.skipH();
    const returnType = this.readIdent();
    this.skipH();
    if (this.peek() === "?") this.advance();
    return { name, params, returnType };
  }

  parse(): Schema {
    const schema = new Schema();
    for (;;) {
      this.skipWS(true);
      if (this.pos >= this.text.length) break;
      if (STRUCT_KW.test(this.text.slice(this.pos))) schema.structs.push(this.parseStruct());
      else if (this.isFunction()) schema.functions.push(this.parseFunction());
      else schema.fields.push(this.parseField());
    }
    return schema;
  }
}

/** Parses .amn text. Validation happens in loadSchema, which knows the custom types. */
export function parseSchema(text: string): Schema {
  return new SchemaParser(text).parse();
}
