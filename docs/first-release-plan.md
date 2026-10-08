# First public reader and review release

## Product contract

An engineer can open a KiCad project, inspect the original pages, search every exported component and net, trace exact pin connections through the full hierarchy, run both this project's rule review and KiCad ERC, and share an offline evidence bundle. PDF/image intake remains explicit, remote, and unverified. No result represents engineering sign-off.

The core should stay format-neutral: EDA adapters produce a canonical electrical graph, the reader displays source pages and evidence, and skills guide the agent through intake, tracing and review. A future editor plugin should launch or link into this same review workflow rather than duplicate the graph and rules.

## Release gates

1. Merge the existing vision/review work after its own review, then rebase the reader branch. Verify the combined wheel, MCP transports and documentation against the release branch.
2. Validate the reader's interaction design in the locally deployed Penpot instance, then check its implementation in a browser on macOS, Windows and Linux. Verify page switching, component/net/finding navigation, zoom, text overflow, large projects and offline behavior.
3. Expand KiCad fixtures for repeated sheet instances, deep hierarchy, buses, multi-unit parts, aliases, NC markers, malformed XML, missing sheet paths and source changes during export. Verify cross-sheet nets against KiCad's netlist for each case.
4. Assemble a permissioned real-project acceptance set with human-reviewed component IDs, pins, net membership and defect labels. Track per-format extraction coverage, false connections, finding false positives/negatives, review time, latency and cost. Maintain a regression ledger for every corrected error.
5. Require every finding to show the exact source location, observed fact, inference and missing evidence. Review high-impact electrical rules against actual datasheets and part numbers before describing them as validated.
6. Run package and supply-chain checks, clean installation, MCP client interoperability, root/symlink boundaries, private-data redaction, docs examples and a source-to-report round trip. Keep the public release tagged only after these gates pass.

## Initial public story

Publish a short reproducible demonstration using a redistributable KiCad project and a known firmware pin mismatch. Show what native parsing verifies, what KiCad ERC reports, what this project's rules add, and which questions still require a hardware engineer. Include a second dense project to show performance and uncertainty boundaries.

Publish English and Chinese setup guides, a small rule catalog with false-positive notes, acceptance-corpus methodology, and contributor instructions for minimal fixtures. Compare capabilities against current KiCad ERC and other active open-source review tools using the same public projects before making superiority claims. Invite issue reports with a minimal licensed schematic and expected pin/net result.

## Current blockers

- The Penpot connector is configured locally but is not exposed to this task's callable tools, so the interaction design and visual QA have not been completed there.
- The existing vision/review PR is still a draft and this branch depends on it.
- The two public KiCad projects used for local compatibility checks have not been human-labeled for defect accuracy.
- The review rules cover a small subset of hardware risks. ERC counts from those projects are untriaged and must not be described as confirmed defects.
