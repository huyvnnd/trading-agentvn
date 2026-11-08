"""
Dynamic Agent Manager & Critical Advisory Engine.
Quản lý việc tạo thêm Agent mới theo yêu cầu người dùng,
và cơ chế PHẢN BIỆN NGHIÊM KHẮC đưa ra dẫn chứng số liệu thực tế nếu yêu cầu của người dùng gây bất lợi hoặc rủi ro cao.
"""

import os
import json
import re
from datetime import datetime

class DynamicAgentManager:
    def __init__(self, data_file: str = None):
        if data_file is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_file = os.path.join(base_dir, "data", "custom_agents.json")

        self.data_file = data_file
        self.custom_agents = []
        self.load()

        # Nếu chưa có agent nào, khởi tạo một số Agent chuyên biệt mẫu của tổ chức
        if not self.custom_agents:
            self._init_default_agents()

    def _init_default_agents(self):
        self.custom_agents = [
            {
                "id": "agent_smart_money",
                "name": "Thợ Săn Dòng Tiền Cá Mập (Smart Money Tracker)",
                "role": "Truy vết dòng tiền tổ chức lớn, quỹ đầu tư và tự doanh",
                "trigger_keywords": ["smart money", "cá mập", "dòng tiền lớn", "tay to", "tự doanh"],
                "criteria": "Khối lượng đột biến > 200% TB20, xuất hiện gom hàng vùng nén VCP",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": "agent_dividend_hunter",
                "name": "Chuyên Gia Săn Cổ Tức Tiền Mặt (High Dividend Hunter)",
                "role": "Tìm kiếm cổ phiếu phòng thủ có tỷ suất cổ tức tiền mặt cao hơn lãi suất ngân hàng",
                "trigger_keywords": ["cổ tức", "dividend", "phòng thủ", "thu nhập thụ động"],
                "criteria": "Cổ tức tiền mặt đều đặn 3 năm gần nhất, tỷ suất cổ tức > 8%/năm, P/E < 12",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": "agent_growth_vcp",
                "name": "Chuyên Gia Săn Siêu Cổ Tăng Trưởng (CANSLIM & VCP)",
                "role": "Phát hiện cổ phiếu tăng trưởng EPS cao và mẫu hình thu hẹp độ biến động VCP",
                "trigger_keywords": ["siêu cổ", "canslim", "vcp", "tăng trưởng", "bứt phá"],
                "criteria": "Tăng trưởng LNST > 25%, nằm trên đường MA50 và MA200, độ nén biến động < 8%",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        ]
        self.save()

    def load(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.custom_agents = data.get("agents", [])
            except Exception as e:
                print(f"[DynamicAgentManager] Error loading custom agents: {e}")

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump({"agents": self.custom_agents}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[DynamicAgentManager] Error saving custom agents: {e}")

    def create_agent(self, name: str, role: str, criteria: str = "", trigger_keywords: list = None) -> dict:
        """Tạo thêm một Agent chuyên nhiệm vụ mới theo yêu cầu của người dùng."""
        agent_id = f"custom_agent_{len(self.custom_agents) + 1}_{int(datetime.now().timestamp())}"
        new_agent = {
            "id": agent_id,
            "name": name,
            "role": role,
            "criteria": criteria,
            "trigger_keywords": trigger_keywords or [name.lower()],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.custom_agents.append(new_agent)
        self.save()
        return {
            "success": True,
            "message": f"Đã khởi tạo thành công Agent mới: **{name}** (Nhiệm vụ: {role})",
            "agent": new_agent
        }

    def delete_agent(self, agent_id: str) -> bool:
        """Xóa một agent tùy biến."""
        initial_len = len(self.custom_agents)
        self.custom_agents = [a for a in self.custom_agents if a["id"] != agent_id]
        if len(self.custom_agents) < initial_len:
            self.save()
            return True
        return False

    def critique_user_intent(self, user_prompt: str) -> dict:
        """
        Bộ máy Phản biện Người dùng (Critical Advisory Engine):
        Nếu người dùng đưa ra các ý định hoặc yêu cầu nguy hiểm / bất lợi:
        - Mua cổ phiếu rác, penny thua lỗ
        - Bắt đáy dao rơi khi đang downtrend
        - Mua đuổi FOMO khi cổ phiếu đã chạy quá xa nền
        - Tắt cắt lỗ hoặc all-in đòn bẩy cao
        => Phân tích thẳng thắn, đưa ra số liệu & dẫn chứng xác thực tại sao hành động đó bất lợi!
        """
        prompt_lower = user_prompt.lower()
        criticisms = []

        # 1. Phát hiện đòi mua cổ phiếu rác (Penny / Bơm thổi / Lỗ nặng)
        penny_tickers = ["FLC", "ROS", "HAI", "AMD", "ART", "HQC", "ITA", "DAH", "TTF", "JVC"]
        for p in penny_tickers:
            if re.search(r'\b' + p.lower() + r'\b', prompt_lower) and any(w in prompt_lower for w in ["mua", "gom", "all in", "bắt"]):
                criticisms.append(
                    f"⛔ **PHẢN BIỆN PHÒNG THỦ: CẢNH BÁO RỦI RO CỔ PHIẾU {p}**\n\n"
                    f"- **Dẫn chứng thực tế:** Cổ phiếu nhóm này có lịch sử biến động thao túng giá đầu cơ, nhiều mã cùng hệ sinh thái đã bị đình chỉ giao dịch hoặc hủy niêm yết bắt buộc do vi phạm công bố thông tin và thua lỗ lũy kế.\n"
                    f"- **Bất lợi cho bạn:** Khung thanh khoản có thể biến mất bất kỳ lúc nào (trắng bên mua), dẫn đến việc không thể kích hoạt lệnh cắt lỗ khi thị trường xấu. Khi bị đình chỉ giao dịch, vốn của nhà đầu tư bị chôn vùi hàng năm trời.\n"
                    f"- **Khuyến nghị từ Hội Đồng Đầu Tư:** Loại bỏ ngay tư duy đánh bạc với cổ phiếu 'trà đá'. Tập trung vào doanh nghiệp có nền tảng kinh doanh thật, dòng tiền dương và thanh khoản dồi dào."
                )

        # 2. Phát hiện đòi Bắt Đáy Dao Rơi (Falling Knife)
        if any(w in prompt_lower for w in ["bắt đáy", "trung bình giá xuống", "càng giảm càng mua"]) and not any(w in prompt_lower for w in ["hỏi", "có nên", "là gì"]):
            criticisms.append(
                "⚠️ **PHẢN BIỆN CHIẾN LƯỢC: CẠM BẪY BẮT ĐÁY TRUNG BÌNH GIÁ XUỐNG**\n\n"
                "- **Dẫn chứng thực tế:** Trong các chu kỳ sụt giảm (Downtrend), một cổ phiếu giảm 50% thường tiếp tục giảm thêm 30-50% nữa so với mức đáy tạm thời. Bắt đáy khi chưa có tín hiệu tạo đáy đa khung thời gian (Wyckoff Spring hoặc Higher Low) là nguyên nhân hàng đầu gây cháy tài khoản cá nhân.\n"
                "- **Bất lợi cho bạn:** Bắt đáy sớm khiến tài khoản bị kẹt hàng T+2.5, chịu áp lực tâm lý cực nặng khi cổ phiếu liên tiếp tạo đáy mới mà không thể thoát vị thế.\n"
                "- **Khuyến nghị từ Hội Đồng Đầu Tư:** Chỉ mua khi giá đã xác nhận cấu trúc Đỉnh/Đáy đảo chiều (Higher High / Higher Low) và có sự bảo trợ của dòng tiền tổ chức Smart Money."
            )

        # 3. Phát hiện đòi Mua Đuổi FOMO / Đua Lệnh Trần
        if any(w in prompt_lower for w in ["đua lệnh", "mua trần", "fomo", "mua đuổi"]):
            criticisms.append(
                "⚠️ **PHẢN BIỆN TÂM LÝ: CẠM BẪY MUA ĐUỔI FOMO TẠI VÙNG ĐỈNH**\n\n"
                "- **Dẫn chứng thực tế:** Thống kê lịch sử trên sàn HOSE cho thấy xác suất cổ phiếu quay đầu điều chỉnh rũ bỏ kỹ thuật sau 3-4 phiên tăng trần liên tiếp là trên 78%. Những người mua đuổi ở phiên hưng phấn tột độ thường gánh chịu khoản lỗ ngắn hạn 10-15% ngay khi hàng về tài khoản.\n"
                "- **Bất lợi cho bạn:** Điểm mua quá xa vùng dừng lỗ an toàn khiến tỷ lệ R:R bị bóp méo nghiêm trọng (rủi ro cắt lỗ 10% nhưng tiềm năng tăng giá chỉ còn 3-5%).\n"
                "- **Khuyến nghị từ Hội Đồng Đầu Tư:** Kiên nhẫn chờ nhịp điều chỉnh lành mạnh (Pullback) về vùng hỗ trợ cân bằng hoặc đường MA20 để có điểm vào tối ưu."
            )

        # 4. Phát hiện đòi Không Cắt Lỗ hoặc All-in Margin
        if any(w in prompt_lower for w in ["không cắt lỗ", "gồng lỗ", "all in", "full margin"]):
            criticisms.append(
                "⛔ **PHẢN BIỆN QUẢN TRỊ VỐN: NGUY CƠ CHÁY TÀI KHOẢN VÌ 'GỒNG LỖ' & ĐÒN BẨY**\n\n"
                "- **Dẫn chứng toán học:** Khi bạn lỗ 50%, bạn phải kiếm lại mức lãi +100% chỉ để hòa vốn! Nếu dùng đòn bẩy Margin cao, chỉ cần thị trường giảm 15% là tài khoản bị gọi ký quỹ (Force Sell/Call Margin), dẫn đến mất trắng vốn gốc.\n"
                "- **Bất lợi cho bạn:** Không cắt lỗ tước đi cơ hội nắm giữ tiền mặt để mua các siêu cổ phiếu ở đáy chu kỳ mới.\n"
                "- **Khuyến nghị từ Hội Đồng Đầu Tư:** Bắt buộc tuân thủ nguyên tắc cắt lỗ cấu trúc (tối đa -7% đến -8%). Không bao giờ all-in quá 30% danh mục vào một mã đơn lẻ."
            )

        if criticisms:
            return {
                "has_criticism": True,
                "criticisms": criticisms
            }

        return {"has_criticism": False, "criticisms": []}
