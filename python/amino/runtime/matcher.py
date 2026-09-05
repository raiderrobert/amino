"""Pattern matching and result handling."""

import dataclasses
from typing import Any


@dataclasses.dataclass
class MatchResult:
    id: Any
    matched: list[str] = dataclasses.field(default_factory=list)
    excluded: list[str] = dataclasses.field(default_factory=list)
    score: float | None = None
    warnings: list[str] = dataclasses.field(default_factory=list)


class Matcher:
    def __init__(self, config: dict[str, Any] | None = None):
        cfg = config or {}
        self._mode = cfg.get("mode", "all")
        self._key = cfg.get("key")
        self._order = cfg.get("order", "asc")
        self._aggregate = cfg.get("aggregate", "sum")
        self._threshold = cfg.get("threshold")

    def process(
        self,
        decision_id: Any,
        rule_results: list[tuple[Any, Any]],
        metadata: dict[Any, dict],
        warnings: list[str],
    ) -> MatchResult:
        if self._mode == "all":
            matched = [rid for rid, val in rule_results if val]
            return MatchResult(id=decision_id, matched=matched, warnings=list(warnings))

        if self._mode == "first":
            matched = [rid for rid, val in rule_results if val]
            if not matched:
                return MatchResult(id=decision_id, matched=[], warnings=list(warnings))
            if self._key:
                matched = sorted(
                    matched,
                    key=lambda rid: metadata.get(rid, {}).get(self._key, float("inf")),
                    reverse=(self._order == "desc"),
                )
            return MatchResult(id=decision_id, matched=[matched[0]], warnings=list(warnings))

        if self._mode == "inverse":
            excluded = [rid for rid, val in rule_results if not val]
            return MatchResult(id=decision_id, excluded=excluded, warnings=list(warnings))

        if self._mode == "score":
            total = 0.0
            for _rid, val in rule_results:
                if isinstance(val, bool):
                    total += 1.0 if val else 0.0
                elif isinstance(val, (int, float)):
                    total += float(val)
            result = MatchResult(id=decision_id, score=total, warnings=list(warnings))
            if self._threshold is not None and total >= self._threshold:
                result.matched = [rid for rid, val in rule_results if val]
            return result

        raise ValueError(f"Unknown match mode: {self._mode!r}")
