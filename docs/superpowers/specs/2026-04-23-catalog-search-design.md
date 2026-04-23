# Catalog Search Design

## Summary

Add a local STAC catalog search layer that provides near-drop-in `pystac-client` search ergonomics for catalogs opened with `pystac.Catalog.from_file(...)`.

The primary goal is to let notebook and library users write code that feels like `Client.search(...)` even when the source is a static catalog with no `/search` endpoint. The implementation should optimize for one-off exploratory use, not repeated analytical workloads.

## Problem

`pystac-client.Client.search()` only works against STAC APIs that advertise the `ITEM_SEARCH` conformance class and expose a search endpoint. Static catalogs such as `nz-elevation` can be traversed with `pystac`, but they do not provide a built-in search abstraction with the same behavior or result interface.

Current limitations:

- Users can iterate collections and items recursively, but must write their own filtering and paging logic.
- `Client.open(...)` on a static catalog does not provide a working search fallback.
- One-off notebook exploration suffers from poor ergonomics compared with API-backed catalogs.

## Goals

- Provide a local search interface for `pystac.Catalog` with call patterns close to `Client.search(...)`.
- Reuse `pystac_client.ItemSearch` for result handling if feasible, rather than maintaining a parallel result object.
- Return a deferred search object with `ItemSearch`-like result methods:
  - `items()`
  - `items_as_dicts()`
  - `pages()`
  - `pages_as_dicts()`
  - `matched()`
  - `item_collection()`
  - `item_collection_as_dict()`
- Support the common search parameters needed for exploratory catalog queries:
  - `ids`
  - `collections`
  - `bbox`
  - `intersects`
  - `datetime`
  - `query`
  - `sortby`
  - `limit`
  - `max_items`
- Support filtering on key LINZ catalog metadata used in the notebook workflow:
  - `linz:region`
  - `linz:slug`
  - `linz:geospatial_category`
- Preserve lazy evaluation where possible so searches stream results instead of materializing the whole catalog by default.
- Warn clearly when a requested behavior is unsupported or only partially supported locally.

## Non-Goals

- Full STAC API conformance for local catalogs.
- Full CQL2 `filter` support in the initial version.
- Aggressive indexing, DuckDB materialization, or persistent local caches.
- Exact parity with remote API paging or conformance negotiation behavior.
- Collection search support.

## User Experience

The first target is notebook exploration. Users should be able to open a catalog from file and create a local search object without manually traversing the catalog.

Target usage:

```python
from pystac import Catalog
from linz_s3_utils.stac import search

catalog = Catalog.from_file(
    "https://nz-elevation.s3-ap-southeast-2.amazonaws.com/catalog.json"
)

item_search = search(
    catalog,
    collections=["01HQS6C8F88JGM04345RY84N9D"],
    bbox=[174.7, -36.95, 174.9, -36.8],
    datetime="2024-01-01/2024-12-31",
    sortby="-properties.created",
    limit=10,
)

list(item_search.items())
item_search.matched()
```

An optional follow-up ergonomic improvement is a wrapper or helper that exposes `.search(...)` as a method, but the initial implementation only needs one stable public entry point.

For the `nz-elevation` use case, the local search should make it straightforward to filter using LINZ-specific metadata currently inspected in the notebook, especially `linz:region`, `linz:slug`, and `linz:geospatial_category`.

## Recommended Public API

Expose a top-level helper:

```python
search(catalog: pystac.Catalog, **search_kwargs) -> pystac_client.ItemSearch
```

Fallback only if reuse is not viable:

```python
class CatalogSearch:
    ...
```

Rationale:

- A function is easier to adopt than monkey-patching `pystac.Catalog`.
- It avoids altering third-party classes or relying on inheritance around objects returned by `Catalog.from_file(...)`.
- It keeps the implementation local to this project and explicit in notebook usage.

If a method-like experience is still desired later, it can be added as a thin wrapper around the same implementation.

Result-object preference:

