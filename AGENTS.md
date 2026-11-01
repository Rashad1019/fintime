# Investor Agents

Fincent's ticker page runs a ticker's real computed numbers (ratios, DCF, risk) past 16 investor personas, each modeled on a real investor's published framework. Full system prompts live in `agents/personas.py`.

## Classic value

| Persona | Framework |
|---|---|
| **Warren Buffett** | Wonderful businesses at fair prices — moats, high ROE, honest management, margin of safety. Treats a stock as part-ownership of a business. |
| **Benjamin Graham** | Strict quantitative value — low P/E and P/B, conservative debt, margin of safety. Treats the market as manic "Mr. Market" to exploit, not follow. |
| **Joel Greenblatt** | Systematic "magic formula" — high earnings yield combined with high return on capital, plus special situations like spinoffs. |

## Growth & quality

| Persona | Framework |
|---|---|
| **Peter Lynch** | Growth-at-a-reasonable-price (PEG ratio) — understandable businesses, plain-language reasoning, wary of "diworsification." |
| **Howard Marks** | Second-level thinking and market cycles — is the good news already in the price? Risk means permanent loss, not volatility. |

## Contrarian & macro

| Persona | Framework |
|---|---|
| **Michael Burry** | Contrarian deep value — exhaustive research into securities the market hates, anchored strictly on cash flow and balance-sheet reality. |
| **Ray Dalio** | Macro and debt cycles — stress-tests positions across growth/inflation regimes, prizes diversification and radical transparency. |

## Tech, AI & disruptive growth

| Persona | Framework |
|---|---|
| **Cathie Wood** | Disruptive innovation (ARK) — AI, robotics, genomics; values 5+ years out, accepts high volatility for exponential platforms. |

## Dividends and indexing

| Persona | Framework |
|---|---|
| **Jack Bogle** | Low-cost indexing — picking stocks is a loser's game after fees; weighs any single stock against just owning the whole market. |
| **Geraldine Weiss** | Dividend-yield theory — judges blue chips by decades of uninterrupted, growing dividends; a stock with no dividend is speculation. |

## ETFs

| Persona | Framework |
|---|---|
| **Rick Ferri** | Core-4 portfolios — a few cheap funds for different jobs (U.S. stocks, international stocks, bonds, real estate). Overlap and high fees fail the test. |
| **Paul Merriman** | Ultimate Buy and Hold — equity sliced by size, value, country, and real estate, held for decades. |
| **Dave Nadig** | ETF structure — what the fund holds, how the exposure is built, what it costs, and whether the name matches the mechanism. |
| **Daniel Sotiroff** | Income funds — dividend-growth funds keep the upside; covered-call funds pay more now because they sell it. |

## Modern / community voices

| Persona | Framework |
|---|---|
| **Ian Dunlap** ("The Master Investor") | "2 tech, 2 index, no stress" — concentrate in elite category winners (e.g. Apple, Microsoft) plus broad index funds (VOO, VTI); hold 5–10 years. |
| **Wall Street Trapper** (Leon Howard) | Ownership over consumption — own shares in the companies people spend with daily; builds wealth one share at a time, plain-language teaching. |

---

Every persona receives the same prompt: the ticker's real price, ratios, DCF value, and risk metrics, with an explicit instruction to reason only from the numbers given (missing data shown as N/A) rather than invent figures. See `agents/personas.py` for the full system prompts and `persona_panel.py` for how they're invoked.
