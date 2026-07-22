"""
CLI entry point.

Usage:
    python main.py --data data/sample_sales.csv --question "..." [--model gpt-4o-mini]
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from src.graph import build_graph, initial_state


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Governed multi-agent data-analysis pipeline")
    parser.add_argument("--data", required=True, help="Path to a CSV file")
    parser.add_argument("--question", required=True, help="Natural-language analysis question")
    parser.add_argument("--model", default="gpt-4o-mini", help="Chat model to use")
    parser.add_argument("--output-dir", default="outputs", help="Where to write report.md and trace.json")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY not set. Copy .env.example to .env and fill it in.")

    df = pd.read_csv(args.data)
    llm = ChatOpenAI(model=args.model, temperature=0)

    app = build_graph(llm)
    state = initial_state(args.question, df)

    print(f"Running pipeline on {args.data} with model={args.model} ...\n")
    final_state = app.invoke(state)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if final_state.get("halted_reason"):
        print(f"Run halted: {final_state['halted_reason']}")
    else:
        report_path = out_dir / "report.md"
        report_path.write_text(final_state["report"], encoding="utf-8")
        print(f"Report written to {report_path}")

    trace_path = out_dir / "trace.json"
    trace_path.write_text(json.dumps(final_state["trace"], indent=2, default=str), encoding="utf-8")
    print(f"Full run trace written to {trace_path}")


if __name__ == "__main__":
    main()
