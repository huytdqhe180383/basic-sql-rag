import json
import os
import sys

from dotenv import load_dotenv

# Add parent to path to import pipeline
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from db_config import get_postgres_connection_kwargs
from pipeline import ask_database
import psycopg2

VIETNAMESE_TRANSLATIONS = {
    1: "CÃ³ bao nhiÃªu Ä‘Æ¡n hÃ ng Ä‘Ã£ Ä‘Æ°á»£c hoÃ n tiá»n trong nÄƒm 2017 vÃ  thÃ nh phá»‘ nÃ o cÃ³ nhiá»u Ä‘Æ¡n bá»‹ há»§y nháº¥t?",
    2: "Cho tÃ´i biáº¿t 3 sáº£n pháº©m cÃ³ lá»£i nhuáº­n cao nháº¥t (tá»•ng doanh thu trá»« Ä‘i giÃ¡ vá»‘n) tá»« trÆ°á»›c Ä‘áº¿n nay, nhÆ°ng loáº¡i trá»« nhá»¯ng máº·t hÃ ng hiá»‡n Ä‘ang bá»‹ Ä‘Ã¡nh dáº¥u lÃ  tá»“n kho quÃ¡ má»©c (overstock).",
    3: "ChÃºng ta cÃ³ thÃªm nhiá»u ngÆ°á»i má»›i tá»« máº¡ng xÃ£ há»™i (social media) hay tÃ¬m kiáº¿m tá»± nhiÃªn (organic search) hÆ¡n trong ná»­a Ä‘áº§u nÄƒm 2020? VÃ  tá»•ng giÃ¡ vá»‘n hÃ ng bÃ¡n (COGS) trong khoáº£ng thá»i gian Ä‘Ã³ lÃ  bao nhiÃªu?",
    4: "TÃ´i cáº§n biáº¿t khu vá»±c (region) mang láº¡i doanh thu cao nháº¥t qua apple pay trong nÄƒm 2022. NgoÃ i ra, sá»‘ ngÃ y cung cáº¥p trung bÃ¬nh (average days of supply) cho táº¥t cáº£ cÃ¡c sáº£n pháº©m vÃ o cuá»‘i nÄƒm 2022 lÃ  bao nhiÃªu?",
    5: "Liá»‡t kÃª top 2 thÃ nh phá»‘ nÆ¡i nam giá»›i mua nhiá»u Ä‘á»“ nháº¥t (tá»•ng sá»‘ lÆ°á»£ng) vÃ  tá»•ng doanh thu tÆ°Æ¡ng á»©ng tá»« khÃ¡ch hÃ ng nam.",
    6: "Hiá»ƒn thá»‹ sá»‘ láº§n chÃºng ta háº¿t hÃ ng Ä‘á»‘i vá»›i cÃ¡c sáº£n pháº©m trong danh má»¥c 'streetwear', nhÃ³m theo thÃ¡ng cá»§a nÄƒm 2022. Äá»“ng thá»i bao gá»“m tá»· lá»‡ Ä‘Ã¡p á»©ng (fill rate) trung bÃ¬nh cho nhá»¯ng máº·t hÃ ng Ä‘Ã³.",
    7: "KÃªnh thu hÃºt (acquisition channel) nÃ o mang láº¡i nhiá»u ngÆ°á»i mua hÃ ng báº±ng Apple Pay nháº¥t, vÃ  Ä‘á»™ tuá»•i phá»• biáº¿n nháº¥t cá»§a nhá»¯ng ngÆ°á»i mua cá»¥ thá»ƒ Ä‘Ã³ lÃ  gÃ¬?",
    8: "TÃ¬m quáº­n (district) cÃ³ tá»· lá»‡ hoÃ n tiá»n cao nháº¥t (Ä‘Æ¡n hÃ ng bá»‹ tráº£ láº¡i / tá»•ng sá»‘ Ä‘Æ¡n hÃ ng). ChÃºng ta Ä‘Ã£ máº¥t bao nhiÃªu doanh thu tá»« nhá»¯ng khoáº£n tráº£ láº¡i Ä‘Ã³?",
    9: "Tá»· lá»‡ bÃ¡n tháº³ng (sell-through rate) trung bÃ¬nh cá»§a danh má»¥c sáº£n pháº©m Ä‘Æ°á»£c giáº£m giÃ¡ máº¡nh nháº¥t trong láº§n chá»¥p tá»“n kho (inventory snapshot) Ä‘Æ°á»£c ghi nháº­n cuá»‘i cÃ¹ng lÃ  bao nhiÃªu?",
    10: "ChÃºng ta Ä‘ang xem xÃ©t nhá»¯ng ngÆ°á»i Ä‘Ã£ Ä‘Äƒng kÃ½ vÃ o nÄƒm 2018. Nguá»“n (source) nÃ o mang láº¡i cho chÃºng ta nhá»¯ng ngÆ°á»i mua trung thÃ nh nháº¥t (nhiá»u Ä‘Æ¡n hÃ ng nháº¥t má»—i ngÆ°á»i), vÃ  mÃ u sáº¯c Ä‘á»“ há» thÃ­ch mua nháº¥t lÃ  gÃ¬?"
}

