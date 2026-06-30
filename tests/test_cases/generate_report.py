import html
import json
import os


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Beacon Pipeline Evaluation Report</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333; line-height: 1.6; padding: 20px; }
        h1 { text-align: center; color: #2c3e50; margin-bottom: 40px; }
        .test-case { background: #fff; border-radius: 8px; padding: 20px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 6px solid #3498db; }
        .question { font-size: 1.2em; font-weight: bold; color: #2c3e50; margin-bottom: 15px; }
        .section { margin-top: 15px; padding-left: 15px; border-left: 3px solid #ecf0f1; }
        .section-title { font-weight: bold; color: #e67e22; }
        pre { background: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 5px; overflow-x: auto; font-size: 0.9em; }
        .answer { background: #e8f6f3; border: 1px solid #1abc9c; padding: 10px; border-radius: 5px; margin-top: 10px; white-space: pre-wrap; }
        .error { background: #fdedec; border: 1px solid #e74c3c; padding: 10px; border-radius: 5px; margin-top: 10px; color: #c0392b; }
        .analysis { margin-top: 15px; padding: 15px; background: #fdf2e9; border-radius: 5px; border: 1px solid #f39c12; }
        .status-badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; color: white; margin-bottom: 10px; }
        .status-completed { background-color: #27ae60; }
        .status-partial { background-color: #f39c12; }
        .status-failed { background-color: #c0392b; }
    </style>
</head>
<body>
    <h1>Beacon Pipeline Evaluation Report (English)</h1>
    <div id="content">
        {content}
    </div>
</body>
</html>
"""

QUESTIONS = {
    1: "How many order were refunded in 2017 and which city has the most canceled order?",
    2: "Tell me the 3 most profitable products (total revenue minus cogs) ever, but exclude items currently flagged as overstock.",
    3: "Did we get more new folks from social media or organic search in the first half of 2020? And what was the total COGS for that period?",
    4: "I need to know the region that brought in the most revenue via apple pay in 2022. Also, what was the average days of supply for all products at the end of 2022?",
    5: "List the top 2 cities where guys buy the most stuff (total quantity) and the corresponding total revenue from male customers.",
    6: "Show me how many times we ran out of stock for products in the 'streetwear' category, grouped by month of 2022. Also include the average fill rate for those items.",
    7: "Which acquisition channel brings in the most Apple Pay buyers, and what is the most common age bracket of those specific buyers?",
    8: "Find the district with the highest refund rate (returned orders / total orders). How much revenue did we lose to those returns?",
    9: "What is the average sell-through rate of the most heavily discounted product category during the last recorded inventory snapshot?",
    10: "We are looking at people who signed up in 2018. Which source gives us the most loyal buyers (most orders per person), and what color of clothing do they like to buy most?",
}


def render_attempts(section: dict) -> str:
    """Render compact retry details for one section."""
    attempts = section.get("attempts") or []
    if not attempts:
        return ""

    rows = []
    for index, attempt in enumerate(attempts, start=1):
        sql = html.escape(attempt.get("sql") or "")
        status = html.escape(str(attempt.get("status") or ""))
        error = html.escape(str(attempt.get("error") or ""))
        reason = html.escape(str(attempt.get("review_reason") or ""))
        rows.append(
            f"""
            <div class='section'>
                <div class='section-title'>Attempt {index}: {status}</div>
                <pre><code>{sql}</code></pre>
                <div>{reason}</div>
                <div class='error'>{error}</div>
            </div>
            """
        )
    return "\n".join(rows)


def generate_report():
    json_path = os.path.join(os.path.dirname(__file__), "..", "test_results", "master_plan_evaluation_results.json")
    if not os.path.exists(json_path):
        print("JSON results not found.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    content_html = ""

    for row in data:
        tc_id = row["id"]
        question = html.escape(QUESTIONS.get(tc_id, "Unknown Question"))
        en_ans = row["en_ans"]
        status = en_ans.get("status", "unknown")
        status_class = f"status-{status}"

        sections_html = ""
        for sec in en_ans.get("sections", []):
            sec_title = html.escape(sec.get("title", ""))
            sec_sql = html.escape(sec.get("sql") or "")
            sec_ans = html.escape(sec.get("answer") or "")
            sec_err = html.escape(str(sec.get("error") or ""))
            attempt_count = sec.get("attempt_count")

            sql_html = f"<pre><code>{sec_sql}</code></pre>" if sec_sql else ""
            ans_html = f"<div class='answer'><b>Response:</b><br>{sec_ans}</div>" if sec_ans else ""
            err_html = f"<div class='error'><b>Error:</b> {sec_err}</div>" if sec_err else ""

            sections_html += f"""
            <div class='section'>
                <div class='section-title'>Section: {sec_title}</div>
                <div>Attempts: {attempt_count}</div>
                {sql_html}
                {ans_html}
                {err_html}
                {render_attempts(sec)}
            </div>
            """

        content_html += f"""
        <div class='test-case'>
            <span class='status-badge {status_class}'>{html.escape(status.upper())}</span>
            <div class='question'>Q{tc_id}: {question}</div>
            <div class='sections'>
                {sections_html}
            </div>
            <div class='analysis'>
                <b>Note:</b> This report is generated from the latest JSON run. See docs/evaluation.md for the current accuracy notes.
            </div>
        </div>
        """

    final_html = HTML_TEMPLATE.replace("{content}", content_html)
    out_path = os.path.join(os.path.dirname(__file__), "..", "test_results", "report.html")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(final_html)

    print(f"Generated report at {out_path}")


if __name__ == "__main__":
    generate_report()
