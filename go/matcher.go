package amino

import "sort"

// MatchConfig selects how rule results are aggregated into a MatchResult.
type MatchConfig struct {
	Mode      string   // "all" (default), "first", "inverse", "score"
	Key       string   // first: the Rule.Meta key to order by
	Order     string   // first: "asc" (default) or "desc"
	Aggregate string   // score: "sum" (the only aggregate)
	Threshold *float64 // score: when set and met, Matched lists the truthy rules
}

// MatchResult is the outcome of evaluating a rule set against one record.
type MatchResult struct {
	ID       any      // the record's "id" value, if any
	Matched  []string // rule ids that matched (all, first, score with threshold)
	Excluded []string // rule ids that did not match (inverse)
	Score    *float64 // the aggregate (score)
	Warnings []string // validation warnings in loose mode
}

type ruleResult struct {
	id    string
	value any
}

func (c *CompiledRules) match(id any, results []ruleResult, warnings []string) (MatchResult, error) {
	out := MatchResult{ID: id, Matched: []string{}, Excluded: []string{}, Warnings: warnings}
	if out.Warnings == nil {
		out.Warnings = []string{}
	}
	cfg := c.cfg
	mode := cfg.Mode
	if mode == "" {
		mode = "all"
	}
	switch mode {
	case "all":
		for _, r := range results {
			if truthy(r.value) {
				out.Matched = append(out.Matched, r.id)
			}
		}
	case "first":
		var matched []string
		for _, r := range results {
			if truthy(r.value) {
				matched = append(matched, r.id)
			}
		}
		if len(matched) == 0 {
			return out, nil
		}
		if cfg.Key != "" {
			desc := cfg.Order == "desc"
			keyOf := func(id string) (float64, bool) {
				meta := c.meta[id]
				if meta == nil {
					return 0, false
				}
				return toFloat(meta[cfg.Key])
			}
			sort.SliceStable(matched, func(i, j int) bool {
				a, aok := keyOf(matched[i])
				b, bok := keyOf(matched[j])
				if !aok {
					return false
				}
				if !bok {
					return true
				}
				if desc {
					return a > b
				}
				return a < b
			})
		}
		out.Matched = []string{matched[0]}
	case "inverse":
		for _, r := range results {
			if !truthy(r.value) {
				out.Excluded = append(out.Excluded, r.id)
			}
		}
	case "score":
		total := 0.0
		for _, r := range results {
			switch v := r.value.(type) {
			case bool:
				if v {
					total++
				}
			default:
				if f, ok := toFloat(v); ok {
					total += f
				}
			}
		}
		out.Score = &total
		if cfg.Threshold != nil && total >= *cfg.Threshold {
			for _, r := range results {
				if truthy(r.value) {
					out.Matched = append(out.Matched, r.id)
				}
			}
		}
	default:
		return out, newError(CodeConfig, "unknown match mode %q", mode)
	}
	return out, nil
}
