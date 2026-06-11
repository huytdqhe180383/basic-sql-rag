import gradio as gr
from pipeline import ask_database


def handle_question(question: str) -> tuple[str, str]:
    if not question.strip():
        return "Please enter a question.", ""
    answer, sql = ask_database(question.strip())
    return answer, sql or ""


with gr.Blocks(title="Beacon - NL to SQL") as demo:
    gr.Markdown("# Beacon — Natural Language to SQL")
    gr.Markdown("Ask questions about customers, orders, and order items in plain English.")

    question_box = gr.Textbox(
        label="Your Question",
        placeholder="e.g. How many orders were placed via mobile last month?",
        lines=2,
    )
    submit_btn = gr.Button("Ask", variant="primary")

    answer_box = gr.Textbox(label="Answer", lines=10, interactive=False)
    sql_box = gr.Code(label="SQL Query Executed", language="sql", interactive=False)

    submit_btn.click(
        fn=handle_question,
        inputs=question_box,
        outputs=[answer_box, sql_box],
    )
    question_box.submit(
        fn=handle_question,
        inputs=question_box,
        outputs=[answer_box, sql_box],
    )


if __name__ == "__main__":
    demo.launch()
