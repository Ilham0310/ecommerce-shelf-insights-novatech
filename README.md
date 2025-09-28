

### Analytical approach

* Parsed five inputs (inventory, catalog, ads, marketplace, competitor intel), cleaned missing values, and standardized fields into one schema to compare apples to apples across issues.
* Ran four checks: stock risk (low units vs. velocity), price undercuts (lost Buy Box/cheaper rivals), ad waste (spend high, conversion low), and content gaps (missing description), then merged results into a single table for review.
* Kept the workflow in two steps: analyze_shelf.py builds raw findings; rank_priority.py converts those findings into a ranked list by value at risk and urgency so the team can act fast.

### Discoveries

* Stock: A few fast-moving SKUs have very low FBA units, which puts them at risk of going offline in days if not replenished quickly, explaining sudden sales drops even when ads are running.
* Price: Some listings are priced above the Buy Box/lowest shelf price, causing share loss on Amazon and Walmart and pulling down revenue despite steady traffic.
* Ads: Several SKUs show ad spend above the median with conversion under 5%, pointing to wasted budget that doesn’t convert into sales and adds noise to revenue trends.
* Content: No description-level gaps were found in the current snapshot, so content is not a top driver of volatility this week, and can be deprioritized for now.

### Recommendations

* Urgent (next 24–48 hours): Raise POs for SKUs with days_to_stockout ≤ 2; enable FBM or move inventory if possible; enforce MAP or short-term promos where Buy Box is lost.
* Near term (this week): Cap bids or pause low-conversion campaigns while testing better creatives/keywords; add alerts for days_to_stockout < 7 and price_gap > defined threshold per category.
* Ongoing: Automate weekly shelf scans; tie competitor_intelligence to pricing guardrails so undercuts trigger rules, not manual hunts.

### Assumptions

* velocity_score is treated as an approximate units/day signal; if missing, set to zero to avoid false urgency; days_to_stockout uses inventory ÷ velocity with a safe divide.
* Buy Box is considered “lost” if the winner is not NovaTech Official on Amazon; for Walmart, “lowest_competitor_price” is the reference for undercutting severity.
* Ad health uses a simple rule: spend above portfolio median and conversion < 5% flags waste; this is a triage line, not a full MMM/attribution view.
* Catalog file only exposes description text; images/bullets aren’t present, so content checks are limited to what exists in the data today.

### AI usage disclosure

* Used an assistant to bootstrap file I/O scaffolding and outline this README, then rewrote logic for cleaning, edge cases, and scoring to fit the data, the brief, and the two-step workflow; prompts and edits are documented in PROMPTS.md to keep the process transparent.
* All thresholds (e.g., 5% ad conversion) and scoring choices were reviewed and tuned manually so the output reads like a practical action list rather than a generic dump; the numbers can be adjusted via small code changes if team norms differ.

### Priority framework

* Value at risk estimates how much money a problem could cost in the near term, by pillar: stock (margin × velocity × expected offline days), price (relative gap scaled where revenue isn’t joined), ads (wasted spend vs. a 5% target), content (low constant until richer fields arrive).
* Urgency boosts problems that hit sooner, especially stockouts with very few days remaining; final priority_score = value_at_risk × urgency_factor and the report is sorted descending so the first rows are the fires to put out now.

### Future enhancements

* Enrich stock math with true unit margins from finance, and incorporate lead times to estimate exact lost days and lost revenue with more confidence; add retailer-level safety-stock rules.
* Join actual price elasticity and share-of-voice to price decisions so the undercut score reflects real revenue impact, not just the gap size; tie in event calendars like Prime days.
* Expand content checks to images, bullets, and A+ flags when those fields are available, and link content refresh tasks to ad tests for faster recovery on low-conversion SKUs.