- Preferred: return a real `pystac_client.ItemSearch` wired to a local execution backend.
- Acceptable fallback: return a project-local search object only if `ItemSearch` cannot be reused cleanly without brittle monkey-patching or private-API coupling.

## Search Semantics

### Parameter Handling

The local search object should accept the same keyword arguments as `Client.search(...)` where practical. The initial implementation should parse and store:

- `method`
- `max_items`
- `limit`
- `ids`
- `collections`
- `bbox`
- `intersects`
- `datetime`
- `query`
- `filter`
- `filter_lang`
- `sortby`
- `fields`

Unsupported or partial parameters should not silently alter meaning.

Rules:

- `filter` and `filter_lang` are accepted for compatibility but only a minimal subset is supported in v1.
- `fields` is accepted for compatibility but may be ignored with a warning in v1.
- `method` is accepted for compatibility but has no behavioral effect for local search.

### Supported Filters

The initial version should support these locally:

- `ids`: exact item ID membership
- `collections`: exact collection ID membership
- `bbox`: item geometry or bbox intersection with the search bbox
- `intersects`: GeoJSON geometry intersection against item geometry or bbox
- `datetime`: overlap against item datetime or start/end datetime properties
- `query`: common comparison operators for flat and nested properties

Expected query support:

- equality
- inequality
- greater than
- greater than or equal
- less than
- less than or equal
- `in` if straightforward to support

Supported property paths should include top-level item fields and `properties.*` paths.
The implementation should also support the LINZ-specific fields `linz:region`, `linz:slug`, and `linz:geospatial_category`, even when they must be resolved from the parent collection metadata rather than the item payload itself.

### Partial or Unsupported Filters

The initial version should warn and degrade rather than fail when possible:

- `filter`:
  - if a simple JSON structure can be mapped directly onto the supported common subset, apply it
  - otherwise warn that full CQL2 is unsupported and skip that predicate
- `fields`:
  - warn that field projection is not enforced for object results
  - optionally apply projection only to `items_as_dicts()` and page dictionaries if this is cheap and safe

If a request mixes supported and unsupported predicates, the supported subset should still run and warnings should identify what was ignored.

## Result Behavior

The returned search object should behave like a deferred local query object.

### Execution Model

- Construction stores normalized parameters.
- No catalog traversal happens until a result method is called.
- Filtering runs as a streaming pass over `catalog.get_items(recursive=True)`.
- Sorting is deferred until needed and only materializes the matching subset when `sortby` is present.

### Result Methods

- `items()`: yields `pystac.Item`
- `items_as_dicts()`: yields item dictionaries
- `pages()`: yields `pystac.ItemCollection`
- `pages_as_dicts()`: yields FeatureCollection-like dictionaries with `features`
- `matched()`: returns the number of matched items
- `item_collection()`: returns a single `pystac.ItemCollection`
- `item_collection_as_dict()`: returns a single FeatureCollection-like dictionary

Behavior notes:

- `limit` should control page size.
- `max_items` should cap total returned items across all result methods.
- `matched()` should count matches before `max_items` truncation and may require a full local scan.
- Paging links such as `next` are not required in local page dictionaries.

## Components

### 1. `ItemSearch` Reuse Layer

The implementation should first attempt to reuse `pystac_client.ItemSearch` directly.

Preferred shape:

- construct an `ItemSearch` instance with normalized parameters
- provide a local backend that satisfies the methods `ItemSearch` expects for paging and counts
- keep the project-specific logic focused on local predicate evaluation, not on reimplementing the public result interface

This should only be rejected if the integration requires invasive monkey-patching or depends too heavily on unstable internals in `pystac-client`.

### 2. Parameter Normalizer

Reuse compatible formatting ideas from `pystac-client` where useful:

- normalize datetime input into a comparable range
- normalize `ids`, `collections`, `bbox`, and `sortby`
- normalize `query` into an internal predicate representation

This does not need to inherit from `pystac-client.ItemSearch`, but it should mirror its accepted argument shapes closely enough to make migration easy.

### 3. Predicate Evaluator

A small evaluator should determine whether a single item matches.

