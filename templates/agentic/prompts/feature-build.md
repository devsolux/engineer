# Prompt template: feature build

```
engineer - [feature name]

Goal: [one sentence]
Scope: touch features/foo/ only; do not refactor unrelated code
Context: Next 16 + Supabase; similar pattern in features/bar/
Acceptance:
- [ ] RLS if new tables
- [ ] getUser() + Zod on mutations
- [ ] loading/empty/error states
- [ ] npm run typecheck && npm run engineer:scan --strict
```
