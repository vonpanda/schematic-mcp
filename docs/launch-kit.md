# Public launch kit (draft until a release tag exists)

## Claim to demonstrate

An open-source, local-first review workspace can open a KiCad hierarchy, preserve KiCad's exact pin/net graph, show the original pages, separate KiCad ERC from its own review rules, and attach exact-MPN datasheet evidence when a local manifest is supplied. PDF/image extraction and LLM review are explicit opt-in paths with unverified results. The tool assists engineers; it does not approve a design.

Every public example should link to one tagged commit, one redistributable input project, an exact command, the generated output, and a table of known limitations. Show the same workflow without an API key first; show remote extraction separately with cost/privacy notes. Do not claim defect-detection accuracy, superiority or production sign-off until a human-labeled evaluation supports it.

## Assets needed before posting

- A release tag, changelog and installation path verified from a clean environment on macOS, Linux and Windows.
- A short screen recording or annotated screenshots of page navigation, net tracing, a source-linked finding, KiCad ERC, and the component knowledge panel. Use only drawings licensed for redistribution.
- One reproducible small example and one dense full-project example with confirmed license and human-checked expected results. Report input hash, KiCad version, reader generation time and unresolved positions.
- An issue template asking for KiCad version, a minimal redistributable schematic, expected pin/net behavior, actual result and privacy confirmation. Never request a proprietary board in a public issue.
- A `good first issue` list for format adapters, documentation, rule evidence, UI accessibility and benchmark labeling. Start with narrowly scoped tasks and review contributor PRs promptly.

## Community sequence

1. Publish the GitHub release and documentation, then invite a small number of hardware engineers to reproduce the demo and file correctness issues. Respond to corrections with source evidence and a regression case.
2. Post a technical walkthrough in the [KiCad.info Projects category](https://forum.kicad.info/c/projects/9), focused on the exact KiCad workflow and limits. [KiCad's forum directory](https://www.kicad.org/community/forums/) also lists the KiCad subreddit, EEVblog KiCad section and a Chinese KiCad community. Check each community's current posting rules before sharing there; tailor the example to the audience.
3. Consider [Show HN](https://news.ycombinator.com/showhn.html) only when a visitor can immediately run or inspect a real artifact. [HN guidelines](https://news.ycombinator.com/newsguidelines.html) ask posters not to submit generated text, so the project owner should write that post in their own words.
4. Avoid communities that prohibit self-promotion. For example, the [r/PrintedCircuitBoard posting rules](https://www.reddit.com/r/PrintedCircuitBoard/comments/zj6ac8/please_read_before_posting_especially_if_using_a/) prohibit promotion.

Track useful feedback rather than raw views: reproduction attempts, valid defect reports, first-time contributor PRs, repeat users, and where engineers abandon the workflow. Make each follow-up release demonstrate a corrected behavior or measured coverage improvement.

## KiCad forum draft, after release verification

> **Open-source schematic reader and evidence-linked review for KiCad projects — feedback wanted**
>
> I maintain `schematic-mcp`, a local-first tool that turns a KiCad schematic project into a searchable pin/net graph and an offline reader. It uses KiCad's exported netlist for the full hierarchy, shows the original schematic pages, and keeps KiCad ERC separate from its own review candidates. An optional local part manifest links exact MPNs to pinned datasheet pages. The outputs always require engineering review.
>
> The release includes a small redistributable example, commands to reproduce it, and documented limitations: [tagged release link], [demo link], [limitations link]. I would especially value corrections to hierarchical net mapping, source-location markers and the usefulness of the review evidence. A minimal licensed schematic plus the expected pin/net result is ideal for a bug report.

Replace the bracketed links only after the release and demo are live. Do not post this draft as though the release already exists.
