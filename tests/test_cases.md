# PriceCompare — test cases

Run manually in GenLayer Studio after deploying
`contracts/price_compare.py` (no constructor args).

The live cases use the Books to Scrape sandbox
(books.toscrape.com), a stable demo bookstore whose pages each
carry one clear main price. The two pages feature different
books; the comparison under test is each page's main listed
price, which is exactly the mechanic the contract performs.

- Page A: https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html — main price £51.77
- Page B: https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html — main price £53.74

Note: page B also shows page A's book at £51.77 in a
"related products" section near the bottom. The judge prompt
instructs validators to use each page's own main price and
ignore related products, so this must not flip the verdict.

## Deterministic validation

1. `submit_comparison` with a non-https URL — expect rejection
   ("URL A must be https" / "URL B must be https").
2. `submit_comparison` with the same URL twice — expect
   rejection ("the two listing URLs must differ").
3. `submit_comparison` with an item description shorter than
   3 characters — expect rejection ("item description too short").
4. `submit_comparison("the book featured on each page", <page A>, <page B>)` — expect
   comparison id `0`, and `get_comparison_count()` returns `1`.
5. `get_status(99)` on an unknown comparison — expect rejection
   ("unknown comparison").
6. `resolve_comparison(99)` on an unknown comparison — expect
   rejection ("unknown comparison").

## Non-deterministic verdict paths

7. Resolve the comparison from case 4 — £51.77 (A) against
   £53.74 (B). Expect `A_CHEAPER`, with a reason naming both
   prices.
8. Submit the same two pages swapped — url_a is page B,
   url_b is page A — and resolve it. Expect `B_CHEAPER`.
9. Submit page A against `https://example.com` (a page with
   no price at all) and resolve it. Expect `CANNOT_COMPARE`.
10. Resolve an already-resolved comparison a second time —
    expect rejection ("comparison already resolved"). Prices
    move; a verdict stays with its own record, and a fresh
    check is a new comparison.
