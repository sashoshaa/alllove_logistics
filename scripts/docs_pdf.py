"""Демо-бланки по образцу первички: ТОРГ-12, упаковочный лист, счёт на оплату."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from fpdf import FPDF

FONT_DIR = Path(__file__).resolve().parent / "fonts"
VAT = Decimal("22")

BUYER = {
    "name": 'ООО «Шоурум AllLove»',
    "inn": "5260123456",
    "kpp": "526001001",
    "okpo": "56234128",
    "address": "603000, г. Нижний Новгород, ул. Большая Покровская, д. 12",
    "phone": "+7 (831) 000-10-00",
    "bank": "Волго-Вятский банк ПАО Сбербанк",
    "bik": "042202603",
    "rs": "40702810100000005621",
    "ks": "30101810900000000603",
    "director": "Кузнецова А.В.",
}

SUPPLIER_REQ = {
    "Ателье Нева": {
        "inn": "7834123456",
        "kpp": "783401001",
        "okpo": "04512367",
        "bank": "Северо-Западный банк ПАО Сбербанк",
        "bik": "044030653",
        "rs": "40702810955000011122",
        "director": "Соколова Е.П.",
        "buh": "Крылова Н.И.",
        "storekeeper": "Васильев П.А.",
        "full": 'ООО «Ателье Нева»',
    },
    "Fashion House": {
        "inn": "7705123789",
        "kpp": "770501001",
        "okpo": "11234567",
        "bank": "ПАО «Банк ВТБ»",
        "bik": "044525187",
        "rs": "40702810100000033445",
        "director": "Морозов И.С.",
        "buh": "Белова О.Г.",
        "storekeeper": "Чижов Д.А.",
        "full": 'ООО «Fashion House»',
    },
    "Maison Luce": {
        "inn": "9909123456",
        "kpp": "990901001",
        "okpo": "99001234",
        "bank": "АО «Райффайзенбанк»",
        "bik": "044525700",
        "rs": "40702810900000055667",
        "director": "Bianchi M.",
        "buh": "Rossi L.",
        "storekeeper": "Ferrari G.",
        "full": "Maison Luce S.r.l.",
    },
    "Шёлк Казани": {
        "inn": "1655123456",
        "kpp": "165501001",
        "okpo": "33445566",
        "bank": "Отделение «Банк Татарстан» ПАО Сбербанк",
        "bik": "049205603",
        "rs": "40702810400000077889",
        "director": "Хакимова Л.Р.",
        "buh": "Сафина Г.М.",
        "storekeeper": "Ибрагимов А.Н.",
        "full": 'ООО «Шёлк Казани»',
    },
    "Nord Knit": {
        "inn": "4704123456",
        "kpp": "470401001",
        "okpo": "77889900",
        "bank": "Северо-Западный банк ПАО Сбербанк",
        "bik": "044030653",
        "rs": "40702810700000099001",
        "director": "Лаасонен К.Э.",
        "buh": "Никитина С.В.",
        "storekeeper": "Петров Ю.К.",
        "full": 'ООО «Nord Knit»',
    },
}

PRICES = {
    "AL-DR-001": Decimal("14500.00"),
    "AL-DR-002": Decimal("18900.00"),
    "AL-BL-010": Decimal("7200.00"),
    "AL-BL-011": Decimal("6800.00"),
    "AL-CT-020": Decimal("24500.00"),
    "AL-CT-021": Decimal("21800.00"),
    "AL-JK-030": Decimal("13200.00"),
    "AL-SK-031": Decimal("8900.00"),
    "AL-KN-040": Decimal("9800.00"),
    "AL-KN-041": Decimal("11200.00"),
    "AL-AC-050": Decimal("3400.00"),
    "AL-AC-051": Decimal("4100.00"),
}

_UNITS = ["", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
_UNITS_F = ["", "одна", "две", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
_TEENS = [
    "десять",
    "одиннадцать",
    "двенадцать",
    "тринадцать",
    "четырнадцать",
    "пятнадцать",
    "шестнадцать",
    "семнадцать",
    "восемнадцать",
    "девятнадцать",
]
_TENS = ["", "", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят", "восемьдесят", "девяносто"]
_HUNDREDS = ["", "сто", "двести", "триста", "четыреста", "пятьсот", "шестьсот", "семьсот", "восемьсот", "девятьсот"]


@dataclass
class LineItem:
    sku: str
    name: str
    color: str
    size: str
    qty: int
    price: Decimal

    @property
    def title(self) -> str:
        parts = [self.name]
        if self.color:
            parts.append(f"цв. {self.color}")
        if self.size:
            parts.append(f"р. {self.size}")
        parts.append(f"арт. {self.sku}")
        return ", ".join(parts)


def money(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{quantized:,.2f}".replace(",", " ").replace(".", ",")


def _triplet(n: int, feminine: bool = False) -> str:
    names = _UNITS_F if feminine else _UNITS
    h, rest = divmod(n, 100)
    words = [_HUNDREDS[h]] if h else []
    if rest >= 10 and rest < 20:
        words.append(_TEENS[rest - 10])
    else:
        t, u = divmod(rest, 10)
        if t:
            words.append(_TENS[t])
        if u:
            words.append(names[u])
    return " ".join(w for w in words if w)


def _plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(n) % 100
    if 11 <= n <= 19:
        return many
    n %= 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many


def money_words(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    rubles = int(quantized)
    kopecks = int((quantized - rubles) * 100)
    millions, rest = divmod(rubles, 1_000_000)
    thousands, units = divmod(rest, 1000)
    parts = []
    if millions:
        parts.append(_triplet(millions))
        parts.append(_plural(millions, "миллион", "миллиона", "миллионов"))
    if thousands:
        parts.append(_triplet(thousands, feminine=True))
        parts.append(_plural(thousands, "тысяча", "тысячи", "тысяч"))
    if units or not parts:
        parts.append(_triplet(units) or "ноль")
    parts.append(_plural(rubles, "рубль", "рубля", "рублей"))
    kop = f"{kopecks:02d}"
    parts.append(kop)
    parts.append(_plural(kopecks, "копейка", "копейки", "копеек"))
    text = " ".join(parts)
    return text[:1].upper() + text[1:]


def supplier_card(name: str, address: str, phone: str) -> dict:
    extra = SUPPLIER_REQ.get(name, {})
    full = extra.get("full", name)
    return {
        "name": name,
        "full": full,
        "inn": extra.get("inn", "0000000000"),
        "kpp": extra.get("kpp", "000000000"),
        "okpo": extra.get("okpo", "00000000"),
        "address": address or "",
        "phone": phone or "",
        "bank": extra.get("bank", ""),
        "bik": extra.get("bik", ""),
        "rs": extra.get("rs", ""),
        "director": extra.get("director", "________________"),
        "buh": extra.get("buh", "________________"),
        "storekeeper": extra.get("storekeeper", "________________"),
        "line": f"{full}, ИНН {extra.get('inn', '—')}, КПП {extra.get('kpp', '—')}, {address or '—'}, тел. {phone or '—'}",
    }


def _font_paths() -> tuple[Path, Path]:
    regular = FONT_DIR / "LiberationSans-Regular.ttf"
    bold = FONT_DIR / "LiberationSans-Bold.ttf"
    if regular.exists() and bold.exists():
        return regular, bold
    return (
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    )


class FormPDF(FPDF):
    def __init__(self, landscape: bool = False):
        super().__init__(orientation="L" if landscape else "P", unit="mm", format="A4")
        regular, bold = _font_paths()
        self.add_font("Doc", "", str(regular))
        self.add_font("Doc", "B", str(bold))
        self.set_auto_page_break(auto=False)
        self.set_margins(8, 8, 8)

    def f(self, size: float, bold: bool = False) -> None:
        self.set_font("Doc", "B" if bold else "", size)

    def line_text(self, text: str, size: float = 7, bold: bool = False) -> None:
        self.f(size, bold)
        self.cell(0, 4, text, new_x="LMARGIN", new_y="NEXT")

    def kv_row(self, label: str, value: str, label_w: float, value_w: float, code_label: str = "", code: str = "") -> None:
        y = self.get_y()
        x = self.l_margin
        height = 8
        self.set_xy(x, y)
        self.f(6)
        self.cell(label_w, height, label, border=1)
        self.set_xy(x + label_w, y)
        self.f(6.2)
        self.rect(x + label_w, y, value_w, height)
        self.set_xy(x + label_w + 0.6, y + 0.6)
        self.multi_cell(value_w - 1.2, 3.3, value)
        if code_label:
            self.set_xy(x + label_w + value_w, y)
            self.f(6)
            self.cell(28, height, code_label, border=1, align="C")
            self.f(7, True)
            self.cell(22, height, code, border=1, align="C")
        self.set_xy(x, y + height)

    def stamp(self, x: float, y: float, title: str, inn: str) -> None:
        self.set_draw_color(176, 48, 48)
        self.set_text_color(176, 48, 48)
        self.set_line_width(0.45)
        self.ellipse(x, y, 34, 34)
        self.set_line_width(0.2)
        self.ellipse(x + 1.4, y + 1.4, 31.2, 31.2)
        self.set_xy(x, y + 8)
        self.f(6, True)
        self.cell(34, 4, "М.П.", align="C")
        self.set_xy(x, y + 13)
        self.f(5, True)
        self.multi_cell(34, 3.2, title, align="C")
        self.set_xy(x, y + 24)
        self.f(4.5)
        self.cell(34, 3, f"ИНН {inn}", align="C")
        self.set_text_color(0, 0, 0)
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.2)

    def sign_line(self, x: float, y: float, w: float, role: str, name: str) -> None:
        self.set_xy(x, y)
        self.f(6)
        self.cell(w, 4, role)
        self.set_xy(x, y + 8)
        self.line(x, y + 8, x + w * 0.55, y + 8)
        self.line(x + w * 0.6, y + 8, x + w, y + 8)
        self.set_xy(x, y + 8.4)
        self.f(5)
        self.cell(w * 0.55, 3, "(подпись)", align="C")
        self.cell(w * 0.45, 3, name, align="C")


def _item_rows(items: list[LineItem]) -> list[dict]:
    rows = []
    for index, item in enumerate(items, start=1):
        qty = Decimal(item.qty)
        net = (qty * item.price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        vat = (net * VAT / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        gross = net + vat
        places = max(1, (item.qty + 1) // 2)
        rows.append(
            {
                "n": str(index),
                "name": item.title,
                "code": item.sku,
                "unit": "шт",
                "okei": "796",
                "pack": "кор.",
                "in_place": "2",
                "places": str(places),
                "brutto": f"{item.qty * 0.45:.1f}".replace(".", ","),
                "qty": str(item.qty),
                "price": money(item.price),
                "net": money(net),
                "rate": "22%",
                "vat": money(vat),
                "gross": money(gross),
                "net_n": net,
                "vat_n": vat,
                "gross_n": gross,
                "qty_n": item.qty,
                "places_n": places,
                "brutto_n": item.qty * 0.45,
            }
        )
    return rows


def torg12_pdf(
    *,
    number: str,
    issued: date,
    supplier_name: str,
    supplier_address: str,
    supplier_phone: str,
    location_name: str,
    location_address: str,
    items: list[LineItem],
    received_by: str,
) -> bytes:
    supplier = supplier_card(supplier_name, supplier_address, supplier_phone)
    rows = _item_rows(items)
    total_net = sum((row["net_n"] for row in rows), Decimal("0"))
    total_vat = sum((row["vat_n"] for row in rows), Decimal("0"))
    total_gross = sum((row["gross_n"] for row in rows), Decimal("0"))
    total_qty = sum(row["qty_n"] for row in rows)
    total_places = sum(row["places_n"] for row in rows)
    total_brutto = sum(row["brutto_n"] for row in rows)

    pdf = FormPDF(landscape=True)
    pdf.add_page()
    pdf.f(7)
    pdf.set_xy(210, 8)
    pdf.multi_cell(
        79,
        3.2,
        "Унифицированная форма № ТОРГ-12\nУтверждена постановлением Госкомстата\nРоссии от 25.12.98 № 132",
        align="R",
    )
    pdf.set_xy(230, 20)
    pdf.f(6)
    pdf.cell(28, 5, "Код", border=1, align="C")
    pdf.cell(22, 5, "", border=1)
    pdf.set_xy(230, 25)
    pdf.cell(28, 5, "Форма по ОКУД", border=1)
    pdf.f(7, True)
    pdf.cell(22, 5, "0330212", border=1, align="C")

    pdf.set_xy(8, 20)
    pdf.f(8, True)
    pdf.cell(0, 5, "ТОВАРНАЯ НАКЛАДНАЯ")
    pdf.set_xy(8, 32)

    sender = f"{supplier['line']}; р/с {supplier['rs']} в {supplier['bank']}, БИК {supplier['bik']}"
    receiver = (
        f"{BUYER['name']}, ИНН {BUYER['inn']}, КПП {BUYER['kpp']}, {location_name}, "
        f"{location_address or BUYER['address']}, тел. {BUYER['phone']}"
    )
    payer = (
        f"{BUYER['name']}, ИНН {BUYER['inn']}/{BUYER['kpp']}, {BUYER['address']}, "
        f"р/с {BUYER['rs']} в {BUYER['bank']}, БИК {BUYER['bik']}"
    )
    pdf.kv_row("Грузоотправитель", sender, 36, 187, "по ОКПО", supplier["okpo"])
    pdf.kv_row("Структурное подразделение", "Склад готовой продукции", 36, 187, "", "")
    pdf.kv_row("Грузополучатель", receiver, 36, 187, "по ОКПО", BUYER["okpo"])
    pdf.kv_row("Поставщик", sender, 36, 187, "по ОКПО", supplier["okpo"])
    pdf.kv_row("Плательщик", payer, 36, 187, "по ОКПО", BUYER["okpo"])
    pdf.kv_row(
        "Основание",
        f"Договор поставки № АЛ-2026/{number[-3:]} от 15.01.2026",
        36,
        187,
        "",
        "",
    )

    y = pdf.get_y() + 1
    pdf.set_xy(8, y)
    pdf.f(6)
    pdf.cell(36, 8, "Транспортная накладная", border=1)
    pdf.f(7)
    pdf.cell(80, 8, f"№ ТН-{number} от {issued.strftime('%d.%m.%Y')}", border=1)
    pdf.f(6)
    pdf.cell(40, 8, "Номер документа", border=1, align="C")
    pdf.cell(40, 8, "Дата составления", border=1, align="C")
    pdf.set_xy(164, y + 8)
    pdf.f(8, True)
    pdf.cell(40, 7, number, border=1, align="C")
    pdf.cell(40, 7, issued.strftime("%d.%m.%Y"), border=1, align="C")
    pdf.set_y(y + 16)

    headers = [
        ("№\nп/п", 8),
        ("Товар\nнаименование, характеристика, сорт, артикул", 62),
        ("Код", 18),
        ("Ед.\nнаим.", 12),
        ("изм.\nкод", 10),
        ("Вид\nупак.", 12),
        ("Кол-во\nв месте", 12),
        ("Кол-во\nмест", 12),
        ("Масса\nбрутто", 14),
        ("Кол-во\n(нетто)", 14),
        ("Цена,\nруб. коп.", 20),
        ("Сумма без\nучета НДС", 22),
        ("НДС\nставка", 12),
        ("НДС\nсумма", 20),
        ("Сумма с\nучетом НДС", 22),
    ]
    y = pdf.get_y() + 2
    x = 8
    pdf.f(5.2, True)
    for text, width in headers:
        pdf.set_xy(x, y)
        pdf.rect(x, y, width, 12)
        pdf.set_xy(x, y + 1)
        pdf.multi_cell(width, 3.2, text, align="C")
        x += width
    col_w = [w for _, w in headers]
    keys = [
        "n",
        "name",
        "code",
        "unit",
        "okei",
        "pack",
        "in_place",
        "places",
        "brutto",
        "qty",
        "price",
        "net",
        "rate",
        "vat",
        "gross",
    ]
    y += 12
    pdf.f(6)
    for row in rows:
        height = 9 if len(row["name"]) < 70 else 12
        x = 8
        pdf.set_xy(x, y)
        for key, width in zip(keys, col_w):
            pdf.set_xy(x, y)
            pdf.rect(x, y, width, height)
            align = "L" if key in {"name", "code"} else "C"
            pdf.set_xy(x + 0.4, y + 1)
            pdf.multi_cell(width - 0.8, 3.2, row[key], align=align)
            x += width
        y += height

    x = 8
    pdf.set_xy(x, y)
    pdf.f(6, True)
    pdf.cell(sum(col_w[:8]), 6, "Всего по накладной", border=1, align="R")
    pdf.f(6)
    pdf.cell(col_w[8], 6, f"{total_brutto:.1f}".replace(".", ","), border=1, align="C")
    pdf.cell(col_w[9], 6, str(total_qty), border=1, align="C")
    pdf.cell(col_w[10], 6, "X", border=1, align="C")
    pdf.cell(col_w[11], 6, money(total_net), border=1, align="C")
    pdf.cell(col_w[12], 6, "X", border=1, align="C")
    pdf.cell(col_w[13], 6, money(total_vat), border=1, align="C")
    pdf.cell(col_w[14], 6, money(total_gross), border=1, align="C")
    y += 8

    pdf.set_xy(8, y)
    pdf.f(7)
    pdf.cell(0, 5, f"Товарная накладная имеет продолжение на листах: 1   Всего наименований: {len(rows)}")
    pdf.set_xy(8, y + 5)
    pdf.cell(0, 5, f"Всего мест: {total_places}     Масса груза (нетто): {total_qty} шт     Масса груза (брутто): {total_brutto:.1f} кг")
    pdf.set_xy(8, y + 10)
    pdf.cell(0, 5, "Приложение (паспорта, сертификаты и т.п.) на 1 листе")
    pdf.set_xy(8, y + 15)
    pdf.f(7, True)
    pdf.cell(0, 5, f"Всего отпущено на сумму: {money_words(total_gross)}")

    pdf.set_xy(8, y + 22)
    pdf.f(7, True)
    pdf.cell(140, 5, "Отпуск груза разрешил")
    pdf.cell(140, 5, "По доверенности № _______ от ______________")
    pdf.sign_line(8, y + 28, 130, "Руководитель организации", supplier["director"])
    pdf.sign_line(150, y + 28, 130, "Груз принял", received_by)
    pdf.sign_line(8, y + 44, 130, "Главный (старший) бухгалтер", supplier["buh"])
    pdf.sign_line(150, y + 44, 130, "Груз получил грузополучатель", received_by)
    pdf.sign_line(8, y + 60, 130, "Отпустил", supplier["storekeeper"])

    pdf.set_xy(8, y + 76)
    pdf.f(6)
    pdf.cell(130, 4, f"М.П.                              {issued.strftime('%d.%m.%Y')}")
    pdf.cell(130, 4, f"М.П.                              {issued.strftime('%d.%m.%Y')}")
    pdf.stamp(96, y + 52, supplier["full"], supplier["inn"])
    pdf.stamp(238, y + 52, BUYER["name"], BUYER["inn"])
    return bytes(pdf.output())


def packing_list_pdf(
    *,
    number: str,
    issued: date,
    supplier_name: str,
    location_name: str,
    items: list[LineItem],
) -> bytes:
    rows = _item_rows(items)
    pdf = FormPDF(landscape=False)
    pdf.add_page()
    pdf.f(9)
    pdf.cell(0, 5, 'ООО «Шоурум AllLove»  ·  складской учёт', new_x="LMARGIN", new_y="NEXT")
    pdf.f(16, True)
    pdf.cell(0, 10, "УПАКОВОЧНЫЙ ЛИСТ", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.f(11, True)
    pdf.cell(0, 7, f"к товарной накладной № {number} от {issued.strftime('%d.%m.%Y')}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(3)
    pdf.f(9)
    pdf.cell(0, 6, f"Грузоотправитель: {supplier_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Грузополучатель: {BUYER['name']}, {location_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Пломба: AL-red / {number}     Маркировка: fragile · одежда", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    cols = [("№", 12), ("Наименование / артикул", 88), ("Место №", 22), ("Кол-во, шт", 24), ("Вес брутто, кг", 28), ("Примечание", 26)]
    x, y = pdf.l_margin, pdf.get_y()
    pdf.f(7, True)
    for text, width in cols:
        pdf.set_xy(x, y)
        pdf.cell(width, 8, text, border=1, align="C")
        x += width
    y += 8
    pdf.f(7.5)
    place = 1
    widths = [w for _, w in cols]
    for row in rows:
        values = [row["n"], row["name"], str(place), row["qty"], row["brutto"], "короб, скотч"]
        x = pdf.l_margin
        height = 10
        for value, width in zip(values, widths):
            pdf.set_xy(x, y)
            pdf.rect(x, y, width, height)
            pdf.set_xy(x + 0.5, y + 1.5)
            pdf.multi_cell(width - 1, 3.4, value, align="C" if width < 40 else "L")
            x += width
        y += height
        place += 1
    pdf.set_xy(pdf.l_margin, y + 4)
    pdf.f(9)
    pdf.cell(0, 6, f"Всего грузовых мест: {sum(row['places_n'] for row in rows)}     Нетто: {sum(row['qty_n'] for row in rows)} шт", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.cell(90, 6, "Упаковщик ________________  / кладовщик /")
    pdf.cell(90, 6, "Принял ________________")
    return bytes(pdf.output())


def invoice_pdf(
    *,
    number: str,
    issued: date,
    supplier_name: str,
    supplier_address: str,
    supplier_phone: str,
    items: list[LineItem],
) -> bytes:
    supplier = supplier_card(supplier_name, supplier_address, supplier_phone)
    rows = _item_rows(items)
    total_gross = sum((row["gross_n"] for row in rows), Decimal("0"))
    total_vat = sum((row["vat_n"] for row in rows), Decimal("0"))
    pdf = FormPDF(landscape=False)
    pdf.add_page()
    pdf.f(9)
    pdf.multi_cell(0, 4.5, f"{supplier['full']}\nИНН {supplier['inn']}  КПП {supplier['kpp']}\n{supplier['address']}\nр/с {supplier['rs']}  {supplier['bank']}  БИК {supplier['bik']}")
    pdf.ln(4)
    pdf.f(16, True)
    pdf.cell(0, 10, f"Счёт на оплату № {number} от {issued.strftime('%d.%m.%Y')}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_draw_color(122, 46, 42)
    pdf.set_line_width(0.8)
    pdf.line(pdf.l_margin, pdf.get_y(), 210 - pdf.r_margin, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.set_draw_color(0, 0, 0)
    pdf.ln(4)
    pdf.f(9)
    pdf.cell(0, 6, f"Поставщик: {supplier['full']}, ИНН {supplier['inn']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Покупатель: {BUYER['name']}, ИНН {BUYER['inn']} / КПП {BUYER['kpp']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Основание: договор поставки № АЛ-2026/{number[-3:]} от 15.01.2026", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    cols = [("№", 10), ("Товары (работы, услуги)", 96), ("Кол-во", 18), ("Ед.", 12), ("Цена", 26), ("Сумма", 28)]
    y = pdf.get_y()
    x = pdf.l_margin
    pdf.f(7, True)
    for text, width in cols:
        pdf.set_xy(x, y)
        pdf.cell(width, 8, text, border=1, align="C")
        x += width
    y += 8
    pdf.f(8)
    for row in rows:
        values = [row["n"], row["name"], row["qty"], "шт", row["price"], row["gross"]]
        x = pdf.l_margin
        height = 10
        for value, width in zip(values, [w for _, w in cols]):
            pdf.set_xy(x, y)
            pdf.rect(x, y, width, height)
            pdf.set_xy(x + 0.5, y + 1.5)
            pdf.multi_cell(width - 1, 3.5, value, align="C" if width < 30 else "L")
            x += width
        y += height
    pdf.set_xy(pdf.l_margin + 136, y)
    pdf.f(9)
    pdf.cell(26, 6, "Итого:", border=1, align="R")
    pdf.cell(28, 6, money(total_gross), border=1, align="C")
    pdf.set_xy(pdf.l_margin + 136, y + 6)
    pdf.cell(26, 6, "В т.ч. НДС 22%:", border=1, align="R")
    pdf.cell(28, 6, money(total_vat), border=1, align="C")
    pdf.set_xy(pdf.l_margin, y + 16)
    pdf.f(9, True)
    pdf.multi_cell(0, 5, f"Всего к оплате: {money_words(total_gross)}")
    pdf.ln(6)
    pdf.f(9)
    pdf.cell(0, 6, f"Руководитель ________________  {supplier['director']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Главный бухгалтер ________________  {supplier['buh']}")
    pdf.stamp(140, y + 28, supplier["full"], supplier["inn"])
    return bytes(pdf.output())


def line_items_from_catalog(entries: list[tuple[str, int]], catalog: dict) -> list[LineItem]:
    rows = []
    for sku, qty in entries:
        item = catalog[sku]
        rows.append(
            LineItem(
                sku=sku,
                name=item.name,
                color=item.color or "",
                size=item.size or "",
                qty=qty,
                price=PRICES.get(sku, Decimal("5000.00")),
            )
        )
    return rows
