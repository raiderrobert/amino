import type { Node } from "./ast.js";
import { AminoError } from "./errors.js";
import { compileNode, type EvalFn, type Func } from "./eval.js";
import { buildOperatorRegistry, type OperatorDef, type OperatorRegistry } from "./operators.js";
import { parseExpression } from "./parser.js";
import { parseSchema, type Schema } from "./schema.js";
import { TypeRegistry, type TypeDef } from "./types.js";
import { validateDecision, type DecisionsMode } from "./validator.js";
import { isNumber, truthy } from "./values.js";

export interface Options {
  /** Built-in operator preset, or an explicit list of built-in operator tokens. and, or, not are always enabled. */
  operators?: "standard" | "minimal" | string[];
  /** Custom operators. */
  customOperators?: OperatorDef[];
  /** Custom types, or overrides of built-in ones. */
  types?: TypeDef[];
  /** Implementations for schema-declared functions. */
  functions?: Record<string, Func>;
  /** "loose" (default) drops non-conforming record fields with a warning; "strict" throws. */
  decisionsMode?: DecisionsMode;
  /** Maximum expression nesting. Default 100. */
  maxDepth?: number;
  /** Maximum expression length in characters. Default 10000. */
  maxLength?: number;
}

/** One expression in a rule set for the in-process target. */
export interface Rule {
  id: string;
  expr: string;
  /** e.g. { ordering: 1 } for first-match mode */
  meta?: Record<string, unknown>;
}

export interface MatchConfig {
  mode?: "all" | "first" | "inverse" | "score";
  /** first: the meta key to order by */
  key?: string;
  /** first: "asc" (default) or "desc" */
  order?: "asc" | "desc";
  /** score: "sum" (the only aggregate) */
  aggregate?: "sum";
  /** score: when set and met, matched lists the truthy rules */
  threshold?: number;
}

export interface MatchResult {
  /** the record's "id" value, if any */
  id: unknown;
  matched: string[];
  excluded: string[];
  score: number | null;
  warnings: string[];
}

/** A parsed, type-checked expression ready for any target. */
export class Expression {
  constructor(
    readonly root: Node,
    readonly schema: Schema,
    private readonly typeRegistry: TypeRegistry,
  ) {}

  /** The root's type: "Bool" for a predicate. */
  get type(): string {
    return this.root.type;
  }

  /** Reduces a type name to its primitive: "email" -> "Str". */
  baseType(name: string): string {
    return this.typeRegistry.base(name);
  }
}

/**
 * Holds a validated schema plus the registered types, operators, and
 * functions an expression may use. Built once, immutable after.
 */
export class Engine {
  readonly schema: Schema;
  private readonly types: TypeRegistry;
  private readonly ops: OperatorRegistry;
  private readonly funcs: Record<string, Func>;
  private readonly decisionsMode: DecisionsMode;
  private readonly maxDepth: number;
  private readonly maxLength: number;

  constructor(schemaText: string, options: Options = {}) {
    this.types = new TypeRegistry();
    for (const t of options.types ?? []) this.types.register(t);
    this.ops = buildOperatorRegistry(options.operators);
    for (const d of options.customOperators ?? []) this.ops.register(d);
    this.funcs = { ...(options.functions ?? {}) };
    if (options.decisionsMode !== undefined && options.decisionsMode !== "strict" && options.decisionsMode !== "loose") {
      throw new AminoError("config", `decisions mode must be strict or loose, got "${String(options.decisionsMode)}"`);
    }
    this.decisionsMode = options.decisionsMode ?? "loose";
    this.maxDepth = options.maxDepth ?? 100;
    this.maxLength = options.maxLength ?? 10000;
    this.schema = parseSchema(schemaText);
    this.schema.validate(this.types.names());
  }

  exportSchema(): string {
    return this.schema.export();
  }

  private parseNode(text: string): Node {
    return parseExpression(text, {
      schema: this.schema,
      ops: this.ops,
      types: this.types,
      maxDepth: this.maxDepth,
      maxLength: this.maxLength,
    });
  }

  /** Parses and type-checks one expression. Throws AminoError. */
  parse(text: string): Expression {
    return new Expression(this.parseNode(text), this.schema, this.types);
  }

