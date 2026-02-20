# Session Handoff: Amino Rewrite Design

**Date**: 2026-02-19
**Branch**: `docs/adr-engine-architecture`

## What We Did

Conducted a full brainstorming and design session for a ground-up rewrite of amino. Produced four ADRs, a design document, and a session handoff.

## Artifacts Produced

All committed to branch `docs/adr-engine-architecture`:

| File | Purpose |
|------|---------|
| `docs/adr/000-adr-template.md` | ADR template |
| `docs/adr/001-engine-architecture-and-lifecycle.md` | Schema fixed at startup, rules hot-swappable, atomic engine replacement, strict/loose modes (loose = skip-and-warn), multi-context is application-level |
| `docs/adr/002-dsl-interchange-format-and-multi-language.md` | DSL text as interchange format, Python as reference implementation, other SDKs are rule composers, schema introspection first-class |
| `docs/adr/003-extensibility-model.md` | Pratt parser, operator presets (standard/minimal), operator registration with type signatures + associativity, keyword vs function call disambiguation by syntax, custom types with validators, match modes (all/first/inverse/score), Bool→1/0 coercion in score mode |
| `docs/adr/004-schema-language-features.md` | Field constraints `{min: 18}`, optional fields `name: Str?`, struct-as-type references |
| `docs/plans/2026-02-19-rewrite-design.md` | **Full design document** — the main reference for implementation |

## Where We Stopped

The design document is complete and approved. The next step is:

1. **Pressure test the design with use cases** (user had a set of use cases ready)
2. **Write the implementation plan** (invoke `superpowers:writing-plans` skill)
3. **Execute the implementation** (the actual rewrite)

## Prompt to Resume

Use this prompt in a new session:

---

We are in the middle of designing a rewrite of the amino rules engine. The design is complete and approved. I have a set of use cases to pressure test the design before we write the implementation plan.

Please read these files to get up to speed:
- `docs/plans/2026-02-19-rewrite-design.md` (the main design document)
- `docs/adr/001-engine-architecture-and-lifecycle.md`
- `docs/adr/002-dsl-interchange-format-and-multi-language.md`
- `docs/adr/003-extensibility-model.md`
- `docs/adr/004-schema-language-features.md`

We are on branch `docs/adr-engine-architecture`.

Once you've read those, I'll walk you through use cases to pressure test the design. After that we need to write an implementation plan using the `superpowers:writing-plans` skill.

---

## Key Design Decisions Summary

- **Three data groups**: schema (fixed), rules (hot-swappable), decisions (always dynamic)
- **Engine is a single context**: multi-tenant is application-level (multiple engine instances)
- **Zero-downtime**: atomic engine replacement by the caller; amino makes engines safely replaceable
- **Type system**: schema types are enforced at rule compile time (TypedCompiler), decisions validated at eval time (DecisionValidator)
- **Strict/loose modes**: independent for rules and decisions; loose = skip-and-warn (no coercion)
- **Pratt parser**: dynamic operator table; `and`/`or`/`not` are irreducible minimum
- **Operator registration**: requires `input_types`, `return_type`, `binding_power`, `associativity`; must complete before first compile/eval
- **Custom types**: register with base type + validator; base type governs default operator behavior
- **Match modes**: all, first, inverse, score (Bool coerces to 1/0 in score mode)
- **Schema language**: constraints `{min: 18}`, optionals `name: Str?`, struct-as-type references
- **DSL is interchange format**: rules travel as text; Python is reference implementation
