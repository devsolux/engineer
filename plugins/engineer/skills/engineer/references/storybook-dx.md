# Storybook DX: component documentation (optional)

**Last verified**: 2026-07-12 · **Review cadence**: 6 months

**Optional** - shadcn components are source-owned in-repo; Storybook adds value
when design system grows beyond shadcn defaults or multiple contributors need
visual regression.

Skip if: solo dev, <20 custom components, no design team.

## When Storybook pays off

| Signal | Benefit |
|---|---|
| Shared `packages/ui` in monorepo | Document variants without running app |
| Design + eng handoff | Isolated component states |
| Visual regression (Chromatic) | Catch token/layout breaks |
| Complex compound components | DataTable, DatePicker edge cases |

## Setup (Next.js + shadcn)

```bash
npm install --save-dev --save-exact storybook@10.5.0
npm exec --offline -- storybook init
```

Configure for App Router + Tailwind v4:
- Import `globals.css` in `.storybook/preview.tsx`
- Mirror `next/font` or use system fallbacks in preview
- Add path alias `@/` matching `tsconfig`

```typescript
// .storybook/preview.tsx
import type { Preview } from "@storybook/react";
import "../app/globals.css";

const preview: Preview = {
 parameters: {
 nextjs: { appDirectory: true },
 },
 decorators: [
 (Story) => (
 <div className="bg-background text-foreground p-4">
 <Story />
 </div>
 ),
 ],
};

export default preview;
```

## Story conventions

```typescript
// components/ui/button.stories.tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Button } from "./button";

const meta: Meta<typeof Button> = {
 component: Button,
 tags: ["autodocs"],
 argTypes: {
 variant: { control: "select", options: ["default", "destructive", "outline"] },
 },
};
export default meta;

type Story = StoryObj<typeof Button>;

export const Primary: Story = { args: { children: "Save changes" } };
export const Loading: Story = { args: { children: "Saving…", disabled: true } };
export const Destructive: Story = { args: { variant: "destructive", children: "Delete" } };
```

Rules:
- One story file per component (colocate with component)
- Cover variants, disabled, loading, empty - not just default
- Use **semantic tokens** in decorators - same as production (`design-system.md`)
- No hardcoded colors in stories

## States to document

| Component type | Stories |
|---|---|
| Button | default, loading, disabled, all variants |
| Form field | empty, error, disabled, with hint |
| Card/list | loading skeleton, empty, populated |
| Dialog | open (use render + userEvent or `open` prop) |
| DataTable | no rows, single page, many rows |

## next-intl in Storybook

If using i18n, add `storybook-next-intl` or wrap with `NextIntlClientProvider`:

```typescript
import { NextIntlClientProvider } from "next-intl";
import messages from "../messages/en.json";

decorators: [
 (Story) => (
 <NextIntlClientProvider locale="en" messages={messages}>
 <Story />
 </NextIntlClientProvider>
 ),
],
```

See `frontend-i18n.md`.

## a11y addon

Enable `@storybook/addon-a11y` - catches contrast and aria issues in isolation.
Does not replace `design-accessibility.md` gate or Playwright axe in CI.

## CI (optional L3)

```yaml
- run: npm run build-storybook
- run: npx chromatic --exit-zero-on-changes # if using Chromatic
```

Lower priority than `engineer-scan`, pgTAP, Playwright.

## Anti-patterns

| Don't | Do |
|---|---|
| Storybook as only documentation | README + engineer design modules |
| Duplicate production CSS incorrectly | Import same globals.css |
| Stories with lorem only | Realistic labels and states |
| Skip dark mode if app supports it | Theme toggle in preview |
| Storybook for every shadcn primitive unchanged | Story custom/wrapped components |

## Composition

| Module | When |
|---|---|
| `design-system.md` | Token usage in stories |
| `design-accessibility.md` | a11y addon thresholds |
| `frontend-i18n.md` | Locale provider in preview |
| `architecture-monorepo.md` | `packages/ui` Storybook location |

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
