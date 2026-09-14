# Public financial data index

A starter index of **real, publicly accessible institutional sources**, checked
on 2026-09-14. These links are discovery resources, not HOLCO customer files,
calibration results or a labelled benchmark. No source dataset is mirrored here.
Source truth, extraction quality and redistribution rights need separate review.

| Source | Access / format | Useful control exercise | Limits |
|---|---|---|---|
| [SEC Financial Statement and Notes Data Sets](https://www.sec.gov/data-research/sec-markets-data/financial-statement-notes-data-sets) | Public bulk datasets extracted from XBRL filings | Reconcile financial facts to filing, period, unit and statement context | As-filed data; amendments and extraction limitations matter. Not a set of validated agent answers. |
| [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | JSON; no API key; follow SEC automated-access policy | Company facts, submission lineage, duration versus point-in-time periods | The API does not support CORS; fiscal periods can differ from calendar frames. |
| [ECB euro reference exchange rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html) | CSV/XML time series; public reference publication | Currency, rate date and quoted-base checks | Informational rates; ECB discourages their use as transaction rates. They do not establish a bank's executed FX price. |
| [French State accounts 2025](https://www.budget.gouv.fr/documentation/comptes-letat/comptes-letat-2025) | Public PDF accounts, general trial balance and related reports | Trace a published aggregate to its statement and supporting balance | Public-sector accounting context. PDF extraction requires validation; no ready-made FEC or client calibration implied. |

## Add a source, without inventing a golden set

A contribution must identify publisher, direct URL, period, retrieval date,
format, access/rate constraints, applicable rights, transformation method and
relevant control IDs. Describe what was actually checked. A URL is not an immutable
capture: a later evaluation must retain the permitted bytes, SHA-256 and acquisition
manifest separately, then obtain an independent expected result.

Do not contribute private FECs, bank statements, customer lists, internal paths,
real-case calibrations or supposedly anonymised client data without a separate
publication review. The repository's MIT licence does not relicense external data.
