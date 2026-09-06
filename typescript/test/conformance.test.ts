/**
 * Runs ../spec/conformance against this implementation. Cases whose xfail
 * reason starts with "typescript:" are expected failures here; other hosts'
 * reasons are ignored and the case must pass.
 */
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { isAminoError, loadSchema, type Options } from "../src/index.js";

const CORPUS = join(__dirname, "..", "..", "spec", "conformance");

interface ParseCase {
  name: string;
  expression: string;
  expect: "accept" | "reject";
  type?: string;
  error?: string;
  xfail?: string;
}
interface ParseFile {
  schema: string;
  operators?: "standard" | "minimal";
  cases: ParseCase[];
}
interface EvalCase {
  expression: string;
  matches: number[];
  xfail?: string;
}
interface EvalFile {
  schema: string;
  records: Record<string, unknown>[];
  cases: EvalCase[];
}

function files(kind: string): string[] {
  const dir = join(CORPUS, kind);
  return readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .sort()
    .map((f) => join(dir, f));
}

function load<T>(path: string): T {
  return JSON.parse(readFileSync(path, "utf8")) as T;
}

function expandMacro(expr: string): string {
  if (expr.startsWith("@deep:")) {
    const n = Number(expr.slice("@deep:".length));
    return "(".repeat(n) + "score > 1" + ")".repeat(n);
  }
  return expr;
}

const ours = (reason: string | undefined): boolean => reason?.startsWith("typescript:") ?? false;

/** Runs a check; under an xfail for this host, a pass is an error and a failure is expected. */
function guarded(xfail: string | undefined, check: () => void): void {
  if (!ours(xfail)) {
    check();
    return;
  }
  let failed = false;
  try {
    check();
  } catch {
    failed = true;
  }
  if (!failed) throw new Error(`marked xfail for typescript but passed; remove the marker: ${xfail}`);
}

describe("conformance: parse", () => {
  const paths = files("parse");
  expect(paths.length).toBeGreaterThan(0);
  for (const path of paths) {
    const f = load<ParseFile>(path);
    const options: Options = f.operators ? { operators: f.operators } : {};
    const engine = loadSchema(f.schema, options);
    describe(path.split("/").pop() as string, () => {
      for (const c of f.cases) {
        it(c.name, () => {
          guarded(c.xfail, () => {
            const result = engine.validate(expandMacro(c.expression));
            if (c.expect === "accept") {
              if (!result.ok) throw new Error(`expected accept, got ${result.error.message}`);
              expect(result.type).toBe(c.type);
            } else {
              if (result.ok) throw new Error(`expected reject with ${c.error}, got accept`);
              expect(isAminoError(result.error)).toBe(true);
              expect(result.error.code).toBe(c.error);
            }
          });
        });
      }
    });
  }
});

describe("conformance: eval", () => {
  const paths = files("eval");
  expect(paths.length).toBeGreaterThan(0);
  for (const path of paths) {
    const f = load<EvalFile>(path);
    const engine = loadSchema(f.schema);
    describe(path.split("/").pop() as string, () => {
      for (const c of f.cases) {
        it(c.expression, () => {
          guarded(c.xfail, () => {
            const compiled = engine.compile([{ id: "q", expr: c.expression }]);
            const got = compiled
              .eval(f.records)
              .filter((r) => r.matched.length === 1)
              .map((r) => r.id as number)
              .sort((a, b) => a - b);
            expect(got).toEqual(c.matches);
          });
        });
      }
    });
  }
});
