import { AminoError } from "./errors.js";

/** A custom type: a name usable in schemas, the primitive it is stored as, and a validator. */
export interface TypeDef {
  name: string;
  base: "Str" | "Int" | "Float" | "Bool";
  validator: (value: unknown) => boolean;
}

export class TypeRegistry {
  private readonly types = new Map<string, TypeDef>();

  constructor() {
    for (const t of builtinTypes()) this.types.set(t.name, t);
  }

  register(t: TypeDef): void {
    if (!["Str", "Int", "Float", "Bool"].includes(t.base)) {
      throw new AminoError("schema_validation", `base type must be Str, Int, Float, or Bool, got "${t.base}"`);
    }
    this.types.set(t.name, t);
  }

  names(): Set<string> {
    return new Set(this.types.keys());
  }

  get(name: string): TypeDef | undefined {
    return this.types.get(name);
  }

  /** Reduces a type name to its primitive; primitives, List, and unknown names return themselves. */
  base(name: string): string {
    return this.types.get(name)?.base ?? name;
  }

  validate(name: string, value: unknown): boolean {
    const t = this.types.get(name);
    if (!t) return false;
    try {
      return Boolean(t.validator(value));
    } catch {
      return false;
    }
  }
}

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const IPV6 = /^[0-9a-f:]+(?:%[0-9a-z]+)?$/i;

function isIPv4(s: string): boolean {
  const parts = s.split(".");
  if (parts.length !== 4) return false;
  return parts.every((p) => /^\d+$/.test(p) && Number(p) >= 0 && Number(p) <= 255);
}

function isIPv6(s: string): boolean {
  if (!IPV6.test(s) || !s.includes(":")) return false;
  const halves = s.split("::");
  if (halves.length > 2) return false;
  const groups = s.replace(/%.*$/, "").split(/::?/).filter((g) => g.length > 0);
  if (groups.some((g) => g.length > 4)) return false;
  return halves.length === 2 ? groups.length <= 7 : groups.length === 8;
}

function isCIDR(s: string): boolean {
  const [addr, bits, ...rest] = s.split("/");
  if (rest.length || addr === undefined || bits === undefined || !/^\d+$/.test(bits)) return false;
  const n = Number(bits);
  if (isIPv4(addr)) return n >= 0 && n <= 32;
  if (isIPv6(addr)) return n >= 0 && n <= 128;
  return false;
}

function str(f: (s: string) => boolean): (v: unknown) => boolean {
  return (v) => typeof v === "string" && f(v);
}

function builtinTypes(): TypeDef[] {
  return [
    { name: "ipv4", base: "Str", validator: str(isIPv4) },
    { name: "ipv6", base: "Str", validator: str(isIPv6) },
    { name: "cidr", base: "Str", validator: str(isCIDR) },
    { name: "email", base: "Str", validator: str((s) => EMAIL.test(s)) },
    { name: "uuid", base: "Str", validator: str((s) => UUID.test(s)) },
  ];
}