def clean_rows(rows):
    clean = []
    for row in rows:
        clean_row = []
        for v in row:
            if isinstance(v, (int, float, str, bool)) or v is None:
                clean_row.append(str(v) if v is not None else None)
            else:
                clean_row.append(str(v))
        clean.append(clean_row)
    return clean

def evaluate_sql(sql):
    if not sql or sql.upper() == "CANNOT_GENERATE":
        return None, "No SQL generated"
    try:
        load_dotenv(override=True)
        conn = psycopg2.connect(**get_postgres_connection_kwargs(os.environ))
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql)
            if cur.description:
                rows = cur.fetchall()
                return clean_rows(rows), None
            return [], None
    except Exception as e:
        return None, str(e)

def run_tests():
    # Load test cases
    json_path = os.path.join(os.path.dirname(__file__), 'complex_test_cases.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        test_cases = json.load(f)

    results = []

    for tc in test_cases:
        tc_id = tc["id"]
        en_question = tc["question"]
        vn_question = VIETNAMESE_TRANSLATIONS[tc_id]

        expected_rows = []
        if tc["answer"] and "rows" in tc["answer"]:
            expected_rows = [[str(v) if v is not None else None for v in r] for r in tc["answer"]["rows"]]

        # 1. Evaluate English
        print(f"Running EN {tc_id}...")
        en_answer_str, en_sql = ask_database(en_question)
        en_rows, en_error = evaluate_sql(en_sql)
        en_passed = (en_rows == expected_rows) if en_error is None else False

        # 2. Evaluate Vietnamese
        print(f"Running VN {tc_id}...")
        vn_answer_str, vn_sql = ask_database(vn_question)
        vn_rows, vn_error = evaluate_sql(vn_sql)
        vn_passed = (vn_rows == expected_rows) if vn_error is None else False

        # Build result record
        results.append({
            "id": tc_id,
            "en_question": en_question,
            "vn_question": vn_question,
            "en_sql": en_sql,
            "vn_sql": vn_sql,
            "en_passed": en_passed,
            "vn_passed": vn_passed,
            "en_error": en_error,
            "vn_error": vn_error,
            "en_returned_rows": en_rows,
            "vn_returned_rows": vn_rows,
            "expected_rows": expected_rows,
            "consistent": (en_passed == vn_passed) and (en_rows == vn_rows)
        })

    # Save to tests/test results
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test results"))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "llm_evaluation_results.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\\nWrote results to {out_path}")

    # Calculate stats
    en_pass_count = sum(1 for r in results if r["en_passed"])
    vn_pass_count = sum(1 for r in results if r["vn_passed"])
    consistent_count = sum(1 for r in results if r["consistent"])

    print(f"EN Passed: {en_pass_count}/10")
    print(f"VN Passed: {vn_pass_count}/10")
    print(f"Consistent: {consistent_count}/10")

if __name__ == "__main__":
    run_tests()
