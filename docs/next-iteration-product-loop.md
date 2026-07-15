# Next Iteration: Product Loop and Personal Context

This is intentionally outside the current backend task-execution refactor. Start it only after the frontend uses the canonical Goal and Run contracts.

## Questions to Resolve

- **Growth loop**: connect completed Steps and Reward Settlement to capabilities, progress, and meaningful follow-up Goals. Avoid rewards that exist only as decorative counters.
- **Marketplace**: keep the system marketplace only if purchases unlock clear capabilities, services, content, or user choices. Otherwise remove it instead of preserving a disconnected novel-inspired mechanic.
- **System companion**: define a permissioned Context Gateway through which the companion can read approved user data such as current conversation context, Goals and Runs, capabilities, profile preferences, and marketplace state if retained.
- **Context engineering**: assemble task-specific context with provenance, freshness, sensitivity, and token budgets instead of sending every user record to every model call.
- **Long-term memory**: separate durable facts, preferences, episodic summaries, and inferred profile traits. Every memory needs source, confidence, update time, visibility, and deletion controls.
- **User profile**: evaluate useful profile extraction and update patterns from the local open-source reference at D:/app/OpenBiliClaw/; absorb principles and contracts, not project-specific coupling.
- **Closed-loop actions**: let recommendations become reviewable Goals or Run drafts, and feed verified outcomes back into profile and planning only with explicit policy.

## Guardrails

- User data access is explicit, owner-scoped, auditable, and revocable.
- Inferences are labeled separately from user-provided facts.
- The companion uses Core interfaces rather than querying application tables directly.
- Marketplace, memory, and profile modules must remain optional so Workspace Core can migrate to another product shell.
