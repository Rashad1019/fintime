# Investor Agents

Fincent's Agents page runs a ticker's real computed numbers (ratios, DCF, risk) past 20 investor personas, each modeled on a real investor's published framework. Full system prompts live in `agents/personas.py`.

## Classic value

| Persona | Framework |
|---|---|
| **Warren Buffett** | Wonderful businesses at fair prices — moats, high ROE, honest management, margin of safety. Treats a stock as part-ownership of a business. |
| **Charlie Munger** | Mental-model latticework and inversion — asks what would make an investment fail before asking why it works. Avoiding stupidity over seeking brilliance. |
| **Benjamin Graham** | Strict quantitative value — low P/E and P/B, conservative debt, margin of safety. Treats the market as manic "Mr. Market" to exploit, not follow. |
| **Seth Klarman** | Absolute value and risk-first thinking — deep discount to conservative (often liquidation) value, comfortable holding cash when nothing is cheap. |
| **Joel Greenblatt** | Systematic "magic formula" — high earnings yield combined with high return on capital, plus special situations like spinoffs. |
| **John Templeton** | Global contrarian — buys at maximum pessimism, sells at maximum optimism, hunts bargains worldwide. |

## Growth & quality

| Persona | Framework |
|---|---|
| **Peter Lynch** | Growth-at-a-reasonable-price (PEG ratio) — understandable businesses, plain-language reasoning, wary of "diworsification." |
| **Phil Fisher** | Long-runway growth via "scuttlebutt" research — outstanding products, R&D, management integrity; pays full price for exceptional companies. |
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
| **Masayoshi Son** | Vision-driven, bet-the-company on AI — 300-year view of technological evolution, enormous concentrated bets on category winners. |
| **Marc Andreessen** | Techno-optimist — software eating every industry, network effects, biggest risk is being under-invested in the future. |
| **Chamath Palihapitiya** | Asymmetric growth bets — huge TAMs, unit economics over current profit, concentrates capital when conviction is high. |

## ETF & dividend focused

| Persona | Framework |
|---|---|
| **Jack Bogle** | Low-cost indexing — picking stocks is a loser's game after fees; weighs any single stock against just owning the whole market. |
| **Geraldine Weiss** | Dividend-yield theory — judges blue chips by decades of uninterrupted, growing dividends; a stock with no dividend is speculation. |
| **Kevin O'Leary** | Cash-return discipline — "only own things that pay me," dividends and buybacks, strict position-sizing rules, zero patience for cash-burners. |

## Modern / community voices

| Persona | Framework |
|---|---|
| **Ian Dunlap** ("The Master Investor") | "2 tech, 2 index, no stress" — concentrate in elite category winners (e.g. Apple, Microsoft) plus broad index funds (VOO, VTI); hold 5–10 years. |
| **Wall Street Trapper** (Leon Howard) | Ownership over consumption — own shares in the companies people spend with daily; builds wealth one share at a time, plain-language teaching. |

---

Every persona receives the same prompt: the ticker's real price, ratios, DCF value, and risk metrics, with an explicit instruction to reason only from the numbers given (missing data shown as N/A) rather than invent figures. See `agents/personas.py` for the full system prompts and `pages/4_Agents.py` for how they're invoked.
