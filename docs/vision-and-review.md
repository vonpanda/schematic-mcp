# PDF/image extraction and engineering review

This workflow turns a drawing into reusable component/pin/net JSON through a vision LLM API, then generates evidence-linked electrical review findings. Native KiCad input still uses the deterministic parser without a network request.

## Install and configure

```sh
python -m pip install -e '.[vision]'
export SCHEMATIC_LLM_BASE_URL='https://api.openai.com/v1'
export SCHEMATIC_LLM_MODEL='YOUR_VISION_CAPABLE_MODEL'
# Configure SCHEMATIC_LLM_API_KEY through your local secret manager or environment.
# Do not commit credentials or proprietary drawings.
```

The model must accept image inputs and Chat Completions. The default response format is strict `json_schema`. For a compatible service that only supports JSON mode, explicitly set `SCHEMATIC_LLM_RESPONSE_FORMAT=json_object`; the same local schema and graph validation still applies. There is no silent downgrade or fallback to another provider. Services that require the older output-token parameter can use `SCHEMATIC_LLM_TOKEN_PARAMETER=max_tokens` (default: `max_completion_tokens`). Anthropic-native Messages, Gemini-native generateContent and Azure-specific authentication are not implemented; use a compatible endpoint or add a separately tested adapter.

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `SCHEMATIC_LLM_MODEL` | required | Explicit vision-capable model; no model is silently selected |
| `SCHEMATIC_LLM_API_KEY` | required | Bearer credential; excluded from config repr and provider errors |
| `SCHEMATIC_LLM_BASE_URL` | `https://api.openai.com/v1` | API root; `/chat/completions` is appended |
| `SCHEMATIC_LLM_RESPONSE_FORMAT` | `json_schema` | `json_schema` or explicit `json_object` |
| `SCHEMATIC_LLM_TOKEN_PARAMETER` | `max_completion_tokens` | Can explicitly select `max_tokens` for compatible services |
| `SCHEMATIC_LLM_MAX_TOKENS` | `16000` | Output limit per call, allowed 256–64000 |
| `SCHEMATIC_LLM_TIMEOUT` | `120` | HTTP operation timeout in seconds, allowed 1–600 |
| `SCHEMATIC_LLM_RETRIES` | `2` | Retry transient network, 429 and selected 5xx errors, allowed 0–3 |

Only HTTPS is accepted except HTTP on `localhost`, `127.0.0.1` or `::1` for local inference. Provider redirects are not followed. Provider error bodies, credentials and images are not echoed in errors. A local service without authentication can use a non-secret dummy bearer value if its compatibility interface accepts one.

## Command line: extract, review, export, reopen

```sh
# Native KiCad: fully local, no API configuration required.
schematic-review examples/minimal.kicad_sch --output ./native-report

# PDF / PNG / JPEG / WebP: explicitly send drawing images to the configured API.
schematic-review board.pdf --vision --output ./board-report

# Also request LLM review of the structured model.
schematic-review board.pdf --vision --llm-review --output ./board-ai-report

# Select one-based PDF pages. Reports warn that other pages are not covered.
schematic-review board.pdf --vision --pages 2 3 --output ./selected-report

# Reopen an exported or manually corrected model without another extraction call.
schematic-review board-report/model.json --output ./offline-review
```

Every successful run writes `model.json`, `review.json` and `review.md`. The output directory must be new; existing artifacts are not overwritten. The CLI reserves the directory before a billable request. If extraction fails, it exits 1 and the reserved directory may be empty. If optional LLM review fails, it exits 1 but preserves the model and completed local review. Exit 0 means the workflow completed, **not** that the design passed electrical review. Inspect the report summary and limitations.

Imported JSON is always `unverified`, even if its contents claim native-parser provenance. Graph consistency checks reject duplicate references/pins/nets, nonexistent endpoints and nonreciprocal pin/net assignments. Manual edits can be reviewed offline; they do not automatically acquire source-resolved trust.

## MCP tools

- `open_schematic(path)`: existing native KiCad workflow, no API call.
- `extract_schematic(path, pages=None)`: explicit remote drawing extraction; replaces the loaded graph only after all selected pages succeed.
- `open_schematic_model(path)`: local validated JSON import; no API call.
- `review_schematic()`: local deterministic electrical rules.
- `review_schematic_with_llm()`: explicit remote model review with validated endpoint citations.
- Existing component, pin, net, signal trace and MCU tools work on either graph and return `connectivity_status`.
- `schematic://current/model`: full exportable model including schema version, evidence and provenance.

`extract_schematic` and `review_schematic_with_llm` are annotated as open-world, non-idempotent tools because they transmit data and can incur charges. Native/query/import/local-review tools remain local. `SCHEMATIC_MCP_ROOT` / `--root` restrictions apply to PDF, images and model JSON as well as KiCad.

A workspace is a single shared current document per server process. State publication is atomic; readers see a consistent model/graph pair and failed extraction retains the previous pair. Concurrent successful opens have last-completion-wins semantics. Run a separate process per independent user/project; this is not a multi-tenant document store. Do not expose the unauthenticated HTTP transport publicly.

## Structured data contract

The extraction schema is in `schemas/page-extraction.schema.json` and is generated from `parsers/vision_schema.py`. Each page returns:

