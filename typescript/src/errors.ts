/**
 * Every failure amino reports is an AminoError with a code. The parse-time
 * codes are the named validation rules from spec/conformance/README.md and
 * are the same in every host implementation.
 */
export type Code =
  | "syntax"
  | "unknown_field"
  | "unknown_function"
  | "unknown_operator"
  | "type_mismatch"
  | "depth_exceeded"
  | "schema_parse"
  | "schema_validation"
  | "decision_validation"
  | "evaluation"
  | "unsupported"
  | "operator_conflict"
  | "config";

export class AminoError extends Error {
  readonly code: Code;
  readonly field: string | undefined;

  constructor(code: Code, message: string, field?: string) {
    super(field === undefined ? `${code}: ${message}` : `${code}: ${message} (field "${field}")`);
    this.name = "AminoError";
    this.code = code;
    this.field = field;
  }
}

export function isAminoError(e: unknown): e is AminoError {
  return e instanceof AminoError;
}
