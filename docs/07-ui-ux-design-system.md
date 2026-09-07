# 07 — UI/UX Design System

The brief asks for "n8n's UI, but extremely beautiful." That is a real, achievable brief if it is
translated into rules rather than adjectives. This document is that translation.

## 7.1 What we take from n8n, and what we do differently

**Take:** the node canvas as the primary surface; the three-column inspector (input / params /
output); data-as-items made visible everywhere; the left-to-right flow direction; the dense,
information-first attitude.

**Do differently:**

| n8n | NeuroFlow | Why |
|---|---|---|
| Bright orange-red accent, high-saturation node colours | Restrained neutral base, one accent, category colour used only in icon tiles and status | Fifty saturated nodes on one screen is visual noise; colour should carry meaning, not decoration |
| Fairly flat, utilitarian chrome | Considered elevation, one soft shadow scale, 1px hairline borders | Depth is what separates "functional" from "polished" |
| Mixed spacing rhythm | Strict 4px base / 8px rhythm | Consistency reads as craft more than any single flourish |
| Dark mode as a variant | Both themes designed as first-class OKLCH sets | Half our users live in dark mode |
| Modal-heavy configuration | Panels and sheets; modals reserved for destructive confirms | Modals break the context that makes the inspector useful |

The aesthetic target is closer to Linear or Vercel's dashboard than to a traditional ops tool:
quiet surfaces, sharp typography, generous-but-not-wasteful spacing, and motion that clarifies
rather than entertains.

## 7.2 Foundation: what already exists

`src/index.css` already defines a complete OKLCH token set with `:root` and `.dark` variants,
mapped into Tailwind v4 via `@theme inline`, plus a radius scale derived from `--radius`. **This
is the design system's foundation and MUST NOT be replaced** — it is coherent, it is what the 61
shadcn primitives are wired to, and rewriting it would mean re-theming all of them.

What we add is **semantic tokens the base set lacks** and a set of composition rules.

### Tokens to add

```css
:root {
  /* status — used by node rings, badges, execution states */
  --success: oklch(0.62 0.17 149);   --success-foreground: oklch(0.985 0 0);
  --warning: oklch(0.75 0.16 78);    --warning-foreground: oklch(0.20 0 0);
  --info:    oklch(0.62 0.16 250);   --info-foreground: oklch(0.985 0 0);
  /* destructive already exists */

  /* canvas */
  --canvas-bg:   oklch(0.985 0 0);
  --canvas-dot:  oklch(0.90 0 0);
  --edge:        oklch(0.72 0 0);
  --edge-active: var(--primary);

  /* node category tints — icon tile backgrounds only */
  --cat-trigger: oklch(0.70 0.17 40);    --cat-flow:    oklch(0.65 0.16 275);
  --cat-data:    oklch(0.68 0.15 190);   --cat-ai:      oklch(0.66 0.18 300);
  --cat-app:     oklch(0.67 0.14 220);   --cat-code:    oklch(0.62 0.02 260);
}
.dark {
  --canvas-bg: oklch(0.16 0 0);  --canvas-dot: oklch(0.26 0 0);  --edge: oklch(0.42 0 0);
  --success: oklch(0.70 0.16 149); --warning: oklch(0.80 0.15 78); --info: oklch(0.70 0.15 250);
  /* category tints lift ~0.06 L and drop ~0.02 C in dark to hold contrast */
}
```

Each new token is registered in the `@theme inline` block so `bg-success`, `text-warning`,
`border-edge` become real utilities. **Rule: no raw colour value ever appears in a component.**
A hex or `oklch()` literal outside `index.css` is a review rejection.

## 7.3 Typography

Geist Variable, already installed. One family, four sizes, three weights — the discipline is the
point.

