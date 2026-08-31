# Gaming in Russia 2026 — Interactive Dashboard

Interactive bilingual (RU/EN) dashboard built on the microdata of the
**«Gaming in Russia 2026»** sociological survey by **RVI × NAFI × IFSI**
(4,932 respondents aged 14+, fieldwork October 2025).

**Official study website:** <https://gaminginrussia.forgamedev.ru>

## What's inside

- **9 sections**: audience overview, gaming habits, money & market,
  attitudes & stereotypes, talking points, children & parents,
  esports & communities, non-gamers, correlations.
- **42 interactive charts** (ECharts), all recomputed in the browser from
  record-level weighted microdata.
- **Filters**: sex, age, million+ city, federal district, gamer status —
  every figure updates live.
- **Correlation explorer**: pick any two of 19 variables, the weighted
  Pearson coefficient and scatter recompute instantly.
- **Bilingual**: switch Russian / English at any time.

## Files

- `index.html` — the dashboard (self-contained UI + logic)
- `data.js` — compact weighted microdata extracted from the SPSS `.sav`
- `build_data.py` — extractor script (NAFI/RVI .sav → data.js)

## Methodology notes

All shares are **weighted** (raked weights from the source data).
Charts show the base (n) under each title. Device-specific genre charts
use the base of players on that device who named at least one genre —
the same convention as the published report.

This is an **unofficial** interactive tool built on open microdata;
please cite the official study when quoting numbers.
