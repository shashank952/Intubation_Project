# Airway MD Design Contract

## Reference Direction

The full-screen loading state follows the supplied reference: an airy pale
ice-blue field with a small centered charcoal airway mark. It is quiet,
clinical, and spatially calm; no card, shadow, copy, or dashboard chrome
appears in the splash state.

## Existing Product System

- Surface: paper/cream in the product UI, with switchable brand ramps through
  `--brand-*`; near-black ink, 2px structural borders, square 4px corners,
  and hard offset shadows.
- Typography: Inter for interface text, JetBrains Mono for system/status text.
- Motion: transform/opacity only; mechanical `steps()` motion for loaders;
  reduced-motion users receive a static, fully visible state.
- Dark mode: class-based; product surfaces use `#121212` and neutral outlines.

## Loading Primitives

- `NeoLoader` inline: compact pulse blocks for buttons and micro states.
- `NeoLoader` block: bordered dashboard loading panel with a scan bar.
- `NeoLoader` page: reference-fidelity splash with the centered airway mark.
- `app/loading.tsx`: route transition fallback using the page primitive.
