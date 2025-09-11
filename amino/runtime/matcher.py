"""Pattern matching and result handling."""

import dataclasses
import enum
from typing import Any, Literal


class MatchMode(enum.Enum):
    """Rule matching modes."""
    ALL = "all"          # Return all matching rules
    FIRST = "first"      # Return first match based on ordering
    BEST = "best"        # Return best match based on score


@dataclasses.dataclass
class MatchOptions:
    """Options for rule matching."""
    mode: MatchMode = MatchMode.ALL
    ordering_key: str | None = None
    ordering_direction: Literal["asc", "desc"] = "asc"


@dataclasses.dataclass
class MatchResult:
    """Result of rule evaluation."""
    id: Any
    results: list[Any] = dataclasses.field(default_factory=list)
    metadata: dict[str, Any] | None = None


class RuleMatcher:
    """Handles rule matching logic and result formatting."""

    def __init__(self, options: MatchOptions | None = None):
        self.options = options or MatchOptions()

    def process_matches(self, data_id: Any, rule_matches: list[tuple[Any, bool]],
                       rule_metadata: dict[Any, dict] | None = None) -> MatchResult:
        """Process rule evaluation results into final match result."""
        rule_metadata = rule_metadata or {}

        # Filter to only matched rules
        matched_rules = [rule_id for rule_id, matched in rule_matches if matched]

        if self.options.mode == MatchMode.ALL:
            return MatchResult(data_id, matched_rules)

        elif self.options.mode == MatchMode.FIRST:
            if not matched_rules:
                return MatchResult(data_id, [])

            # Sort by ordering if specified
            if self.options.ordering_key:
                sorted_rules = self._sort_rules(matched_rules, rule_metadata)
                return MatchResult(data_id, [sorted_rules[0]] if sorted_rules else [])
            else:
                return MatchResult(data_id, [matched_rules[0]])

        else:
            # For now, treat BEST the same as FIRST
            return self.process_matches(data_id, rule_matches, rule_metadata)

    def _sort_rules(self, rule_ids: list[Any], metadata: dict[Any, dict]) -> list[Any]:
        """Sort rules by ordering key."""
        if not self.options.ordering_key:
            return rule_ids

        def get_ordering_value(rule_id):
            meta = metadata.get(rule_id, {})
            return meta.get(self.options.ordering_key, float('inf'))

        reverse = self.options.ordering_direction == "desc"
        return sorted(rule_ids, key=get_ordering_value, reverse=reverse)
