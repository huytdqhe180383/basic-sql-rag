"""Minimal Gradio UI for Beacon."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import gradio as gr

from beacon.runtime.pipeline import ask_database


def handle_question(question: str) -> tuple[str, str]:
    """Run one UI question through the core pipeline."""
    if not question.strip():
        return "Please enter a question.", ""
    answer, sql = ask_database(question.strip())
    return answer, sql or ""


with gr.Blocks(title="Beacon - NL to SQL") as demo:
    gr.Markdown("# Beacon - Natural Language to SQL")
    question_box = gr.Textbox(label="Question", lines=2)
    submit_btn = gr.Button("Ask", variant="primary")
    answer_box = gr.Textbox(label="Answer", lines=10, interactive=False)
    sql_box = gr.Code(label="SQL", language="sql", interactive=False)
    submit_btn.click(handle_question, question_box, [answer_box, sql_box])
    question_box.submit(handle_question, question_box, [answer_box, sql_box])


def main() -> None:
    """Launch the UI."""
    demo.launch()


if __name__ == "__main__":
    main()
