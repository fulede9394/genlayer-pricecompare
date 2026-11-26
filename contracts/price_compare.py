# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import typing


class PriceCompare(gl.Contract):
    """
    PriceCompare - which of these two listings is cheaper
    right now?

    A shopping agent, a deal hunter or a procurement bot keeps
    asking the same question: the same item is listed in two
    places, which one is cheaper right now? Prices move, pages
    show list prices next to sale prices, and a listing page
    is full of other products' prices in sidebars and
    "related items" sections. Reading the right price off two
    live pages and comparing them is a small job that still
    needs eyes, not a scraper pointed at one store's markup.

    This contract turns "listing A is cheaper than listing B"
    into a checkable on-chain record. The submitter fixes
    three things at submission time: a description of the
    item and the two listing URLs. Validators then read both
    live pages, find each page's main price for the item, and
    compare them.

    Consensus follows the comparative pattern. The LLM does
    not extract one field for code to compare against a stored
    claim; it compares the two prices itself and returns one
    line:

      VERDICT|REASON

    VERDICT is A_CHEAPER, B_CHEAPER, SAME_PRICE or
    CANNOT_COMPARE, and REASON names the two prices it found.
    The line is judged under prompt_comparative: two judgments
    are equivalent when they name the same cheaper side based
    on the same two prices, whatever the wording. Deterministic
    code then only parses the verdict word and stores the
    reason - it never re-reads the pages or redoes the
    comparison.

    There is no dispute here and nobody wins anything: the
    two listings are not parties, they are price tags. The
    verdict is a price relation between two live pages at
    resolve time, recorded with the prices that produced it,
    so a later reader can see not just which side was cheaper
    but what the two prices actually were.
    """

    comparison_count: u256
    items: TreeMap[u256, str]
    urls_a: TreeMap[u256, str]
    urls_b: TreeMap[u256, str]
    statuses: TreeMap[u256, str]
    reasons: TreeMap[u256, str]

    PENDING = "PENDING"
    A_CHEAPER = "A_CHEAPER"
    B_CHEAPER = "B_CHEAPER"
    SAME_PRICE = "SAME_PRICE"
    CANNOT_COMPARE = "CANNOT_COMPARE"

    def __init__(self):
        self.comparison_count = u256(0)

    @gl.public.write
    def submit_comparison(
        self,
        item: str,
        url_a: str,
        url_b: str,
    ) -> int:
        item = item.strip()
        url_a = url_a.strip()
        url_b = url_b.strip()

        assert len(item) >= 3, "item description too short"
        assert len(item) <= 200, "item description too long"
        assert url_a.startswith("https://"), "URL A must be https"
        assert url_b.startswith("https://"), "URL B must be https"
        assert len(url_a) <= 300, "URL A too long"
        assert len(url_b) <= 300, "URL B too long"
        assert url_a != url_b, "the two listing URLs must differ"

        cid = self.comparison_count
        self.items[cid] = item
        self.urls_a[cid] = url_a
        self.urls_b[cid] = url_b
        self.statuses[cid] = self.PENDING
        self.reasons[cid] = ""
        self.comparison_count = cid + u256(1)
        return int(cid)

    @gl.public.write
    def resolve_comparison(self, comparison_id: int) -> str:
        cid = u256(comparison_id)
        assert cid in self.statuses, "unknown comparison"
        assert self.statuses[cid] == self.PENDING, "comparison already resolved"

        # Copy storage into locals: non-deterministic blocks may not
        # touch contract storage, they may only capture local values.
        item = self.items[cid]
        url_a = self.urls_a[cid]
        url_b = self.urls_b[cid]

        def judge_prices() -> str:
            page_a = gl.nondet.web.render(url_a, mode="text")
            page_b = gl.nondet.web.render(url_b, mode="text")
            prompt = f"""Compare the price of one item on two live listing pages, using only the pages below.

Item: {item}

On each page, find the main price of the page's own featured item - the price shown for the product the page is about, near the top of the page. Ignore prices of other products (related items, sidebars, recommendations) and ignore any second price that is only a tax breakdown of the main price.

--- Listing A ---
{page_a[:2500]}

--- Listing B ---
{page_b[:2500]}

Reply with exactly one line, nothing else, in this format:
VERDICT|REASON

VERDICT is one of:
A_CHEAPER - listing A's main price is lower than listing B's
B_CHEAPER - listing B's main price is lower than listing A's
SAME_PRICE - both pages show the same main price for the item
CANNOT_COMPARE - either page could not be read, or it shows no clear main price for the item

REASON names the two prices you found, for example: A shows £51.77 and B shows £53.74. Compare prices only when both pages price the item in the same currency; if the currencies differ and no conversion is possible from the pages, use CANNOT_COMPARE."""
            return gl.nondet.exec_prompt(prompt).strip()

        line = gl.eq_principle.prompt_comparative(
            judge_prices,
            principle="Two judgments are equivalent when they name the same cheaper side (or the same tie, or the same cannot-compare outcome) based on the same two main prices. Different wording or price formatting does not make them different.",
        )

        # Deterministic parsing only: the verdict word is taken
        # from the agreed line, the reason is stored for audit.
        first_sep = line.find("|")
        if first_sep == -1:
            verdict_word = line.strip().upper()
            reason = ""
        else:
            verdict_word = line[:first_sep].strip().upper()
            rest = line[first_sep + 1:]
            reason = rest.strip()
        self.reasons[cid] = reason

        if verdict_word == "A_CHEAPER":
            final = self.A_CHEAPER
        elif verdict_word == "B_CHEAPER":
            final = self.B_CHEAPER
        elif verdict_word == "SAME_PRICE":
            final = self.SAME_PRICE
        else:
            final = self.CANNOT_COMPARE

        self.statuses[cid] = final
        return final

    @gl.public.view
    def get_comparison(self, comparison_id: int) -> typing.Any:
        cid = u256(comparison_id)
        assert cid in self.statuses, "unknown comparison"
        return {
            "id": comparison_id,
            "item": self.items[cid],
            "url_a": self.urls_a[cid],
            "url_b": self.urls_b[cid],
            "status": self.statuses[cid],
            "reason": self.reasons[cid],
        }

    @gl.public.view
    def get_status(self, comparison_id: int) -> str:
        cid = u256(comparison_id)
        assert cid in self.statuses, "unknown comparison"
        return self.statuses[cid]

    @gl.public.view
    def get_comparison_count(self) -> int:
        return int(self.comparison_count)