Responsibilities:

- resolve item values by path
- resolve collection-derived values by path when an item-level query depends on parent collection metadata
- derive comparable temporal extents from item properties
- derive geometry for spatial checks
- apply query comparisons consistently
- collect warnings about unsupported clauses

This evaluator should be independent from paging logic so it can be tested directly.

### 4. Local Search Backend

If `ItemSearch` is reused, the local backend should emulate the paging/count contract it needs without pretending to be a full remote STAC API.

Responsibilities:

- accept normalized local search parameters
- iterate items recursively from the catalog
- apply local predicates lazily
- produce FeatureCollection-like page dictionaries
- provide enough count behavior for `matched()`

### 5. Search Executor

The executor should:

- iterate items recursively from the catalog
- apply filter predicates lazily
- count total matches for `matched()`
- materialize only when sorting is requested
- chunk output into pages for page-oriented methods

### 6. Dict Conversion Layer

Object and dict result methods should share the same matching logic. Dict conversion should happen as late as possible to avoid unnecessary copying.

## Performance Strategy

The chosen workload is one-off exploration, so the design should avoid expensive upfront indexing.

### Initial Strategy

- No DuckDB initialization.
- No persistent cache.
- No full-catalog pre-scan at construction time.
- Stream items directly from `catalog.get_items(recursive=True)`.

### Low-Cost Optimizations

- Cache per-item derived values within a single execution pass if the same item is checked by multiple predicates.
- Short-circuit cheap predicates before expensive spatial checks.
- Only materialize all matches when `sortby` is requested.
- Use page-sized buffering for `pages()` and `pages_as_dicts()` when no sorting is requested.

### When to Revisit

Revisit indexing or DuckDB only if one of these becomes true:

- catalogs become large enough that a single scan is too slow for notebook use
- users repeatedly run many searches over the same in-memory catalog
- richer query semantics make ad hoc predicate evaluation too complex

If that happens later, the right next step is likely an optional in-memory metadata index, not a mandatory DuckDB dependency.

## Error Handling and Warnings

- Invalid parameter shapes should raise `ValueError`.
- Unsupported but ignorable semantics should emit `warnings.warn(...)`.
- Missing geometry, bbox, or datetime values should exclude the item from the relevant predicate unless the predicate can be evaluated another way.
- If `sortby` references a missing field, missing values should sort last rather than crash.

## Testing Strategy

Add unit tests around a synthetic in-memory catalog built from a few collections and items.

Minimum coverage:

- ID and collection filtering
- bbox filtering
- intersects filtering
- datetime filtering for single timestamps and ranges
- query comparisons on `properties.*`
- paging with `limit`
- truncation with `max_items`
- `matched()` counting before truncation
- sort ascending and descending
- warnings for unsupported `filter` and `fields`

Tests should avoid network access and should not depend on the external `nz-elevation` catalog.

## Open Decisions Resolved

- Compatibility target: near-drop-in `Client.search()` argument compatibility
- Primary workload: one-off exploration
- Unsupported semantics policy: support the common subset and warn on the rest
- Indexing strategy: defer indexing and DuckDB until real performance evidence justifies them

## Implementation Outline

1. Prototype reuse of `pystac_client.ItemSearch` with a local paging/count backend.
2. Implement parameter normalization and the common-subset predicate evaluator.
3. Implement the local backend for lazy item/page production.
4. Fall back to a project-local search object only if the `ItemSearch` reuse prototype proves too brittle.
5. Add tests covering supported filters, paging, truncation, sorting, warnings, and `ItemSearch` compatibility.
6. Add a short usage example to project documentation or notebook comments if needed.

## Risks

- Local search semantics may differ subtly from API-backed search for edge cases.
- CQL2 expectations may be higher than the supported v1 subset.
- Sorting requires materialization of matches, which may be slower on larger catalogs.
- `ItemSearch` reuse may rely on `pystac-client` internals that change across versions.

These risks are acceptable for the initial scope because the goal is exploratory usability rather than full API emulation.
