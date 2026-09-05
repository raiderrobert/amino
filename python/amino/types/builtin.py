"""Built-in type definitions."""

import re

from .registry import TypeRegistry


def _is_ipv4(v: object) -> bool:
    if not isinstance(v, str):
        return False
    parts = v.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


def _is_ipv6(v: object) -> bool:
    if not isinstance(v, str):
        return False
    try:
        import ipaddress
        ipaddress.IPv6Address(v)
        return True
    except ValueError:
        return False


def _is_cidr(v: object) -> bool:
    if not isinstance(v, str) or "/" not in v:
        return False
    try:
        import ipaddress
        ipaddress.ip_network(v, strict=False)
        return True
    except ValueError:
        return False


def _is_email(v: object) -> bool:
    if not isinstance(v, str):
        return False
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v))


def _is_uuid(v: object) -> bool:
    if not isinstance(v, str):
        return False
    return bool(re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        v, re.IGNORECASE,
    ))


def register_builtin_types(registry: TypeRegistry) -> None:
    registry.register_type("ipv4", base="Str", validator=_is_ipv4)
    registry.register_type("ipv6", base="Str", validator=_is_ipv6)
    registry.register_type("cidr", base="Str", validator=_is_cidr)
    registry.register_type("email", base="Str", validator=_is_email)
    registry.register_type("uuid", base="Str", validator=_is_uuid)
