import { AminoError } from "./errors.js";
import type { Field, Schema } from "./schema.js";
import type { TypeRegistry } from "./types.js";
import { equalValues, isNumber } from "./values.js";

export type DecisionsMode = "strict" | "loose";

export interface Validated {
  cleaned: Record<string, unknown>;
  warnings: string[];
}

/**
 * Checks a record against the schema. Loose mode drops non-conforming fields
 * with a warning; strict mode throws on the first problem.
 */
export function validateDecision(
  decision: Record<string, unknown>,
  schema: Schema,
  types: TypeRegistry,
  mode: DecisionsMode,
): Validated {
  const cleaned: Record<string, unknown> = {};
  const warnings: string[] = [];
  const fail = (f: Field, msg: string): void => {
    if (mode === "strict") throw new AminoError("decision_validation", msg, f.name);
    warnings.push(msg);
  };

  for (const f of schema.fields) {
    if (!(f.name in decision)) {
      if (!f.optional) fail(f, `required field "${f.name}" is missing`);
      continue;
    }
    const value = decision[f.name];
    if (value === null || value === undefined) {
      if (!f.optional) fail(f, `field "${f.name}" expected ${f.typeName}, got null`);
      continue;
    }
    if (!checkType(value, f, schema, types)) {
      fail(f, `field "${f.name}" expected ${f.typeName}, got ${typeof value}`);
      continue;
    }
    const violation = checkConstraints(value, f.constraints);
    if (violation) {
      fail(f, `field "${f.name}" constraint violation: ${violation}`);
      continue;
    }
    cleaned[f.name] = value;
  }
  for (const [k, v] of Object.entries(decision)) {
    if (!(k in cleaned) && schema.lookup(k) === undefined) cleaned[k] = v;
  }
  return { cleaned, warnings };
}

function checkType(value: unknown, f: Field, schema: Schema, types: TypeRegistry): boolean {
  switch (f.kind) {
    case "Int":
      return isNumber(value) && Number.isInteger(value);
    case "Float":
      return isNumber(value);
    case "Str":
      return typeof value === "string";
    case "Bool":
      return typeof value === "boolean";
    case "List":
      return Array.isArray(value);
    case "Custom": {
      if (schema.isStruct(f.typeName)) return typeof value === "object" && value !== null && !Array.isArray(value);
      const t = types.get(f.typeName);
      if (t) return checkBase(value, t.base) && types.validate(f.typeName, value);
      return true;
    }
  }
}

function checkBase(value: unknown, base: string): boolean {
  switch (base) {
    case "Int":
      return isNumber(value) && Number.isInteger(value);
    case "Float":
      return isNumber(value);
    case "Str":
      return typeof value === "string";
    case "Bool":
      return typeof value === "boolean";
  }
  return true;
}

function checkConstraints(value: unknown, constraints: Record<string, unknown>): string | undefined {
  const num = isNumber(value) ? value : undefined;
  const len = typeof value === "string" ? [...value].length : Array.isArray(value) ? value.length : undefined;
  const list = Array.isArray(value) ? value : undefined;
  for (const [key, cv] of Object.entries(constraints)) {
    const bound = isNumber(cv) ? cv : undefined;
    switch (key) {
      case "min":
        if (num !== undefined && bound !== undefined && num < bound) return `value ${num} below min ${bound}`;
        break;
      case "max":
        if (num !== undefined && bound !== undefined && num > bound) return `value ${num} above max ${bound}`;
        break;
      case "exclusiveMin":
        if (num !== undefined && bound !== undefined && num <= bound) return `value ${num} not above exclusiveMin ${bound}`;
        break;
      case "exclusiveMax":
        if (num !== undefined && bound !== undefined && num >= bound) return `value ${num} not below exclusiveMax ${bound}`;
        break;
      case "minLength":
        if (len !== undefined && bound !== undefined && len < bound) return `length ${len} below minLength ${bound}`;
        break;
      case "maxLength":
        if (len !== undefined && bound !== undefined && len > bound) return `length ${len} above maxLength ${bound}`;
        break;
      case "exactLength":
        if (len !== undefined && bound !== undefined && len !== bound) return `length must be ${bound}`;
        break;
      case "pattern":
        if (typeof cv === "string" && typeof value === "string") {
          let re: RegExp;
          try {
            re = new RegExp(`^(?:${cv})$`);
          } catch {
            return `value does not match pattern "${cv}"`;
          }
          if (!re.test(value)) return `value does not match pattern "${cv}"`;
        }
        break;
      case "oneOf":
        if (Array.isArray(cv) && !cv.some((o) => safeEqual(value, o))) return `value ${String(value)} not in ${JSON.stringify(cv)}`;
        break;
      case "const":
        if (!safeEqual(value, cv)) return `value must equal ${JSON.stringify(cv)}`;
        break;
      case "minItems":
        if (list !== undefined && bound !== undefined && list.length < bound) return `list length ${list.length} below minItems ${bound}`;
        break;
      case "maxItems":
        if (list !== undefined && bound !== undefined && list.length > bound) return `list length ${list.length} above maxItems ${bound}`;
        break;
      case "unique":
        if (cv === true && list !== undefined) {
          const seen = new Set(list.map((x) => `${typeof x}:${JSON.stringify(x)}`));
          if (seen.size !== list.length) return "list elements must be unique";
        }
        break;
      default:
        break;
    }
  }
  return undefined;
}

function safeEqual(a: unknown, b: unknown): boolean {
  try {
    return equalValues(a, b);
  } catch {
    return false;
  }
}
