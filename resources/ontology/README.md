# M1 pinned ontology slice

Revision-2 additions are separate from this legacy slice. `prompt-sources.json`
pins FIBO CurrencyAmount at the same commit, and `generated/taxonomy-v2.json`
inventories 932 terms, 35 formal restrictions and 66 unresolved imports from six
modules. `python -m intentlineage.taxonomy` reproduces the inventory. The actual
Payment/hasPaymentAmount/MonetaryAmount existential supplies one proposed checkable
typed-relation rule. Missing witnesses are unknown under open-world semantics;
neither preservation nor approval follows from ontology vocabulary. Proposed
operationalizations are in `resources/evidence/operationalizations-v2.json`.

`manifest.json` records immutable commits, original paths, SHA-256 hashes,
declaration lines, versions and licences. `upstream/` retains five unmodified
modules; `generated/slice.ttl` contains 18 selected declarations, their reachable
blank-node axioms and source ontology metadata (271 triples). Imports are retained
as references but are **not loaded**. Run from the project root:

```powershell
.\.venv\Scripts\python.exe -m intentlineage.ontology
```

ePO v5.2.0 is pinned to
[2276eb5](https://github.com/OP-TED/ePO/tree/2276eb5638bac5f66c80ec133bc6a24d0fdd5b76),
released in October 2025. ePayment supplies PaymentInformation, total payment
amount and invoice reference; eInvoicing supplies Invoice, Payee, payment-account
identifier, amount due and order reference. eOrdering supplies Order; core
supplies MonetaryValue, amount value and currency. These bindings describe
concepts/relationships; they do not prescribe our match, approval or preservation
rules. The modules do not define a Payment action or PaymentObligation class.

The minimal FIBO supplement is
[PaymentsAndSchedules at master_2026Q2](https://github.com/edmcouncil/fibo/blob/f59157fe156e3d91b1c045222d0a7dc06b7d78a2/FND/ProductsAndServices/PaymentsAndSchedules.rdf):
Payment, PaymentObligation, fulfillsObligation and Payee. The two Payee terms
illustrate ambiguity; unqualified `Payee` remains unresolved. No equivalence
axioms are invented between FIBO and ePO. Approval revision is explicitly local;
account-ownership proof is unresolved. P2P-O is reference only.

ePO ontology headers explicitly identify **EUPL 1.2**, whereas its README uses
CC BY 4.0 for documents. Original notices and the complete EUPL are preserved in
`licenses/epo-LICENSE`. The generated subset is an identified modification of
these modules; keep its source, upstream attribution, licence and modification
notice with any permitted redistribution. FIBO identifies MIT in both its module
and repository licence; preserve the EDM Council/OMG copyright and permission
notices. Engine MIT notices are also retained. This does not select the project's
publication licence; human review of the combined release remains a later task.

[Open Ontologies Lite's pinned Python documentation](https://github.com/fabio-rovai/open-ontologies/blob/c729e7a31da0a10886d3d832a3415ff66ffc9e5b/python/README.md)
exposes parse/validate, load, SPARQL query, conversion, lint and statistics, with
optional SHACL through pySHACL. We installed **0.5.0 with `[shacl]`** on Windows /
CPython 3.11.9. `generated/operations.json` records actual syntax rejection,
loading, declaration queries, subclass property-path traversal, declared versus
undeclared vocabulary, passing/failing SHACL and zero-focus abstention.

The [root Rust MCP/CLI documentation](https://github.com/fabio-rovai/open-ontologies/blob/c729e7a31da0a10886d3d832a3415ff66ffc9e5b/README.md)
offers analogous validate/query/load/SHACL commands and a larger surface, with
native Windows build guidance. Its CLI needs a separate binary/toolchain; it was
not installed or executed. The tested Python path meets M1's small operations
without that build. Do not infer parity from the shared name or claim full
OWL-DL consistency, resolved imports or business verification. The local SHACL
shape demonstrates required-property checking; it is not an upstream rule.
