import { describe, expect, it } from "vitest";

import { AminoError, loadSchema } from "../src/index.js";

function code(fn: () => unknown): string {
  try {
    fn();
  } catch (e) {
    if (e instanceof AminoError) return e.code;
    throw e;
  }
  return "";
}

describe("schema", () => {
  it("parses, indexes, and exports", () => {
    const engine = loadSchema(`# comment
struct Address { street: Str, city: Str }
struct Customer {
    id: Str
    billing: Address
    shipping: Address?
}
amount: Int {min: 0, max: 100}
tags: List[Str|Int]
email: Str?
customer: Customer
score: (a: Int, b: Float?) -> Float
`);
    const s = engine.schema;
    expect(s.structs).toHaveLength(2);
    expect(s.fields).toHaveLength(4);
    expect(s.functions).toHaveLength(1);
    expect(s.lookup("customer.billing.city")?.typeName).toBe("Str");
    expect(s.lookup("tags")?.elementTypes).toEqual(["Str", "Int"]);
    expect(s.lookup("amount")?.constraints).toEqual({ min: 0, max: 100 });
    expect(engine.exportSchema()).toBe(
      [
        "struct Address {street: Str, city: Str}",
        "struct Customer {id: Str, billing: Address, shipping: Address?}",
        "amount: Int {max: 100, min: 0}",
        "tags: List[Str|Int]",
        "email: Str?",
        "customer: Customer",
        "score: (a: Int, b: Float?) -> Float",
      ].join("\n"),
    );
  });

  it("rejects bad schemas", () => {
    for (const src of ["a: Nope", "a: Int\na: Str", "struct A { b: B }\nstruct B { a: A }", "struct S { x: Int, x: Str }", "a Int", "struct: Int"]) {
      const c = code(() => loadSchema(src));
      expect(["schema_parse", "schema_validation"], src).toContain(c);
    }
  });
});

describe("evaluation", () => {
  const engine = loadSchema("amount: Int\nstate: Str");
  const rules = [
    { id: "1", expr: "amount > 0 and state = 'CA'", meta: { ordering: 3 } },
    { id: "2", expr: "amount > 10 and state = 'CA'", meta: { ordering: 2 } },
    { id: "3", expr: "amount >= 100", meta: { ordering: 1 } },
  ];
  const rec = { id: 45, amount: 100, state: "CA" };

  it("all", () => {
    const r = engine.eval(rules, rec);
    expect(r.matched).toEqual(["1", "2", "3"]);
    expect(r.id).toBe(45);
  });
  it("first by ordering", () => {
    expect(engine.eval(rules, rec, { mode: "first", key: "ordering", order: "asc" }).matched).toEqual(["3"]);
    expect(engine.eval(rules, rec, { mode: "first", key: "ordering", order: "desc" }).matched).toEqual(["1"]);
  });
  it("inverse", () => {
    expect(engine.eval(rules, { amount: 5, state: "NY" }, { mode: "inverse" }).excluded).toEqual(["1", "2", "3"]);
  });
  it("score", () => {
    const r = engine.eval([{ id: "a", expr: "amount" }, { id: "b", expr: "amount > 0" }], rec, { mode: "score", threshold: 50 });
    expect(r.score).toBe(101);
    expect(r.matched).toEqual(["a", "b"]);
  });
  it("missing field makes the rule false, or tolerates a failing left side", () => {
    const e = loadSchema("a: Int\nb: Int?");
    const r = e.eval([{ id: "r", expr: "not b = 1" }, { id: "s", expr: "b = 1 or a = 1" }], { a: 1 });
    expect(r.matched).toEqual(["s"]);
  });
});

describe("validation", () => {
  it("strict mode throws on type, constraint, and custom type failures", () => {
    const strict = loadSchema("n: Int {min: 0}\ncontact: email", { decisionsMode: "strict" });
    const rule = [{ id: "r", expr: "n > 1" }];
    expect(code(() => strict.eval(rule, { n: "x", contact: "a@b.co" }))).toBe("decision_validation");
    expect(code(() => strict.eval(rule, { n: -1, contact: "a@b.co" }))).toBe("decision_validation");
    expect(code(() => strict.eval(rule, { n: 2, contact: "nope" }))).toBe("decision_validation");
  });
  it("loose mode drops the field with a warning", () => {
    const loose = loadSchema("n: Int\ncontact: email");
    const r = loose.eval([{ id: "r", expr: "contact = 'nope'" }], { n: 2, contact: "nope" });
    expect(r.matched).toEqual([]);
    expect(r.warnings).toHaveLength(1);
  });
});

describe("extensibility", () => {
  it("functions and custom operators", () => {
    const engine = loadSchema("text: Str\ntoxicity: (t: Str) -> Float\na: Int\nb: Int", {
      functions: { toxicity: () => 0.9 },
      customOperators: [
        {
          keyword: "near",
          bindingPower: 40,
          inputTypes: ["Int", "Int"],
          returnType: "Bool",
          fn: (x, y) => Math.abs((x as number) - (y as number)) < 5,
        },
      ],
    });
    const r = engine.eval([{ id: "t", expr: "toxicity(text) > 0.5" }, { id: "n", expr: "a near b" }], { text: "hi", a: 3, b: 6 });
    expect(r.matched).toEqual(["t", "n"]);
    expect(code(() => engine.parse("toxicity(a) > 0.5"))).toBe("type_mismatch");
    expect(code(() => engine.parse("toxicity()"))).toBe("type_mismatch");
  });
  it("limits", () => {
    const engine = loadSchema("a: Int", { maxDepth: 3, maxLength: 20 });
    expect(code(() => engine.parse("(((a > 1)))"))).toBe("depth_exceeded");
    expect(code(() => engine.parse("a > 1 and a > 1 and a > 1"))).toBe("syntax");
  });
  it("operator conflict", () => {
    expect(code(() => loadSchema("a: Int", { customOperators: [{ symbol: "=", bindingPower: 40 }] }))).toBe("operator_conflict");
  });
  it("validate() never throws for bad input", () => {
    const engine = loadSchema("a: Int");
    const r = engine.validate("a >");
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.error.code).toBe("syntax");
    expect(engine.validate("a > 1")).toEqual({ ok: true, type: "Bool" });
  });
});