  /**
   * Validates without throwing: the way a browser composer checks input as
   * the user types. Returns the expression's type on success or the error.
   */
  validate(text: string): { ok: true; type: string } | { ok: false; error: AminoError } {
    try {
      return { ok: true, type: this.parse(text).type };
    } catch (e) {
      if (e instanceof AminoError) return { ok: false, error: e };
      throw e;
    }
  }

  /** Parses every rule and returns a reusable rule set. */
  compile(rules: Rule[], match: MatchConfig = {}): CompiledRules {
    const seen = new Set<string>();
    const compiled: CompiledRule[] = [];
    for (const r of rules) {
      if (seen.has(r.id)) throw new AminoError("config", `duplicate rule id "${r.id}"`);
      seen.add(r.id);
      compiled.push({ id: r.id, fn: compileNode(this.parseNode(r.expr)), meta: r.meta ?? {} });
    }
    return new CompiledRules(this, compiled, match);
  }

  /** Compiles and evaluates in one call. */
  eval(rules: Rule[], decision: Record<string, unknown>, match: MatchConfig = {}): MatchResult {
    return this.compile(rules, match).evalOne(decision);
  }

  /** @internal */
  _validate(decision: Record<string, unknown>) {
    return validateDecision(decision, this.schema, this.types, this.decisionsMode);
  }

  /** @internal */
  get _funcs(): Record<string, Func> {
    return this.funcs;
  }
}

interface CompiledRule {
  id: string;
  fn: EvalFn;
  meta: Record<string, unknown>;
}

/** A rule set compiled once for repeated evaluation. Immutable; to change rules, compile again. */
export class CompiledRules {
  constructor(
    private readonly engine: Engine,
    private readonly rules: CompiledRule[],
    private readonly cfg: MatchConfig,
  ) {}

  /** Evaluates against one record. Throws only for a strict-mode validation failure. */
  evalOne(decision: Record<string, unknown>): MatchResult {
    const { cleaned, warnings } = this.engine._validate(decision);
    const results = this.rules.map((r) => {
      let value: unknown;
      try {
        value = r.fn(cleaned, this.engine._funcs);
      } catch {
        value = false;
      }
      return { id: r.id, value, meta: r.meta };
    });
    return this.match(decision["id"], results, warnings);
  }

  eval(decisions: Record<string, unknown>[]): MatchResult[] {
    return decisions.map((d) => this.evalOne(d));
  }

  private match(id: unknown, results: { id: string; value: unknown; meta: Record<string, unknown> }[], warnings: string[]): MatchResult {
    const out: MatchResult = { id, matched: [], excluded: [], score: null, warnings };
    const mode = this.cfg.mode ?? "all";
    switch (mode) {
      case "all":
        out.matched = results.filter((r) => truthy(r.value)).map((r) => r.id);
        break;
      case "first": {
        const matched = results.filter((r) => truthy(r.value));
        if (matched.length === 0) break;
        const key = this.cfg.key;
        if (key !== undefined) {
          const desc = this.cfg.order === "desc";
          const keyOf = (r: { meta: Record<string, unknown> }): number => {
            const v = r.meta[key];
            return isNumber(v) ? v : Number.POSITIVE_INFINITY;
          };
          matched.sort((a, b) => (desc ? keyOf(b) - keyOf(a) : keyOf(a) - keyOf(b)));
        }
        out.matched = [(matched[0] as { id: string }).id];
        break;
      }
      case "inverse":
        out.excluded = results.filter((r) => !truthy(r.value)).map((r) => r.id);
        break;
      case "score": {
        let total = 0;
        for (const r of results) {
          if (typeof r.value === "boolean") total += r.value ? 1 : 0;
          else if (isNumber(r.value)) total += r.value;
        }
        out.score = total;
        if (this.cfg.threshold !== undefined && total >= this.cfg.threshold) {
          out.matched = results.filter((r) => truthy(r.value)).map((r) => r.id);
        }
        break;
      }
      default:
        throw new AminoError("config", `unknown match mode "${String(mode)}"`);
    }
    return out;
  }
}

/** Parses and validates schema text and builds an Engine. */
export function loadSchema(schemaText: string, options: Options = {}): Engine {
  return new Engine(schemaText, options);
}
