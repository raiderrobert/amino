package amino

import "fmt"

// Code identifies why amino rejected something. The parse-time codes are the
// named validation rules from spec/conformance/README.md and are the same in
// every host implementation.
type Code string

const (
	// Parse-time codes, shared across hosts.
	CodeSyntax          Code = "syntax"
	CodeUnknownField    Code = "unknown_field"
	CodeUnknownFunction Code = "unknown_function"
	CodeUnknownOperator Code = "unknown_operator"
	CodeTypeMismatch    Code = "type_mismatch"
	CodeDepthExceeded   Code = "depth_exceeded"

	// Other codes.
	CodeSchemaParse        Code = "schema_parse"
	CodeSchemaValidation   Code = "schema_validation"
	CodeDecisionValidation Code = "decision_validation"
	CodeEvaluation         Code = "evaluation"
	CodeUnsupported        Code = "unsupported"
	CodeOperatorConflict   Code = "operator_conflict"
	CodeConfig             Code = "config"
)

// Error is the only error type amino returns. Use errors.As to inspect Code.
type Error struct {
	Code    Code
	Message string
	Field   string // the schema field involved, when there is one
}

func (e *Error) Error() string {
	if e.Field != "" {
		return fmt.Sprintf("%s: %s (field %q)", e.Code, e.Message, e.Field)
	}
	return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

func newError(code Code, format string, args ...any) *Error {
	return &Error{Code: code, Message: fmt.Sprintf(format, args...)}
}

func fieldError(code Code, field, format string, args ...any) *Error {
	return &Error{Code: code, Message: fmt.Sprintf(format, args...), Field: field}
}
