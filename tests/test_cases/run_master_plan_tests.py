import json
import os
import sys

# Add src directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))
from beacon.pipeline import answer_question

VIETNAMESE_TRANSLATIONS = {
    1: "Có bao nhiêu đơn hàng đã được hoàn tiền trong năm 2017 và thành phố nào có nhiều đơn bị hủy nhất?",
    2: "Cho tôi biết 3 sản phẩm có lợi nhuận cao nhất (tổng doanh thu trừ đi giá vốn) từ trước đến nay, nhưng loại trừ những mặt hàng hiện đang bị đánh dấu là tồn kho quá mức (overstock).",
    3: "Chúng ta có thêm nhiều người mới từ mạng xã hội (social media) hay tìm kiếm tự nhiên (organic search) hơn trong nửa đầu năm 2020? Và tổng giá vốn hàng bán (COGS) trong khoảng thời gian đó là bao nhiêu?",
    4: "Tôi cần biết khu vực (region) mang lại doanh thu cao nhất qua apple pay trong năm 2022. Ngoài ra, số ngày cung cấp trung bình (average days of supply) cho tất cả các sản phẩm vào cuối năm 2022 là bao nhiêu?",
    5: "Liệt kê top 2 thành phố nơi nam giới mua nhiều đồ nhất (tổng số lượng) và tổng doanh thu tương ứng từ khách hàng nam.",
    6: "Hiển thị số lần chúng ta hết hàng đối với các sản phẩm trong danh mục 'streetwear', nhóm theo tháng của năm 2022. Đồng thời bao gồm tỷ lệ đáp ứng (fill rate) trung bình cho những mặt hàng đó.",
    7: "Kênh thu hút (acquisition channel) nào mang lại nhiều người mua hàng bằng Apple Pay nhất, và độ tuổi phổ biến nhất của những người mua cụ thể đó là gì?",
    8: "Tìm quận (district) có tỷ lệ hoàn tiền cao nhất (đơn hàng bị trả lại / tổng số đơn hàng). Chúng ta đã mất bao nhiêu doanh thu từ những khoản trả lại đó?",
    9: "Tỷ lệ bán thẳng (sell-through rate) trung bình của danh mục sản phẩm được giảm giá mạnh nhất trong lần chụp tồn kho (inventory snapshot) được ghi nhận cuối cùng là bao nhiêu?",
    10: "Chúng ta đang xem xét những người đã đăng ký vào năm 2018. Nguồn (source) nào mang lại cho chúng ta những người mua trung thành nhất (nhiều đơn hàng nhất mỗi người), và màu sắc đồ họ thích mua nhất là gì?"
}

def run_tests():
    json_path = os.path.join(os.path.dirname(__file__), 'complex_test_cases.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        test_cases = json.load(f)

    results = []
    for tc in test_cases:
        tc_id = tc["id"]
        en_question = tc["question"]
        vn_question = VIETNAMESE_TRANSLATIONS[tc_id]
        
        print(f"Running EN {tc_id}...")
        try:
            en_report = answer_question(en_question)
            en_ans = {
                "status": en_report["status"],
                "sections": [{
                    "title": s["title"],
                    "status": s["status"],
                    "sql": s["sql"],
                    "answer": s["answer"],
                    "error": s["error"],
                    "attempt_count": s.get("attempt_count"),
                    "attempts": s.get("attempts", [])
                } for s in en_report["sections"]]
            }
        except Exception as e:
            en_ans = {"error": str(e)}

        print(f"Running VN {tc_id}...")
        try:
            vn_report = answer_question(vn_question)
            vn_ans = {
                "status": vn_report["status"],
                "sections": [{
                    "title": s["title"],
                    "status": s["status"],
                    "sql": s["sql"],
                    "answer": s["answer"],
                    "error": s["error"],
                    "attempt_count": s.get("attempt_count"),
                    "attempts": s.get("attempts", [])
                } for s in vn_report["sections"]]
            }
        except Exception as e:
            vn_ans = {"error": str(e)}

        results.append({
            "id": tc_id,
            "en_ans": en_ans,
            "vn_ans": vn_ans
        })

    out_path = os.path.join(os.path.dirname(__file__), '..', 'test_results', 'master_plan_evaluation_results.json')
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"\\nWrote results to {out_path}")

if __name__ == "__main__":
    run_tests()
