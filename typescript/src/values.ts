import { AminoError } from "./errors.js";

export function isNumber(v: unknown): v is number {
  return typeof v === "number" && !Number.isNaN(v);
}

/** "=" with the cross-type rules the language can produce; anything else is an evaluation error. */
export function equalValues(a: unknown, b: unknown): boolean {
  if (isNumber(a) && isNumber(b)) return a === b;
  if (typeof a === "string") return typeof b === "string" && a === b;
  if (typeof a === "boolean") return typeof b === "boolean" && a === b;
  if (Array.isArray(a)) {
    if (!Array.isArray(b) || a.length !== b.length) return false;
    return a.every((x, i) => {
      try {
        return equalValues(x, b[i]);
      } catch {
        return false;
      }
    });
  }
  if (a === null || a === undefined) return b === null || b === undefined;
  throw new AminoError("evaluation", `cannot compare ${typeof a} with ${typeof b}`);
}

/** Orders two numbers or two strings. */
export function compareValues(a: unknown, b: unknown): number {
  if (isNumber(a) && isNumber(b)) return a < b ? -1 : a > b ? 1 : 0;
  if (typeof a === "string" && typeof b === "string") return a < b ? -1 : a > b ? 1 : 0;
  throw new AminoError("evaluation", `cannot order ${typeof a} and ${typeof b}`);
}

export function inList(v: unknown, list: unknown): boolean {
  if (!Array.isArray(list)) throw new AminoError("evaluation", "right side of 'in' is not a list");
  return list.some((item) => {
    try {
      return equalValues(v, item);
    } catch {
      return false;
    }
  });
}

/** Python truthiness for the values the evaluator can see. */
export function truthy(v: unknown): boolean {
  if (v === null || v === undefined) return false;
  if (typeof v === "boolean") return v;
  if (typeof v === "number") return v !== 0;
  if (typeof v === "string") return v !== "";
  if (Array.isArray(v)) return v.length > 0;
  if (typeof v === "object") return Object.keys(v as object).length > 0;
  return true;
}
