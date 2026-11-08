# PROJECT CONSTITUTION & AGENTS OPERATIONAL PROTOCOL (SPEC-KIT SDD)

Project: **Vietnam Quantitative Multi-Agent Hedge Fund & Algorithmic Trading Platform**
Architecture Framework: **Specification-Driven Development (github/spec-kit)**

---

## 🏛️ SECTION 1: CORE SPEC-DRIVEN DEVELOPMENT (SDD) PRINCIPLES

1. **The Power Inversion**: Code serves specifications; specifications do not serve code. All trading strategies, data models, agent behaviors, and UI dashboards must be backed by living, executable specifications.
2. **Intent-First & No Vibe Coding**: Never write ad-hoc trading logic or speculative algorithms without formal definitions of mathematical formulas, edge cases (e.g. T+2.5, floor/ceiling price limits, zero-liquidity), and acceptance criteria.
3. **Structured 6-Phase Lifecycle**:
   - `Constitution`: Capital preservation first, strict risk limits, zero tolerance for contradictions.
   - `Specify`: User stories prioritized by P1 (Core MVP), P2 (Enhancements), P3 (Advanced).
   - `Clarify`: Active clarification of ambiguities, risk thresholds, and market regimes.
   - `Plan`: Architectural blueprint with data models, calculation engines, and visual contracts.
   - `Tasks`: Atomic task breakdown (`T001...`) with parallelization markers `[P]`.
   - `Implement & Verify`: Deterministic verification with test scripts before reporting completion.

---

## 🛡️ SECTION 2: INSTITUTIONAL TRADING INVARIANTS & CONSTITUTIONAL RULES

1. **Capital Preservation Non-Negotiable**:
   - Stage 4 Downtrend stocks (Stan Weinstein & Mark Minervini) are strictly VETOED (0% allocation).
   - Under no circumstances can a Stage 1 (Accumulation / Base) or Stage 4 stock be recommended under "Top Cổ Phiếu Chuẩn Điểm Mua Stage 2".
2. **Three-Tier Institutional Separation**:
   - 🟢 **Tier 1 (Approved Stage 2 Buys)**: Stage 2 + SEPA ≥ 5/8 + RS ≥ 65 + Score ≥ 35 + CIO Approval.
   - 🟡 **Tier 2 (Watchlist)**: Stage 1 accumulation or pullback at POC support (e.g., NKG, TPB, VJC). Allocation 0% NAV.
   - ⛔ **Tier 3 (Avoid / Veto)**: Stage 4 Downtrend & High Risk.
3. **Bidirectional Consistency**:
   - The Screener, the CIO Agent, the Risk Agent, and the AI Chat must maintain 100% mutual consensus. No contradictory verdicts are permitted.
4. **Vietnam Market Invariants**:
   - Account for settlement cycle $T+2.5$, price limits ($\pm 7\%$ HOSE, $\pm 10\%$ HNX, $\pm 15\%$ UPCOM), round-lot 100 shares, and foreign investor cashflow.
5. **Self-Learning Reflection Loop**:
   - All recommendation outcomes and user corrections must be recorded in `data/reflection_memory.json` and `data/self_learning_memory.json` to continuously refine parameters.
