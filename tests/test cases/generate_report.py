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
        .correct { color: #27ae60; font-weight: bold; }
        .wrong { color: #c0392b; font-weight: bold; }
        .partial { color: #f39c12; font-weight: bold; }
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
    10: "We are looking at people who signed up in 2018. Which source gives us the most loyal buyers (most orders per person), and what color of clothing do they like to buy most?"
}

ANALYSIS = {
    1: "<span class='correct'>Correct.</span> The pipeline successfully mapped 'refunded' to `order_status = 'returned'` thanks to the new metadata grounding layer. It also correctly split the independent intent (canceled city) into its own SQL query, joining the geography table securely.",
    2: "<span class='correct'>Correct.</span> The pipeline correctly identified 'profitable' as `SUM(oi.quantity * oi.unit_price - oi.discount_amount - (p.cogs * oi.quantity))` and correctly filtered out `overstock` flags from the inventory snapshot.",
    3: "<span class='partial'>Partial.</span> The first section correctly compares signup sources. However, the second section ('total COGS for that period') failed safely because it lost the context of 'that period' (first half of 2020). The pipeline successfully blocked returning an inaccurate guess.",
    4: "<span class='correct'>Correct.</span> The pipeline correctly split the intents. It accurately joined geography and order_items to sum revenue for Apple Pay in 2022. It accurately pulled the `days_of_supply` metric from the inventory table.",
    5: "<span class='correct'>Correct.</span> The query accurately maps 'guys' to male customers, joins across customers, orders, order_items, and geography, and correctly ranks by total quantity and outputs corresponding revenue.",
    6: "<span class='correct'>Correct.</span> A brilliant query. It successfully handles grouping by month, accurately filtering for 'streetwear' using a CTE or inline WHERE, and mathematically processes stockout events and fill rate averages perfectly.",
    7: "<span class='wrong'>Wrong (Context Loss).</span> Section 1 correctly identifies organic_search as the top channel for Apple Pay. However, Section 2 ('those specific buyers') drops the Apple Pay filter and returns the most common age bracket across the ENTIRE customer base. It failed to carry over the filter context.",
    8: "<span class='correct'>Correct.</span> A phenomenally accurate multi-CTE query. It calculates refund rate gracefully with `NULLIF` to prevent division-by-zero, and accurately calculates the revenue lost from order_items tied to the returned orders.",
    9: "<span class='correct'>Correct.</span> Thanks to the metadata grounding layer, the LLM correctly defined discount as `discount_amount / unit_price` (instead of hallucinating profit margin) to find the 'most heavily discounted' category, and successfully pulled the sell-through rate from the inventory snapshot.",
    10: "<span class='wrong'>Wrong (Context Loss).</span> Section 1 brilliantly calculated 'loyal buyers' as average orders per person for the 2018 cohort. However, Section 2 ('color of clothing do they like to buy most') completely dropped the 2018 cohort filter and just queried the most popular clothing color across the entire database."
}

def generate_report():
    json_path = os.path.join(os.path.dirname(__file__), '..', 'test results', 'master_plan_evaluation_results.json')
    if not os.path.exists(json_path):
        print("JSON results not found.")
        return
        
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    content_html = ""
    
    for row in data:
        tc_id = row['id']
        question = QUESTIONS.get(tc_id, "Unknown Question")
        analysis = ANALYSIS.get(tc_id, "No analysis available.")
        en_ans = row['en_ans']
        status = en_ans.get('status', 'unknown')
        
        status_class = f"status-{status}"
        
        sections_html = ""
        for sec in en_ans.get('sections', []):
            sec_title = sec.get('title', '')
            sec_sql = sec.get('sql')
            sec_ans = sec.get('answer', '')
            sec_err = sec.get('error')
            
            sql_html = f"<pre><code>{sec_sql}</code></pre>" if sec_sql else ""
            ans_html = f"<div class='answer'><b>Response:</b><br>{sec_ans}</div>" if sec_ans else ""
            err_html = f"<div class='error'><b>Error:</b> {sec_err}</div>" if sec_err else ""
            
            sections_html += f"""
            <div class='section'>
                <div class='section-title'>Section: {sec_title}</div>
                {sql_html}
                {ans_html}
                {err_html}
            </div>
            """
            
        content_html += f"""
        <div class='test-case'>
            <span class='status-badge {status_class}'>{status.upper()}</span>
            <div class='question'>Q{tc_id}: {question}</div>
            <div class='sections'>
                {sections_html}
            </div>
            <div class='analysis'>
                <b>Analysis:</b> {analysis}
            </div>
        </div>
        """
        
    final_html = HTML_TEMPLATE.replace("{content}", content_html)
    out_path = os.path.join(os.path.dirname(__file__), '..', 'test results', 'report.html')
    
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
        
    print(f"Generated report at {out_path}")

if __name__ == "__main__":
    generate_report()