- A `1.0` schema version, model-declared coverage (`complete`, `partial`, `unreadable`) and explicit warnings.
- Components with reference, value, optional-as-empty library ID, visible physical pins and evidence.
- Pins with number, name, electrical type, page-local `net_id` or null, explicit NC marker and evidence.
- Nets with an ID, display name, labels, explicit local/global/unknown scope and evidence.
- Evidence with whole-page normalized rectangle (`x0`, `y0`, `x1`, `y1`), observation and model-reported confidence.

All schema fields are required; nullable/empty values represent unknowns. Unsupported keys, malformed JSON, invalid boxes, non-finite scores, duplicate physical pins/references/net IDs and dangling net references fail closed. A visible NC marker attached to a wire is preserved as a reviewable contradiction, not erased by validation. Model refusal and truncated output never become a partial successful graph.

The canonical model adds:

- `schema_version: "1.0"` and `connectivity_status` at the top level.
- Page-qualified references such as `P2/U1`; the original reference remains in `properties.source_reference`.
- Names such as `P2/n1:RESET`; identical local labels on different pages are not merged. Distinct IDs with the same displayed label also remain separate.
- Only explicitly global labels form candidate `GLOBAL/<name>` nets across pages. These remain unverified.
- Evidence with page numbers on components, pins and nets.
- Source SHA-256 of the exact byte snapshot rendered, model, prompt version, selected pages, per-page claimed coverage and returned token usage. Confidence is explicitly uncalibrated.

Physical identity of multi-page/multi-unit components and hierarchical port instances is **not** resolved by the vision adapter. Page-qualified symbols remain separate. Ordinary off-page arrows are not assumed global. Review reports disclose this boundary. The offline native KiCad parser remains root-sheet-only; the separate KiCad CLI XML-netlist path resolves full project connectivity.

## What review checks

| Rule | Trigger | Interpretation |
| --- | --- | --- |
| `OUTPUT_CONFLICT` | Multiple `output` pins on one net | Check drive contention and whether pin types are correct |
| `POWER_OUTPUT_CONFLICT` | Multiple physical `power_out` pins | Check permitted parallel operation; KiCad `power:PWR_FLAG` excluded |
| `NC_CONNECTED` | Explicit NC marker/type and a net | Inspect contradictory marker/wiring |
| `UNRESOLVED_INPUT` | Input or power input lacks a net and an intentional NC marker | Check source drawing and extraction completeness |
| `INPUT_ONLY_NET` | All represented endpoints are `input` | Check missing driver, hierarchy or external connection |
| `ISOLATED_POWER_INPUT` | One `power_in` endpoint alone on its net | Check missing supply and sheet coverage |

Open-collector, open-emitter, bidirectional and tri-state buses are not incorrectly treated as multiple push-pull outputs. Missing/unspecified electrical types reduce coverage. The extraction prompt prohibits guessing types from remembered datasheets, so many PDF pins legitimately have unknown types and driver rules cannot evaluate them.

LLM review adds hypotheses with exact existing endpoint IDs, recommendations and missing information. Nonexistent or ambiguous citations reject the remote result. Citations prove that the named endpoint exists in the model; they do **not** prove that the model's reasoning or visual interpretation is correct. Local evidence records are attached by the application rather than invented by the reviewer.

Reports always remain `needs_engineering_review`, including reports with zero findings. No datasheet retrieval, quantitative voltage/current rating check, analog simulation, timing validation or layout review is claimed. Supply requirements, BOM ratings and device datasheets are needed to extend those checks reliably.

## Resource bounds and failure behavior

PDFs are rendered locally using PDFium at up to 200 DPI and 32 megapixels/page. Each call includes a 2048-pixel overview and up to 16 overlapping detail crops when needed. This preserves more small-text and wire context than sending only a reduced full page, but image resolution and model vision limits still affect results. Images support EXIF orientation correction; multi-frame images are rejected.

Maximum input is 40 MiB, 40 selected pages, 32 megapixels for raster images, 8 MiB provider response and 1 MiB serialized input to LLM review. Oversized/invalid page selections fail explicitly; documents are never silently shortened. A provider may have lower payload/context limits; configure a smaller page selection or split the source. Retried calls can incur additional cost. No automatic cache or background network activity is used. Optional vision dependencies are Pillow (MIT-CMU) and pypdfium2/PDFium (per their bundled Apache/BSD notices); they are reused as packages rather than vendored.

## Validation and release gate

Offline tests exercise real image/PDF rendering, JSON contracts, synthetic HTTP-provider requests, CLI subprocess exports/reimports, real MCP stdio, fault recovery, boundary escapes, review rules and uncertainty propagation. Synthetic provider responses establish transport/application correctness only.

Before claiming a supported provider/model or production extraction quality, configure the intended real API and run an explicitly redistributable labeled schematic corpus with clean pages, dense pages, crossings/junctions, NC conflicts, multi-page scopes and known defects. Compare component identity, pin numbers, net membership and evidence locations against human-reviewed ground truth; measure false positives, false negatives, latency and API usage. Record the exact model/version and document hashes. This repository does not yet claim real-model accuracy or complete EDA/ERC coverage.

Protocol references: [OpenAI image inputs](https://developers.openai.com/api/docs/guides/images-vision) and [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs). Compatible provider behavior must be validated separately.
