## engineer ship gate

Verify before requesting review:

- [ ] **Types** compile; no new unjustified `any`
- [ ] **Zod** on all new external inputs (forms, API, webhooks)
- [ ] **Auth** on mutations — `getUser()` in Server Actions
- [ ] **RLS** enabled if schema changed (`check-rls-migration.sh` passes)
- [ ] **States** — loading, empty, error on async UI
- [ ] **Tokens** — semantic colors only (engineer-scan passes)
- [ ] **a11y** — labels on inputs, focus visible, keyboard reachable
- [ ] **Secrets** — none in client; service role server-only
- [ ] **Tests** — unit for schemas/logic; e2e if critical path changed

### Automated checks (must pass)

- [ ] `npm run typecheck`
- [ ] `npm run lint:ci`
- [ ] `npm run engineer:scan -- --strict`

### Screenshots (UI changes)

<!-- Before/after or Loom for visual changes -->
