# PriceCompare — Two-Listing Price Comparison Primitive

A standalone Intelligent Contract that attests which of two
live listings is cheaper right now, instead of trusting a
screenshot or a stale scrape.

## Deployed

- Network: StudioNet (GenLayer Studio)
- Contract: 0x8B8b94F3ee5C466E60D0dbc7779BEeDe2276e50e
- Deploy tx: 0x20589e4bab0779b1bc9f96fcb3c35c272e1dea190feb3b54144aad3774c63d4e
- Explorer: https://explorer-studio.genlayer.com/address/0x8B8b94F3ee5C466E60D0dbc7779BEeDe2276e50e

Smoke tests on this deployment (all as expected):
`A_CHEAPER` for £51.77 vs £53.74 — the £51.77 shown in page
B's related-products section was correctly ignored;
`B_CHEAPER` with the pages swapped; `CANNOT_COMPARE` against
a page with no price.

## Why this exists

The same item is listed in two places, and the question is
always the same: which one is cheaper right now? Prices move,
pages show list prices next to sale prices, and a listing
page is full of other products' prices in sidebars and
"related items" sections. PriceCompare turns "listing A is
cheaper than listing B" into a reusable primitive with a
visible audit trail.

1. `submit_comparison(item, url_a, url_b)` — the item
   description and the two listing URLs are fixed at
   submission time.
2. `resolve_comparison(comparison_id)` — validators read both
   live pages, find each page's main price for the item, and
   compare them. The LLM compares; it does not extract one
   field for code to check against a stored claim.
3. The verdict is `A_CHEAPER`, `B_CHEAPER`, `SAME_PRICE` or
   `CANNOT_COMPARE`, and the reason — which names the two
   prices found — is stored on-chain for audit.

There is no dispute here and nobody wins anything: the two
listings are not parties, they are price tags. The verdict is
a price relation between two live pages at resolve time.

## Comparison, not extraction

The LLM returns one line, `VERDICT|REASON`, judged under
prompt_comparative: two judgments are equivalent when they
name the same cheaper side based on the same two main
prices, whatever the wording. Deterministic code then only
parses the verdict word — it never re-reads the pages or
redoes the comparison. A page with no clear main price is
`CANNOT_COMPARE`, not a guessed loser.

## State design

One-way state machine per comparison:
`PENDING -> A_CHEAPER | B_CHEAPER | SAME_PRICE | CANNOT_COMPARE`

- `A_CHEAPER` / `B_CHEAPER`: that listing's main price for
  the item is lower.
- `SAME_PRICE`: both pages show the same main price.
- `CANNOT_COMPARE`: a page could not be read, shows no clear
  main price, or the two prices are in different currencies
  with no conversion possible from the pages.

Because the reason names both prices, anyone can see what
the comparison was actually made on, instead of getting a
single opaque word.

## Try it in GenLayer Studio

1. Paste `contracts/price_compare.py` into Studio and deploy (no args).
2. `submit_comparison` with, for example:
   - item: `the book featured on each page`
   - url_a: `https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html`
   - url_b: `https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html`
3. `resolve_comparison(0)`, then `get_comparison(0)` — expect
   `A_CHEAPER` (£51.77 vs £53.74).

## Tests

See `tests/test_cases.md` (9 cases): input validation, unknown /
double resolution, and three of the four terminal states
(`SAME_PRICE` is a possible outcome but no live test forces it).
