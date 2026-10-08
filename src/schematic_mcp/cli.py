"""Non-MCP extraction/review workflow with reusable JSON and Markdown exports."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from schematic_mcp.llm import JSONClient, LLMConfig
from schematic_mcp.review import markdown_report, review_schematic
from schematic_mcp.workspace import Workspace


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract and review a hardware schematic")
    parser.add_argument("path", help="KiCad schematic, or PDF/PNG/JPEG/WebP with --vision")
    parser.add_argument("--root", help="Restrict source reads to this directory")
    parser.add_argument("--vision", action="store_true", help="Explicitly send rendered input pages to configured LLM API")
    parser.add_argument("--project", action="store_true", help="Use KiCad CLI to resolve the complete project hierarchy")
    parser.add_argument("--llm-review", action="store_true", help="Also send the structured model to the configured LLM API")
    parser.add_argument("--pages", type=int, nargs="+", help="One-based PDF page selection; other pages remain unreviewed")
    parser.add_argument("--output", type=Path, required=True, help="New directory for model.json, review.json, review.md")
    args = parser.parse_args()
    try:
        if args.pages and not args.vision:
            raise ValueError("--pages requires --vision")
        if args.project and args.vision:
            raise ValueError("--project and --vision are mutually exclusive")
        # Reserve a new directory before any billable request; never overwrite artifacts.
        args.output.mkdir(parents=True, exist_ok=False)
        workspace = Workspace()
        if args.root:
            workspace.root = Path(args.root).expanduser().resolve()
        if args.vision:
            schematic = workspace.extract(args.path, args.pages)
        elif Path(args.path).suffix.lower() == ".json":
            schematic = workspace.open_model(args.path)
        elif args.project:
            schematic = workspace.open_project(args.path)
        else:
            schematic = workspace.open(args.path)
        (args.output / "model.json").write_text(json.dumps(schematic.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        # Always save deterministic results before an optional remote review can fail.
        report = review_schematic(schematic)
        for name, content in [("review.json", json.dumps(report, ensure_ascii=False, indent=2)), ("review.md", markdown_report(report))]:
            (args.output / name).write_text(content, encoding="utf-8")
        if args.llm_review:
            report = review_schematic(schematic, JSONClient(LLMConfig.from_env()))
            (args.output / "review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            (args.output / "review.md").write_text(markdown_report(report), encoding="utf-8")
        print(json.dumps({"ok": True, "output": str(args.output.resolve()), "summary": report["summary"], "status": report["status"]}))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