| Role | Size / line-height | Weight | Used for |
|---|---|---|---|
| Display | 24 / 32 | 600 | Page titles |
| Heading | 16 / 24 | 600 | Section headers, panel titles, node titles |
| Body | 14 / 20 | 400 | Default — everything |
| Small | 12 / 16 | 400/500 | Labels, metadata, badges, node subtitles |
| Mono | 13 / 20 | 400 | JSON, code, expressions, IDs (`ui-monospace`/Geist Mono) |

Rules: body text never below 12px; labels are `text-small font-medium text-muted-foreground`;
numbers in tables use `tabular-nums`; IDs are always mono with a copy affordance.

## 7.4 Spacing, radius, elevation

**Spacing** — 4px base, and only these steps: `4, 8, 12, 16, 24, 32, 48, 64`. Component internal
padding is 12 or 16; section gaps are 24; page padding is 24 (32 on wide viewports). An arbitrary
`p-[13px]` is a bug.

**Radius** — `--radius: 0.625rem` (10px) exists; the derived scale gives sm 6 / md 8 / lg 10 /
xl 14. Cards and nodes use `lg`; inputs and buttons `md`; badges and pills `sm`; sheets and
dialogs `xl`.

**Elevation** — four levels, no more:

```
0  flat            — canvas, page background
1  hairline        — cards, nodes at rest: 1px border, no shadow
2  raised          — hovered node, dropdown, popover: 0 1px 2px / 0 2px 8px @ 6%
3  floating        — dialog, sheet, command palette: 0 8px 32px @ 12%
```

Dark mode reduces shadow opacity and leans on a lighter surface colour instead — shadows barely
read on dark backgrounds, and pushing them harder just produces murk.

## 7.5 Layout

**App shell** — 56px topbar, 240px collapsible sidebar (56px collapsed, icon-only), content area.
Built on the existing `sidebar` primitive. Sidebar: workspace switcher, then Workflows, Agents,
Executions, Credentials, Variables, Settings; user menu pinned bottom.

**Content pages** — max-width 1440px, centred, 24px gutters. The editor is the exception: it is
full-bleed, and the sidebar auto-collapses on entry.

**Density** — this is a professional tool used for hours. Table rows are 40px, not 56. List
padding is 12, not 20. Density is a feature here; airiness would be a mistake.

## 7.6 Motion

Motion exists to explain causality. Nothing animates for delight alone.

| Interaction | Duration | Easing |
|---|---|---|
| Hover / focus | 120 ms | `ease-out` |
| Panel open/close, sheet | 220 ms | `cubic-bezier(0.32,0.72,0,1)` |
| Dialog | 180 ms | `ease-out` |
| Toast | 240 ms | spring-ish out |
| Canvas auto-layout | 300 ms | `ease-in-out` |
| Edge dash flow | 1000 ms linear, infinite | — |
| Node status change | 160 ms | `ease-out` |

Nothing exceeds 300 ms except deliberate canvas layout. All of it is disabled under
`prefers-reduced-motion` except opacity fades. `tw-animate-css` is already installed for the
keyframe primitives.

## 7.7 Component patterns

**Buttons** — one primary per view. `default` for the main action, `secondary` for adjacent,
`ghost` for toolbars and icons, `destructive` only for destruction. Icon-only buttons always carry
a tooltip with the keyboard shortcut in a `<Kbd>`.

**Forms** — labels above inputs, always. Helper text below in `text-small text-muted-foreground`.
Errors replace helper text in `text-destructive` and are announced. Required fields marked on the
label, not by placeholder. Placeholders show *format examples*, never restate the label.

**Empty states** — every list has one, and it does three things: says what this is, why it is
empty, and offers the primary action. The `empty` primitive is already installed. An empty state
that just says "No data" is a missed onboarding opportunity, and this product has a lot of first-run
surfaces.

**Loading** — skeletons that match the final layout for initial loads (no layout shift);
`spinner` inside buttons for pending mutations; a thin top progress bar for route transitions.
Never a full-page spinner on a route that has a known shape.

