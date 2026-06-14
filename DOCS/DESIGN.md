# DESIGN.md

Minimal design system for the QKD Adversarial Evolution Benchmark dashboard.

## Theme

Dark theme only. Desktop-only (1280px minimum viewport).

## Colors

```
Background:     #0d1117
Surface:        #161b22  (panels, cards)
Border:         #30363d  (subtle dividers)
Text primary:   #e6edf3
Text secondary: #8b949e
Blue (defense): #58a6ff
Red (attack):   #f85149
Success:        #3fb950
Warning:        #d29922
Purple:         #a371f7
Orange:         #f0883e
```

## Attack Type Colors + Shapes

| Attack Type      | Color   | Shape          |
|------------------|---------|----------------|
| intercept_resend | #f85149 | circle         |
| beam_splitting   | #d29922 | diamond        |
| pns_attack       | #a371f7 | triangle       |
| trojan_horse     | #f0883e | square         |
| clean            | #3fb950 | circle-outline |

All data is double-encoded (color + shape) for colorblind accessibility.

## Typography

| Role     | Font            | Size | Weight   |
|----------|-----------------|------|----------|
| Data     | JetBrains Mono  | 13px | Regular  |
| Labels   | Inter           | 14px | Regular  |
| Headings | Inter           | 16px | Semibold |
| Title    | Inter           | 20px | Bold     |

## Spacing

8px base unit: 8, 16, 24, 32, 48.

## Chart Library

D3.js for all visualizations (line charts, bar charts, confusion matrices, phylogeny tree).

## Principles

- Data-dense but readable
- Calm surface hierarchy
- Utility language (orientation, status, action)
- No decorative elements
- Monospace for all numerical data
- Panels separated by subtle borders or whitespace, not card shadows
