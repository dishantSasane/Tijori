# P1e regime activation contract

Status: fixed routing contract, not fitted. The first version uses only two
declared state variables and a flat fallback. It cannot make a strategy
eligible based on its backtest rank alone.

## State inputs

At a closed daily bar, compute:

- Trend: `up` when close > SMA(200) and SMA(200) > its value 20 sessions ago;
  `down` when close < SMA(200) and SMA(200) < its value 20 sessions ago;
  otherwise `sideways`.
- Volatility: `normal` when ATR(14) / close is at or below the 80th percentile
  of the previous 252 completed daily values; otherwise `high`. The current
  value is compared only with prior values. If any required value is missing,
  state is `unknown` and no new strategy is eligible.

Percentile convention: sort prior values ascending and select nearest-rank
index `ceil(0.8*n)-1`; require 252 prior non-null values. This fixed rule is
not a parameter sweep. No market-news, LLM, or future bar data enters state.

## Strategy declarations

Each candidate version declares a non-empty set of allowed `(trend, volatility)`
states before testing. Initial hypothesis declarations:

- T1, T2, T3: `(up, normal)` and `(up, high)`; strategy's own stop/risk rules
  remain responsible for high-volatility exposure.
- T4, T6: `(up, normal)` and `(sideways, normal)` for research comparison;
  these declarations are hypotheses, not assumptions of efficacy.
- Custom RPF: `(up, normal)` only, after its full rules are made mechanical.
- T5: not in the daily activation layer.

Only versions marked `promoted` by the P1d evaluation policy may be routed.
Development/validation winners remain research candidates. The promotion
status and rule version are part of the input provenance.

## Routing and overlap

For one instrument and decision bar:

1. If state is unknown, emit `abstain:unknown_state`.
2. Filter to promoted versions whose declared state set contains the current
   state.
3. If none remain, emit `abstain:no_eligible_strategy`.
4. Return exact `(strategy_id, version)` pairs. If exactly one remains, return
   that version as eligible.
5. If more than one remains, return all versioned pairs as an overlap conflict; defer the
   signal collision to the existing overlap guard/risk engine (RISK_SPEC I11).
   The activation layer never invents a performance-based tie-break.

Record per-version and per-instrument activation opportunities, eligible
count, abstentions, conflicts, and signals attributed to that exact version.
Rules remain frozen across the holdout; any change creates a new version and a
new experiment family. Invalid or non-finite feature inputs produce unknown
state and abstain.
