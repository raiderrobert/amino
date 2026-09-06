/**
 * amino for TypeScript: parse, type-check, and evaluate user-written
 * conditions against a developer-defined schema.
 *
 * The primary use is validating an expression in the browser as the user
 * composes it, before it is sent to a backend that re-parses it. The
 * in-process evaluator is here too, so Node services can be a full host.
 */
export { loadSchema, Engine, Expression, CompiledRules } from "./engine.js";
export type { Options, Rule, MatchConfig, MatchResult } from "./engine.js";
export { AminoError, isAminoError } from "./errors.js";
export type { Code } from "./errors.js";
export { parseSchema, Schema } from "./schema.js";
export type { Field, StructDef, FunctionDef, Param, Kind } from "./schema.js";
export type { Node, Literal, Variable, Unary, Binary, Call, LiteralValue } from "./ast.js";
export type { OperatorDef, OperatorFn } from "./operators.js";
export type { TypeDef } from "./types.js";
export type { Func } from "./eval.js";
