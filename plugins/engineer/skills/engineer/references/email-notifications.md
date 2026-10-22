# Email & notifications: transactional and lifecycle

**Last verified**: 2026-10-22 · **Review cadence**: 3 months

Strategy: `growth-funnels.md` (activation event first). Auth emails: Supabase Auth templates.
Jobs: `background-jobs.md` for durable send workers.

## Contents
- [Stack choice](#stack-choice)
- [React Email + Resend](#react-email--resend)
- [Supabase Auth emails](#supabase-auth-emails)
- [Lifecycle templates](#lifecycle-templates)
- [Behavioral onboarding (suppress on success)](#behavioral-onboarding-suppress-on-success)
- [Dunning / failed payment](#dunning--failed-payment)
- [In-app notifications](#in-app-notifications)
- [Deliverability](#deliverability)
- [Anti-patterns](#anti-patterns)

## Stack choice

| Provider | Best for |
|---|---|
| **Resend** + React Email | Transactional + product emails from Next.js |
| **Supabase Auth** | Magic link, confirm, reset (built-in) |
| **Postmark / SendGrid** | High-volume transactional |
| **Customer.io / Loops** | Marketing automation (founder-owned) |

Developer builds: templates + send API + webhook hooks. Founder owns copy/sequences.

## React Email + Resend

```typescript
// emails/welcome.tsx (React Email 6+: components ship in `react-email`;
// `@react-email/components` is deprecated)
import { Html, Body, Text, Button } from "react-email";

export interface WelcomeEmailProps {
 name: string;
 activationUrl: string;
}

export function WelcomeEmail({ name, activationUrl }: WelcomeEmailProps) {
 return (
 <Html>
 <Body>
 <Text>Hi {name},</Text>
 <Text>One step left - create your first project.</Text>
 <Button href={activationUrl}>Get started</Button>
 </Body>
 </Html>
 );
}
```

```typescript
// lib/email/send.ts
import "server-only";
import { Resend } from "resend";
import { WelcomeEmail, type WelcomeEmailProps } from "@/emails/welcome";

const resend = new Resend(process.env.RESEND_API_KEY);

export async function sendWelcomeEmail(to: string, props: WelcomeEmailProps) {
 // SDK returns { data, error } instead of throwing - surface failures to the job
 const { data, error } = await resend.emails.send({
 from: "Product <hello@example.com>",
 to,
 subject: "Finish setting up your account",
 react: WelcomeEmail(props),
 });
 if (error) throw new Error(`resend: ${error.message}`);
 return data?.id;
}
```

Send from Server Actions or webhook handlers - never expose API key client-side.

## Supabase Auth emails

Customize in Supabase Dashboard → Auth → Email Templates:
- Confirm signup
- Magic link
- Reset password
- Also: invite, change email, reauthentication; opt-in security notifications (password/email changed)

Custom SMTP (Resend, Postmark, SES...) is required in production: the built-in sender only
delivers to project team addresses at ~2 emails/hour. Custom SMTP starts at 30/hour; raise it under Auth rate limits.

## Lifecycle templates

| Trigger | Email | Send from |
|---|---|---|
| Signup complete | Welcome + **one** next step to activation | Server Action / auth hook |
| Signup, no activation 24h | Setup reminder | Cron / durable job |
| Still no activation day 3-4 | Feature tip tied to activation event | Cron (skip if activated) |
| Trial ending 3d | Upgrade CTA | Stripe webhook + scheduler |
| Payment failed | Update card | `invoice.payment_failed` webhook |
| Team invite | Invite link | Server Action on invite |

**Principle:** every onboarding email drives the **single activation event** from `growth-funnels.md`. Not three CTAs. Behavior beats pure time drips: suppress remaining onboarding once `activation_completed` fires.

Idempotency: track sends in DB (unique on user + template + window); on retries also pass
Resend's `idempotencyKey` (second arg to `emails.send`, kept 24h).

```sql
create table public.email_log (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users,
 template text not null,
 provider_id text,
 sent_at timestamptz not null default now()
);

-- prevent double-send of same template within a UTC day
-- (bare sent_at::date is STABLE, not IMMUTABLE, so Postgres rejects it in an index)
create unique index email_log_user_template_day
 on public.email_log (user_id, template, ((sent_at at time zone 'UTC')::date));

alter table public.email_log enable row level security;
-- no client policies; service role / server only
```

## Behavioral onboarding (suppress on success)

```text
signup
 -> welcome (immediate)
 -> if !activation @ +24h -> nudge_1
 -> if !activation @ +72h -> nudge_2
 -> if activation_completed -> cancel remaining onboarding jobs
```

| Rule | Why |
|---|---|
| One activation-shaped CTA | Higher conversion than multi-link blasts |
| Suppress on product event | Stops nagging after success |
| Durable job + cancel token | Survives deploys; avoid double fire |
| Instrument `email.sent` + `email.clicked` | Debug lifecycle, not vanity opens alone |

Wire product events into the worker the same way you wire analytics (`activation_completed`).

## Dunning / failed payment

Involuntary churn from failed cards is large; treat dunning as product-critical.

| Step | When | Content |
|---|---|---|
| 1 | `invoice.payment_failed` immediate | Update card + billing portal link |
| 2 | +2-3 days if still open | Urgency + support path |
| 3 | +5-7 days / before cancel | Final notice |

Rules:
- Send from **webhook + durable job**, not only success_url
- Idempotent on `invoice.id` + step
- Link to Stripe Customer Portal (server-created session)
- Do not unlock paid features on client query params (`billing-stripe.md`)
- Log outcomes to `audit_log` / billing events for support

## In-app notifications

Prefer in-app for real-time; email for async/nudge:
- Toast: immediate feedback
- Notification bell + unread count: Supabase Realtime or polling
- Banner: account-level (trial ending)

Don't email AND in-app spam the same event within minutes.

## Deliverability

- Verify a sending subdomain in Resend (SPF + DKIM records), then publish DMARC (`p=none` minimum)
- `hello@` or `notifications@` - not no-reply without reason
- One primary CTA per email
- Plain-text fallback (Resend auto)
- Unsubscribe link on marketing; transactional exempt but include preferences link
- Bulk senders (~5,000+/day to Gmail or Outlook.com; Yahoo too): SPF **and** DKIM pass, DMARC aligned
 with the From domain. Gmail/Yahoo: marketing mail needs one-click unsubscribe (`List-Unsubscribe` +
 `List-Unsubscribe-Post: List-Unsubscribe=One-Click`, RFC 8058) honored within 2 days; spam rate < 0.3% (aim < 0.1%)
- Test with [mail-tester.com](https://www.mail-tester.com) before launch

## Anti-patterns

- Sending from unverified domain
- API key in client
- Marketing email without unsubscribe
- Duplicate lifecycle emails (no idempotency)
- Time-only drip that ignores activation (nags converted users)
- Full HTML string concat - use React Email components
- Password or magic link in logs
- Three competing CTAs in one onboarding email

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