**Tables** — sticky header, 40px rows, hover highlight, row click opens detail, checkbox column
only when bulk actions exist, keyset pagination ("Load more" / infinite scroll, not page numbers —
see [11](./11-api-design.md)).

**Toasts** — mutations only. Success is short and specific ("Workflow saved"), never "Success!".
Errors include the server message and a copyable request ID. Auto-dismiss 4 s for success,
persistent for errors.

**Destructive confirms** — an `alert-dialog` naming the object exactly ("Delete *Stripe sync*?"),
stating consequences ("124 executions will be retained"), with the destructive verb on the button
("Delete workflow", not "OK").

## 7.8 Iconography

Lucide, already installed. 16px in dense UI, 20px in nav, 32px in node tiles. Stroke width 1.5 —
2 reads heavy at small sizes. Icons are never the sole carrier of meaning outside a toolbar, and
toolbar icons always have tooltips.

**Integration logos** are the exception: real brand SVGs for Slack, Stripe, Postgres, etc.,
rendered inside a neutral tile. Users identify integrations by logo faster than by any label.

## 7.9 Writing

Copy is design. Rules:

- Sentence case everywhere. No Title Case, no ALL CAPS except 11px badge labels.
- Second person, active, present: "Connect your account," not "Account must be connected."
- Errors state what happened, why, and the next action: *"Couldn't reach api.stripe.com — the
  request timed out after 30s. Check the URL, or increase the timeout in node settings."*
- Never expose internal vocabulary — no "null", "500", "exception", "serialization" in user copy.
- Buttons are verbs. Never "Submit" or "OK".
- Numbers get units and separators: "1,240 items", "1.2 s", "4.3 MB".

## 7.10 Dark mode

Both themes are designed, not derived. Specific rules that prevent the common dark-mode failure:

- Elevation goes *up* in lightness, not down in shadow. A raised surface in dark mode is
  `oklch(0.22)` against `oklch(0.16)`.
- Pure black (`oklch(0 0 0)`) and pure white text are banned — `0.145` and `0.985` are the
  existing bounds and they are correct.
- Saturated accents lose ~0.02 chroma and gain ~0.05 lightness in dark to avoid vibration.
- The canvas dot grid uses a lighter dot in dark mode, not an inverted one.
- Every screenshot in review must be shown in both themes. Bugs here are found by looking.

## 7.11 Accessibility baseline

- WCAG 2.1 AA: 4.5:1 for body text, 3:1 for large text and UI boundaries. Verified per token
  pair, both themes, in CI via a contrast script.
- Visible focus ring on every interactive element: 2px `--ring`, 2px offset. Never `outline: none`
  without a replacement.
- Full keyboard operability, logical tab order, `Escape` closes every overlay, focus trapped in
  dialogs and restored on close.
- All icon-only controls have `aria-label`. All form controls have real `<label>` associations.
- Status is communicated by icon + text + colour, never colour alone — critical for the execution
  states, which are the highest-stakes information in the product.
- Respect `prefers-reduced-motion` and `prefers-contrast`.

## 7.12 The polish checklist

A feature is not done until every line here is true. This list is the operational definition of
"extremely beautiful" and belongs in the PR template.

- [ ] Renders correctly in light and dark
- [ ] Loading, empty, error, and success states all exist and are designed
- [ ] Keyboard-operable end to end; focus ring visible
- [ ] No layout shift between skeleton and loaded content
- [ ] Hover, focus, active, and disabled states on every interactive element
- [ ] Spacing uses only the scale; no arbitrary values
- [ ] No hard-coded colours; tokens only
- [ ] Text truncates gracefully with a tooltip; tested with a 120-character name
- [ ] Responsive to 1280px minimum (editor); 768px (list pages)
- [ ] Copy follows §7.9
- [ ] Motion under 300 ms and reduced-motion safe
- [ ] Contrast verified
