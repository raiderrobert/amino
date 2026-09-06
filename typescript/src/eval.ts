import type { Node } from "./ast.js";
import { AminoError } from "./errors.js";
import { truthy } from "./values.js";

/** Implements a schema-declared function on the in-process target. */
export type Func = (...args: unknown[]) => unknown;

export type EvalFn = (record: Record<string, unknown>, fns: Record<string, Func>) => unknown;

/** Turns the typed AST into a closure. An error thrown during evaluation makes the rule false. */
export function compileNode(n: Node): EvalFn {
  switch (n.node) {
    case "literal": {
      const v = n.value;
      return () => v;
    }
    case "variable": {
      const parts = n.name.split(".");
      const name = n.name;
      return (record) => {
        let cur: unknown = record;
        for (const part of parts) {
          if (cur === null || typeof cur !== "object" || Array.isArray(cur) || !(part in (cur as object))) {
            throw new AminoError("evaluation", `field "${name}" not found`, name);
          }
          cur = (cur as Record<string, unknown>)[part];
        }
        return cur;
      };
    }
    case "unary": {
      const operand = compileNode(n.operand);
      if (n.op === "not") return (r, f) => !truthy(operand(r, f));
      const fn = n.def.fn;
      if (!fn) throw new AminoError("config", `operator "${n.op}" has no implementation`);
      return (r, f) => fn(operand(r, f));
    }
    case "binary": {
      const left = compileNode(n.left);
      const right = compileNode(n.right);
      if (n.op === "and") {
        return (r, f) => {
          let lv: unknown;
          try {
            lv = left(r, f);
          } catch {
            return false;
          }
          if (!truthy(lv)) return false;
          return truthy(right(r, f));
        };
      }
      if (n.op === "or") {
        return (r, f) => {
          try {
            if (truthy(left(r, f))) return true;
          } catch {
            // a failing left side is treated as false
          }
          try {
            return truthy(right(r, f));
          } catch {
            return false;
          }
        };
      }
      const fn = n.def.fn;
      if (!fn) throw new AminoError("config", `operator "${n.op}" has no implementation`);
      return (r, f) => fn(left(r, f), right(r, f));
    }
    case "call": {
      const args = n.args.map(compileNode);
      const name = n.name;
      return (r, f) => {
        const fn = f[name];
        if (!fn) throw new AminoError("evaluation", `function "${name}" has no implementation`);
        return fn(...args.map((a) => a(r, f)));
      };
    }
  }
}
