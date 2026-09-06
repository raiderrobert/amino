import { AminoError } from "./errors.js";
import { compareValues, equalValues, inList } from "./values.js";

/** Implements an operator on the in-process target. Prefix operators get one argument, infix two. */
export type OperatorFn = (...args: unknown[]) => unknown;

/**
 * Registers an operator with the parser. Exactly one of symbol or keyword is
 * set. inputTypes and returnType drive type checking; "*" accepts anything.
 * fn may be omitted for and/or/not, which the evaluator implements itself.
 */
export interface OperatorDef {
  symbol?: string;
  keyword?: string;
  kind?: "infix" | "prefix";
  fn?: OperatorFn;
  bindingPower: number;
  associativity?: "left" | "right";
  inputTypes?: string[];
  returnType?: string;
}

/** A fully defaulted operator as stored in the registry. */
export interface ResolvedOperator {
  token: string;
  kind: "infix" | "prefix";
  fn: OperatorFn | undefined;
  bindingPower: number;
  associativity: "left" | "right";
  inputTypes: string[];
  returnType: string;
  isSymbol: boolean;
}

export class OperatorRegistry {
  private readonly byToken = new Map<string, ResolvedOperator[]>();

  register(def: OperatorDef): void {
    const hasSymbol = def.symbol !== undefined && def.symbol !== "";
    const hasKeyword = def.keyword !== undefined && def.keyword !== "";
    if (hasSymbol === hasKeyword) throw new AminoError("config", "operator needs exactly one of symbol or keyword");
    const kind = def.kind ?? "infix";
    const op: ResolvedOperator = {
      token: (hasSymbol ? def.symbol : def.keyword) as string,
      kind,
      fn: def.fn,
      bindingPower: def.bindingPower,
      associativity: def.associativity ?? "left",
      inputTypes: def.inputTypes ?? (kind === "prefix" ? ["*"] : ["*", "*"]),
      returnType: def.returnType ?? "Bool",
      isSymbol: hasSymbol,
    };
    const existing = this.byToken.get(op.token) ?? [];
    for (const e of existing) {
      if (e.inputTypes.length === op.inputTypes.length && e.inputTypes.every((t, i) => t === op.inputTypes[i])) {
        throw new AminoError("operator_conflict", `operator "${op.token}" with input types [${op.inputTypes.join(", ")}] already registered`);
      }
    }
    existing.push(op);
    this.byToken.set(op.token, existing);
  }

  candidates(token: string): ResolvedOperator[] {
    return this.byToken.get(token) ?? [];
  }

  bindingPower(token: string): number | undefined {
    return this.byToken.get(token)?.[0]?.bindingPower;
  }

  prefix(token: string): ResolvedOperator | undefined {
    return this.byToken.get(token)?.find((d) => d.kind === "prefix");
  }

  /** Symbol tokens, longest first, for the tokenizer. */
  symbols(): string[] {
    const out: string[] = [];
    for (const [tok, defs] of this.byToken) if (defs[0]?.isSymbol) out.push(tok);
    return out.sort((a, b) => b.length - a.length);
  }
}

export const ALWAYS = new Set(["or", "and", "not"]);

export function standardOperators(): OperatorDef[] {
  const cmp =
    (f: (c: number) => boolean): OperatorFn =>
    (a, b) =>
      f(compareValues(a, b));
  return [
    { keyword: "or", bindingPower: 10, inputTypes: ["Bool", "Bool"] },
    { keyword: "and", bindingPower: 20, inputTypes: ["Bool", "Bool"] },
    { keyword: "not", kind: "prefix", bindingPower: 30, inputTypes: ["Bool"] },
    { keyword: "in", bindingPower: 40, inputTypes: ["*", "List"], fn: (a, b) => inList(a, b) },
    { keyword: "not in", bindingPower: 40, inputTypes: ["*", "List"], fn: (a, b) => !inList(a, b) },
    { symbol: "=", bindingPower: 40, fn: (a, b) => equalValues(a, b) },
    { symbol: "!=", bindingPower: 40, fn: (a, b) => !equalValues(a, b) },
    { symbol: ">", bindingPower: 40, fn: cmp((c) => c > 0) },
    { symbol: "<", bindingPower: 40, fn: cmp((c) => c < 0) },
    { symbol: ">=", bindingPower: 40, fn: cmp((c) => c >= 0) },
    { symbol: "<=", bindingPower: 40, fn: cmp((c) => c <= 0) },
    {
      keyword: "contains",
      bindingPower: 40,
      inputTypes: ["Str", "Str"],
      fn: (a, b) => {
        if (typeof a !== "string" || typeof b !== "string") throw new AminoError("evaluation", "contains needs two strings");
        return a.includes(b);
      },
    },
  ];
}

export function builtinTokens(): Set<string> {
  return new Set(standardOperators().map((d) => (d.symbol ?? d.keyword) as string));
}

export function buildOperatorRegistry(preset: "standard" | "minimal" | string[] | undefined): OperatorRegistry {
  const all = standardOperators();
  let chosen: OperatorDef[];
  if (Array.isArray(preset)) {
    const enabled = new Set(preset);
    chosen = all.filter((d) => enabled.has((d.symbol ?? d.keyword) as string) || ALWAYS.has(d.keyword ?? ""));
  } else if (preset === undefined || preset === "standard") {
    chosen = all;
  } else if (preset === "minimal") {
    chosen = all.filter((d) => ALWAYS.has(d.keyword ?? ""));
  } else {
    throw new AminoError("config", `unknown operator preset "${String(preset)}"`);
  }
  const r = new OperatorRegistry();
  for (const d of chosen) r.register(d);
  return r;
}
