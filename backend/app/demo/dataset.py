from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

DATASET_ID = uuid5(NAMESPACE_URL, "smartinventory/demo-inventory/v1")
VERSION = "v1"
CATEGORIES = (
    "Văn phòng phẩm",
    "Thiết bị công nghệ",
    "Bao bì đóng gói",
    "Bảo hộ lao động",
    "Vệ sinh công nghiệp",
    "Nguyên liệu thực phẩm",
    "Vật tư kỹ thuật",
    "Hàng ngừng kinh doanh",
)
SUPPLIERS = (
    "Văn phòng Minh An",
    "Công nghệ Sao Mai",
    "Bao bì Đông Phương",
    "Bảo hộ An Tâm",
    "Hóa phẩm Sạch Việt",
    "Nguyên liệu An Phú",
    "Vật tư Thành Công",
    "Nhà cung cấp cũ",
)
State = Literal["normal", "high", "low", "zero", "no_history", "archived_empty", "archived_stock"]


@dataclass(frozen=True)
class ProductSpec:
    code: str
    name: str
    category: int
    unit: str
    minimum: str
    cost: str
    lead: int
    state: State
    batch: str

    @property
    def sku(self) -> str:
        return "DEMO-" + self.code

    @property
    def active(self) -> bool:
        return not self.state.startswith("archived")

    @property
    def target(self) -> Decimal:
        minimum, batch = Decimal(self.minimum), Decimal(self.batch)
        step = Decimal("1") if self.unit == "PCS" else Decimal("0.001")
        if self.state in {"zero", "no_history", "archived_empty"}:
            return Decimal(0)
        if self.state == "low":
            return (minimum / 4).quantize(step, rounding=ROUND_DOWN)
        if self.state == "high":
            return minimum * 12 + batch * 4
        if self.state == "archived_stock":
            return minimum + batch * 3
        return minimum * 3 + batch * 4


PRODUCTS = (
    ProductSpec("VP001", "Bút bi xanh 0.5 mm", 0, "PCS", "50", "3500", 3, "low", "12"),
    ProductSpec("VP002", "Bút bi đen 0.7 mm", 0, "PCS", "40", "4200", 3, "normal", "10"),
    ProductSpec("VP003", "Giấy A4 80 gsm — ram 500 tờ", 0, "PCS", "20", "78000", 5, "high", "6"),
    ProductSpec("VP004", "Bìa hồ sơ còng A4", 0, "PCS", "30", "16500", 2, "normal", "8"),
    ProductSpec("VP005", "Hộp mực máy in laser", 0, "PCS", "5", "650000", 10, "zero", "2"),
    ProductSpec("VP006", "Sổ tay bìa cứng A5", 0, "PCS", "10", "42000", 4, "no_history", "4"),
    ProductSpec("IT001", "Chuột không dây", 1, "PCS", "10", "185000", 7, "normal", "3"),
    ProductSpec("IT002", "Bàn phím USB tiêu chuẩn", 1, "PCS", "8", "320000", 7, "low", "3"),
    ProductSpec("IT003", "Ổ cứng SSD 512 GB", 1, "PCS", "5", "890000", 14, "high", "1"),
    ProductSpec("IT004", "Cáp USB-C dài 2 m", 1, "PCS", "20", "65000", 5, "normal", "5"),
    ProductSpec("IT005", "Tai nghe có micro", 1, "PCS", "6", "450000", 12, "zero", "2"),
    ProductSpec("BB001", "Thùng carton 40 × 30 × 30 cm", 2, "PCS", "100", "12500", 4, "low", "30"),
    ProductSpec("BB002", "Cuộn băng keo trong 48 mm", 2, "PCS", "40", "18500", 2, "normal", "10"),
    ProductSpec("BB003", "Màng PE quấn hàng", 2, "KG", "25", "48000", 5, "high", "5.125"),
    ProductSpec("BB004", "Dây đai nhựa đóng kiện", 2, "KG", "15", "42000", 4, "normal", "3.250"),
    ProductSpec("BB005", "Túi zip 20 × 30 cm", 2, "PCS", "200", "800", 3, "normal", "60"),
    ProductSpec("BH001", "Găng tay phủ cao su — đôi", 3, "PCS", "50", "8500", 4, "normal", "20"),
    ProductSpec("BH002", "Khẩu trang bảo hộ", 3, "PCS", "100", "2500", 3, "high", "25"),
    ProductSpec("BH003", "Kính bảo hộ trong suốt", 3, "PCS", "15", "35000", 7, "low", "4"),
    ProductSpec("BH004", "Áo phản quang", 3, "PCS", "20", "48000", 6, "normal", "5"),
    ProductSpec("VS001", "Nước lau sàn hương sả", 4, "LITER", "40", "18000", 3, "normal", "8.500"),
    ProductSpec(
        "VS002", "Dung dịch sát khuẩn bề mặt", 4, "LITER", "25", "42000", 5, "low", "6.125"
    ),
    ProductSpec("VS003", "Nước rửa chén đậm đặc", 4, "LITER", "30", "22000", 3, "high", "7.250"),
    ProductSpec("VS004", "Bột giặt công nghiệp", 4, "KG", "20", "36000", 4, "normal", "4.375"),
    ProductSpec("VS005", "Chất tẩy rửa đa năng", 4, "LITER", "0", "25000", 0, "normal", "3.125"),
    ProductSpec("NL001", "Gạo thơm đóng bao", 5, "KG", "100", "18500", 3, "normal", "25.500"),
    ProductSpec("NL002", "Đường tinh luyện", 5, "KG", "50", "24000", 4, "low", "12.125"),
    ProductSpec("NL003", "Hạt cà phê rang mộc", 5, "KG", "20", "185000", 10, "normal", "4.750"),
    ProductSpec("NL004", "Dầu ăn thực vật", 5, "LITER", "40", "48000", 5, "normal", "10.125"),
    ProductSpec("NL005", "Syrup đường mía", 5, "LITER", "10", "65000", 7, "no_history", "3.125"),
    ProductSpec("VT001", "Bu lông M8 mạ kẽm", 6, "PCS", "200", "1500", 7, "high", "60"),
    ProductSpec("VT002", "Vòng bi máy công nghiệp", 6, "PCS", "10", "95000", 15, "normal", "3"),
    ProductSpec("VT003", "Dầu nhờn máy công nghiệp", 6, "LITER", "25", "78000", 10, "low", "6.125"),
    ProductSpec("VT004", "Hạt nhựa PP nguyên sinh", 6, "KG", "50", "32000", 20, "normal", "12.250"),
    ProductSpec(
        "CU001", "Bàn phím cổng PS/2 — dòng cũ", 7, "PCS", "0", "95000", 0, "archived_empty", "2"
    ),
    ProductSpec(
        "CU002",
        "Dầu công nghiệp — dòng cũ",
        7,
        "LITER",
        "10",
        "65000",
        0,
        "archived_stock",
        "3.125",
    ),
)


def entity_id(label: str):
    return uuid5(DATASET_ID, label)
