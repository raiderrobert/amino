package amino_test

import (
	"bytes"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"testing"

	amino "github.com/raiderrobert/amino/go"
)

// The corpus in ../spec/conformance is the specification. Cases whose xfail
// reason starts with "go:" are expected failures for this host; xfail reasons
// for other hosts are ignored and the case is required to pass here.

const corpusDir = "../spec/conformance"

type parseFile struct {
	Schema    string      `json:"schema"`
	Operators string      `json:"operators"`
	Cases     []parseCase `json:"cases"`
}

type parseCase struct {
	Name       string `json:"name"`
	Expression string `json:"expression"`
	Expect     string `json:"expect"`
	Type       string `json:"type"`
	Error      string `json:"error"`
	XFail      string `json:"xfail"`
}

type evalFile struct {
	Schema  string           `json:"schema"`
	Records []map[string]any `json:"records"`
	Cases   []evalCase       `json:"cases"`
}

type evalCase struct {
	Expression string  `json:"expression"`
	Matches    []int64 `json:"matches"`
	XFail      string  `json:"xfail"`
}

func xfailForGo(reason string) bool { return strings.HasPrefix(reason, "go:") }

func loadJSON(t *testing.T, path string, into any) {
	t.Helper()
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read %s: %v", path, err)
	}
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.UseNumber()
	if err := dec.Decode(into); err != nil {
		t.Fatalf("decode %s: %v", path, err)
	}
}

// normalize converts json.Number to int64 or float64, recursively, so records
// look the way application code would build them.
func normalize(v any) any {
	switch x := v.(type) {
	case json.Number:
		if i, err := x.Int64(); err == nil {
			return i
		}
		f, _ := x.Float64()
		return f
	case map[string]any:
		out := make(map[string]any, len(x))
		for k, e := range x {
			out[k] = normalize(e)
		}
		return out
	case []any:
		out := make([]any, len(x))
		for i, e := range x {
			out[i] = normalize(e)
		}
		return out
	}
	return v
}

func expandMacro(expr string) string {
	if strings.HasPrefix(expr, "@deep:") {
		n := 0
		for _, ch := range expr[len("@deep:"):] {
			n = n*10 + int(ch-'0')
		}
		return strings.Repeat("(", n) + "score > 1" + strings.Repeat(")", n)
	}
	return expr
}

func TestConformanceParse(t *testing.T) {
	files, _ := filepath.Glob(filepath.Join(corpusDir, "parse", "*.json"))
	if len(files) == 0 {
		t.Fatal("no parse corpus files found")
	}
	for _, path := range files {
		var f parseFile
		loadJSON(t, path, &f)
		var opts []amino.Option
		if f.Operators != "" {
			opts = append(opts, amino.WithOperators(f.Operators))
		}
		engine, err := amino.LoadSchema(f.Schema, opts...)
		if err != nil {
			t.Fatalf("%s: schema: %v", path, err)
		}
		for _, c := range f.Cases {
			c := c
			t.Run(filepath.Base(path)+"/"+c.Name, func(t *testing.T) {
				expr, err := engine.Parse(expandMacro(c.Expression))
				var failure string
				switch c.Expect {
				case "accept":
					if err != nil {
						failure = "expected accept, got " + err.Error()
					} else if expr.Type != c.Type {
						failure = "expected type " + c.Type + ", got " + expr.Type
					}
				case "reject":
					var ae *amino.Error
					if err == nil {
						failure = "expected reject with " + c.Error + ", got accept"
					} else if !errors.As(err, &ae) {
						failure = "expected *amino.Error, got " + err.Error()
					} else if string(ae.Code) != c.Error {
						failure = "expected code " + c.Error + ", got " + string(ae.Code)
					}
				default:
					t.Fatalf("bad expect %q", c.Expect)
				}
				if xfailForGo(c.XFail) {
					if failure == "" {
						t.Fatalf("marked xfail for go but passed; remove the marker: %s", c.XFail)
					}
					t.Skipf("expected failure: %s", c.XFail)
				}
				if failure != "" {
					t.Fatal(failure)
				}
			})
		}
	}
}

func TestConformanceEval(t *testing.T) {
	files, _ := filepath.Glob(filepath.Join(corpusDir, "eval", "*.json"))
	if len(files) == 0 {
		t.Fatal("no eval corpus files found")
	}
	for _, path := range files {
		var f evalFile
		loadJSON(t, path, &f)
		engine, err := amino.LoadSchema(f.Schema)
		if err != nil {
			t.Fatalf("%s: schema: %v", path, err)
		}
		records := make([]map[string]any, len(f.Records))
		for i, r := range f.Records {
			records[i] = normalize(r).(map[string]any)
		}
		for _, c := range f.Cases {
			c := c
			t.Run(filepath.Base(path)+"/"+c.Expression, func(t *testing.T) {
				var failure string
				compiled, err := engine.Compile([]amino.Rule{{ID: "q", Expr: c.Expression}}, nil)
				if err != nil {
					failure = "compile: " + err.Error()
				} else {
					results, err := compiled.Eval(records)
					if err != nil {
						failure = "eval: " + err.Error()
					} else {
						var got []int64
						for _, r := range results {
							if len(r.Matched) == 1 {
								got = append(got, r.ID.(int64))
							}
						}
						sort.Slice(got, func(i, j int) bool { return got[i] < got[j] })
						want := c.Matches
						if want == nil {
							want = []int64{}
						}
						if got == nil {
							got = []int64{}
						}
						if len(got) != len(want) {
							failure = "matches differ"
						} else {
							for i := range got {
								if got[i] != want[i] {
									failure = "matches differ"
								}
							}
						}
						if failure != "" {
							failure += ": want " + join(want) + ", got " + join(got)
						}
					}
				}
				if xfailForGo(c.XFail) {
					if failure == "" {
						t.Fatalf("marked xfail for go but passed; remove the marker: %s", c.XFail)
					}
					t.Skipf("expected failure: %s", c.XFail)
				}
				if failure != "" {
					t.Fatal(failure)
				}
			})
		}
	}
}

func join(ids []int64) string {
	parts := make([]string, len(ids))
	for i, id := range ids {
		parts[i] = jsonString(id)
	}
	return "[" + strings.Join(parts, ", ") + "]"
}

func jsonString(v any) string {
	b, _ := json.Marshal(v)
	return string(b)
}
