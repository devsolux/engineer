# Product onboarding: activation UI patterns

**Last verified**: 2026-07-14 · **Review cadence**: 3 months

Strategy: define activation event in `growth-funnels.md`. UX patterns: `design-patterns.md`.
Emails: `email-notifications.md` (suppress onboarding when activated). Motion: `design-motion.md`.

## Contents
- [Activation-first design](#activation-first-design)
- [Empty states as primary surface](#empty-states-as-primary-surface)
- [Behavior-gated checklist](#behavior-gated-checklist)
- [Setup wizard vs checklist](#setup-wizard-vs-checklist)
- [Sample data pattern](#sample-data-pattern)
- [Progress and momentum](#progress-and-momentum)
- [Orchestration (do not stack noise)](#orchestration-do-not-stack-noise)
- [Instrumentation](#instrumentation)
- [Anti-patterns](#anti-patterns)

## Activation-first design

Every new-user screen answers: **"What's the one action that leads to aha moment?"**

```
Signup → minimal gate (email/OAuth)
 → land on dashboard with ONE primary CTA (not feature tour)
 → user completes activation event
 → celebrate + suggest next habit action
```

Target: activation in **first session** (<15 min TTV). See growth-funnels benchmarks.

## Empty states as primary surface

In 2026 practice, empty states are the **main onboarding surface** - not a dead end after a tour.

```tsx
export function ProjectsEmptyState() {
 return (
 <div className="flex flex-col items-center gap-4 rounded-lg border border-border bg-card p-12 text-center">
 <h2 className="text-lg font-semibold">Create your first project</h2>
 <p className="text-muted-foreground max-w-sm">
 Projects organize your work. Most teams start with one in under a minute.
 </p>
 <CreateProjectButton size="lg" />
 {/* optional secondary - never equal weight to primary */}
 <button type="button" className="text-sm text-muted-foreground underline">
 Explore sample project
 </button>
 </div>
 );
}
```

Rules:
- **One** primary CTA - not three equal buttons
- Outcome language - not "No data" or "Nothing here yet"
- Optional illustration - never blocks CTA
- Same layout dimensions as populated state (CLS)
- Prefer **sample data or template** over a blank canvas when the product needs data to make sense
- Empty state CTA should be the activation step when possible

## Behavior-gated checklist

3-5 items tied to **outcomes that lead to activation**, not every settings screen.

| Good item | Bad item |
|---|---|
| Create first project | Open settings |
| Invite a teammate (if collab is activation-adjacent) | Read the docs |
| Connect data source | Watch 4-minute tour |

Rules:
- **Behavior-gated**: item completes when product state changes, not when user clicks "Mark done"
- Skippable sidebar or panel - never a blocking modal before value
- Hide or collapse checklist after activation event
- Optional steps clearly labeled; core path stays short
- Each item deep-links into the action surface

```tsx
const items = [
 { id: "project", title: "Create a project", done: hasProject, href: "/projects/new" },
 { id: "invite", title: "Invite a teammate", done: hasInvite, href: "/settings/team", optional: true },
] as const;
// complete when server state true - not localStorage-only checkmarks
```

Research cue: many users activate without finishing checklists - measure **activation**, not checklist 100%.

## Setup wizard vs checklist

| Pattern | Use when |
|---|---|
| **Single-screen CTA** | Simple product (1 activation action) |
| **Optional checklist** | 3-5 setup steps, skippable |
| **Forced wizard** | Rare - only if steps are truly required (legal, billing entity) |

Make checklist **optional sidebar**, not blocking modal.

## Sample data pattern

Complex products (analytics, dashboards):

- Offer **"Try with sample data"** on empty state
- Pre-seed demo workspace on signup (server-side, flagged `is_demo`)
- Clear badge: "Sample data - replace with yours"
- One-click purge sample data
- Sample workspace still goes through RLS as a real org when possible

Reduces TTV when real data requires imports/integrations.

## Orchestration (do not stack noise)

Do **not** fire all of these on first session at once:

- full-screen tour
- checklist
- welcome modal
- chat bubble
- three lifecycle emails in 10 minutes
- tooltip hotspots on every control

Pick **one** primary in-app guide (usually empty state + optional checklist). Lifecycle email reinforces the same activation event and **suppresses** when it fires (`email-notifications.md`).

## Progress and momentum

After activation event:
- **Celebration** - subtle confetti or success toast (honor `prefers-reduced-motion`)
- **Next step** - one suggested action ("Invite teammate", "Connect integration")
- **Progress bar** - only if multi-step setup is optional, not gate

Progress indicator:

```tsx
<p className="text-sm text-muted-foreground">
 Step 2 of 3 - Connect your data source
</p>
<Progress value={66} className="h-2" />
```

## Instrumentation

Fire events at onboarding boundaries:

```typescript
track(Events.SIGNUP_COMPLETED);
track(Events.ACTIVATION_COMPLETED, { method: "create_project" });
track(Events.ONBOARDING_STEP, { step: "invite_teammate", completed: true });
```

Define activation event with growth/founder before building UI.

## Anti-patterns

- Feature tour modal on first login (blocks TTV)
- Empty dashboard with no CTA
- Forced 10-step wizard before any value
- Checklist completion treated as activation metric
- Multiple competing primary actions on empty state
- Onboarding copy that describes features not outcomes
- LocalStorage-only checklist that ignores server product state
- Tour + checklist + email + chat all on first paint

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
