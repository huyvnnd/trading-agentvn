# WORKSPACE RULE: SPECIFICATION-DRIVEN DEVELOPMENT (SPEC-KIT SDD)

Applied to all development, feature additions, and refactoring within this workspace.

## 1. Specification Before Code
- Always draft or verify the feature specification (`specs/[feature-name]/spec.md`) and implementation plan (`plan.md`) before modifying system code.
- Prioritize user stories into P1 (MVP), P2, P3. Every story must be an independently testable vertical slice.

## 2. Clarification Before Planning
- Proactively clarify edge cases: missing data, network timeouts, zero volume, division by zero in financial ratios, T+2.5 settlement timing, price ceiling/floor caps.

## 3. Atomic Task Discipline
- Break plans into discrete tasks (`T001...`) in `tasks.md`.
- Mark parallelizable tasks `[P]`.
- Implement and verify task by task.

## 4. Verification Evidence
- Run verification tests with Python virtualenv (`/home/osboxes/Desktop/trading/venv/bin/python3`) after every major change.
- Verify that background daemons (e.g. Streamlit on port 8502) run cleanly and respond with HTTP 200.
