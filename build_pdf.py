import os
import sys
import json
from datetime import datetime
from pypdf import PdfWriter, PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

#def setup_jp_font(bold: bool = False):
    # 1) Cloud対応：同梱フォント優先
    #bundled = os.path.join(ASSETS_DIR, "fonts", "NotoSansJP-Regular.ttf")
    #if os.path.exists(bundled):
        #pdfmetrics.registerFont(TTFont("JPFont", bundled))
        #return "JPFont"

    # 2) Windowsローカル：Meiryo
    #meiryo_path = r"C:\Windows\Fonts\meiryo.ttc"
    #if os.path.exists(meiryo_path):
        #pdfmetrics.registerFont(TTFont("Meiryo", meiryo_path))
        #return "Meiryo"


    # 3) 最後の保険
    #return "Helvetica"

def setup_jp_font(bold: bool = False) -> str:
    # assets/fonts に入れたフォントを使う（ローカル/Cloudで統一）
    regular_path = os.path.join(ASSETS_DIR, "fonts", "NotoSansJP-Regular.ttf")
    bold_path    = os.path.join(ASSETS_DIR, "fonts", "NotoSansJP-Bold.ttf")

    # Regular
    if "JPFont" not in pdfmetrics.getRegisteredFontNames():
        if not os.path.exists(regular_path):
            raise FileNotFoundError(f"フォントが見つかりません: {regular_path}")
        pdfmetrics.registerFont(TTFont("JPFont", regular_path))

    # Bold（入れていれば使う）
    if bold:
        if os.path.exists(bold_path) and "JPFont-Bold" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("JPFont-Bold", bold_path))
        if "JPFont-Bold" in pdfmetrics.getRegisteredFontNames():
            return "JPFont-Bold"

    return "JPFont"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
FIXED_DIR = os.path.join(ASSETS_DIR, "fixed")
KAMI_DIR  = os.path.join(ASSETS_DIR, "kami")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

#NAME_RGB = (132, 88, 0)     # 鑑定士・お客様・誕生日の文字の色のRGB
#NAME_RGB = (140, 95, 5)     # 鑑定士・お客様・誕生日の文字の色のRGB
NAME_RGB = (150, 105, 15)     # 鑑定士・お客様・誕生日の文字の色のRGB
OMAKE_RGB = (127, 96, 0)     # 鑑定士・お客様・誕生日の文字の色のRGB

NAME_FONT_SIZE = 44         # 鑑定士・お客様・誕生日の文字サイズ
COVER_FONT_STYLE = "meiryo"  # "meiryo" フォントはメイリオ



ROLE_FILE = {
    "tenmei": "tenmei.pdf",
    "syukumei": "syukumei.pdf",
    "shimei": "shimei.pdf",
    "unmei": "unmei.pdf",
}

ROLE_BITS = {
    "tenmei": 1,
    "syukumei": 2,
    "shimei": 4,
    "unmei": 8,
}

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def must_exist(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"ファイルが見つかりません: {path}")
    return path

def make_placeholder_pdf(path: str, title: str, lines: list[str]) -> str:
    """overlayの代わりに、仮ページPDFを自動生成（1ページ）"""
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 18)
    c.drawString(48, h - 72, title)
    c.setFont("Helvetica", 12)
    y = h - 110
    for line in lines:
        c.drawString(48, y, line)
        y -= 18
    c.showPage()
    c.save()
    return path

import uuid





from reportlab.lib.utils import ImageReader

#==========================
# meta.json から神様名（漢字＋カナ）を読む
# ==========================
def load_kami_title(kami_no: int) -> tuple[str, str]:
    meta_path = os.path.join(KAMI_DIR, str(kami_no), "meta.json")

    if not os.path.exists(meta_path):
        print(f"⚠ meta.json not found: kami_no={kami_no} path={meta_path}")
        return "", ""

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except json.JSONDecodeError as e:
        print(f"⚠ JSONDecodeError in meta.json: kami_no={kami_no}")
        print(f"   path: {meta_path}")
        print(f"   error: {e}")
        # 落とさず進める（仮名）
        return f"神様{kami_no}", ""
    except Exception as e:
        print(f"⚠ meta.json read error: kami_no={kami_no} path={meta_path} err={e}")
        return "", ""

    name = str(meta.get("kami_name", "") or "").strip()
    kana = str(meta.get("kami_kana", "") or "").strip()
    kana = kana.replace("”", "").replace("“", "").strip()
    return name, kana

def load_kami_shrines(kami_no: int) -> list[tuple[str, str]]:
    """assets/kami/<no>/meta.json の shrines を [(name, pref), ...] で返す"""
    meta_path = os.path.join(KAMI_DIR, str(kami_no), "meta.json")
    if not os.path.exists(meta_path):
        return []

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        return []

    out: list[tuple[str, str]] = []
    for s in meta.get("shrines", []) or []:
        name = str(s.get("name", "") or "").strip()
        pref = str(s.get("pref", "") or "").strip()
        if name:
            out.append((name, pref))
    return out






#----------------------------------------------------------
# ベースPDFと同じサイズでoverlayを作る
#----------------------------------------------------------
def make_overlay_for_base(base_pdf_path: str, overlay_path: str, draw_fn) -> str:
    """baseのページサイズに合わせて overlay を作る（1ページ）"""
    font = setup_jp_font()

    base = PdfReader(base_pdf_path)
    page0 = base.pages[0]
    w = float(page0.mediabox.width)
    h = float(page0.mediabox.height)

    c = canvas.Canvas(overlay_path, pagesize=(w, h))
    draw_fn(c, w, h, font)
    c.showPage()
    c.save()
    return overlay_path



def merge_base_and_overlay(base_pdf: str, overlay_pdf: str, out_pdf: str) -> str:
    """base(1p) + overlay(1p) を重ねて 1p の完成PDFを作る"""
    base = PdfReader(base_pdf)
    over = PdfReader(overlay_pdf)
    page = base.pages[0]
    page.merge_page(over.pages[0])
    w = PdfWriter()
    w.add_page(page)
    with open(out_pdf, "wb") as f:
        w.write(f)
    return out_pdf

#--------グリッド座標を求める関数

def make_grid_overlay_for_base(base_pdf_path: str, overlay_path: str, step: int = 50):
    base = PdfReader(base_pdf_path)
    p0 = base.pages[0]
    w = float(p0.mediabox.width)
    h = float(p0.mediabox.height)

    c = canvas.Canvas(overlay_path, pagesize=(w, h))
    c.setFont("Helvetica", 7)

    x = 0
    while x <= w:
        c.line(x, 0, x, h)
        c.drawString(x + 2, 2, str(int(x)))
        x += step

    y = 0
    while y <= h:
        c.line(0, y, w, y)
        c.drawString(2, y + 2, str(int(y)))
        y += step

    c.showPage()
    c.save()

def merge_one_page(base_pdf: str, overlay_pdf: str, out_pdf: str):
    base = PdfReader(base_pdf)
    over = PdfReader(overlay_pdf)
    page = base.pages[0]
    page.merge_page(over.pages[0])
    w = PdfWriter()
    w.add_page(page)
    with open(out_pdf, "wb") as f:
        w.write(f)



def to_zenkaku_digits(s: str) -> str:
    """半角0-9を全角０-９に変換"""
    return s.translate(str.maketrans("0123456789", "０１２３４５６７８９"))



def format_birthday_ja(iso_yyyy_mm_dd: str) -> str:
    # "YYYY-MM-DD" -> "YYYY年MM月DD日"（数字は全角）
    y, m, d = iso_yyyy_mm_dd.split("-")
    s = f"{y}年{int(m):02d}月{int(d):02d}日"
    return to_zenkaku_digits(s)


def unique_gods_in_order(tenmei: int, syukumei: int, shimei: int, unmei: int) -> list[int]:
    """天命→宿命→使命→運命の順で走査して、初出だけ残す"""
    ordered = [tenmei, syukumei, shimei, unmei]
    seen = set()
    result = []
    for k in ordered:
        if k not in seen:
            seen.add(k)
            result.append(k)
    return result

def build_mask(kami_no: int, tenmei: int, syukumei: int, shimei: int, unmei: int) -> int:
    mask = 0
    if kami_no == tenmei:   mask |= ROLE_BITS["tenmei"]
    if kami_no == syukumei: mask |= ROLE_BITS["syukumei"]
    if kami_no == shimei:   mask |= ROLE_BITS["shimei"]
    if kami_no == unmei:    mask |= ROLE_BITS["unmei"]
    return mask  # 1..15

def fixed_pdf(no: int) -> str:
    return os.path.join(FIXED_DIR, f"{no:02d}.pdf")

def bonus_pdf(no: int) -> str:
    # 30〜42などを fixed に同じ番号で置く前提
    return os.path.join(FIXED_DIR, f"{no:02d}.pdf")

def course_pdf(no: int) -> str:
    return os.path.join(FIXED_DIR, f"{no:02d}.pdf")

def wrap_text(font_name: str, font_size: int, text: str, max_width: float) -> list[str]:
    """文字列を max_width に収まるように簡易折り返し（全角対応の超簡易版）"""
    lines = []
    cur = ""
    for ch in text:
        nxt = cur + ch
        if pdfmetrics.stringWidth(nxt, font_name, font_size) <= max_width:
            cur = nxt
        else:
            if cur:
                lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines

#---------------------------------------------------------
# おまけ　の計算に使います
#---------------------------------------------------------


# 1桁になるまで足す
def reduce_1_9(n: int) -> int:
    while n >= 10:
        n = sum(int(d) for d in str(n))
    return n

def year_kami_no(year: int) -> int:
    return reduce_1_9(sum(int(d) for d in str(year)))

def digitsum(n: int) -> int:
    return sum(int(d) for d in str(n))

def get_effective_year_month():
    now = datetime.now()
    y = now.year
    m = now.month
    d = now.day

    # 20日以降なら来月
    if d >= 20:
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1

    return y, m

def personal_year_kami_no_from_unmei(year: int, unmei_no: int) -> int:
    return reduce_1_9(digitsum(year) + int(unmei_no))


def month_kami_no(year: int, month: int) -> int:
    return reduce_1_9(digitsum(year) + digitsum(month))

def personal_month_kami_no(month_kami: int, unmei_no: int) -> int:
    return reduce_1_9(month_kami + int(unmei_no))

from reportlab.lib.utils import ImageReader

def draw_omake04_kami(c, w, h, title: str, kami_no: int):
    font = setup_jp_font()
    r, g, b = OMAKE_RGB
    c.setFillColorRGB(r/255, g/255, b/255)
    
    # タイトル（位置は仮）
    c.setFont(font, 60)
    c.drawString(100, h - 110, title)
    c.drawString(100+0.6, h - 110, title)
    c.drawString(100+1.2, h - 110, title)

    # カード（位置は仮）
    card_w, card_h = 130, 180
    x = 250
    y = h - 130

    photo_path = os.path.join(KAMI_DIR, str(kami_no), "photo.png")
    if os.path.exists(photo_path):
        img = ImageReader(photo_path)
        c.drawImage(img, x, y - card_h, width=card_w, height=card_h, mask="auto")
    else:
        c.rect(x, y - card_h, card_w, card_h)
    
    # ---------------------------
    # ★ 神様名（漢字＋カナ）を表示（追加）
    # ---------------------------
    # ★ 神様名（漢字＋カナ）を表示（追加）
    kami_name, kami_kana = load_kami_title(kami_no)

    # ここで色を鑑定士の色にする
    #set_fill_rgb255(c, NAME_RGB)

    base_y = (y - card_h) + 50

    c.setFont(font, 60)
    c.drawCentredString( 650, base_y, kami_name)
    c.drawCentredString( 650+0.6, base_y, kami_name)
    c.drawCentredString( 650+1.2, base_y, kami_name)

    #if kami_kana:
    #    c.setFont(font, 60)
    #    c.drawCentredString(x + card_w / 2, base_y - 14, kami_kana)

# もし後続で黒に戻したいなら（必要なら）
# c.setFillColorRGB(0, 0, 0)


#---------------------------------------------------------
# main
#---------------------------------------------------------
def main(input_json_path: str):
    with open(input_json_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    out = build_pdf_from_payload(payload)
    print("✅ 出力しました:", out)
    return out


def build_pdf_from_payload(payload: dict) -> str:
    ensure_dir(OUTPUTS_DIR)

    reader_name = payload["reader_name"]
    client_name = payload["client_name"]
    birthday    = payload["birthday"]  # YYYY-MM-DD
    tenmei      = int(payload["tenmei"])
    syukumei    = int(payload["syukumei"])
    shimei      = int(payload["shimei"])
    unmei       = int(payload["unmei"])
    include_bonus  = bool(payload.get("include_bonus", True))
    include_course = bool(payload.get("include_course", False))

    uniq = unique_gods_in_order(tenmei, syukumei, shimei, unmei)

    # 出力先（Web運用を考えるならUUID付け推奨）
    out_pdf_path = payload.get("output_pdf_path")
    if not out_pdf_path:
        today = datetime.now().strftime("%y%m%d")
        tag = uuid.uuid4().hex[:8]  # ★同名衝突防止
        out_pdf_path = os.path.join(OUTPUTS_DIR, f"鑑定書_{client_name}_{today}_{tag}.pdf")

    # tmp_dir（Web運用なら毎回ユニークが安全）
    tmp_dir = os.path.join(OUTPUTS_DIR, "_tmp_pages", uuid.uuid4().hex[:8])
    ensure_dir(tmp_dir)

    #----------------------------------------------
    #表紙：cover.pdf に「鑑定士名」を重ねる
    #----------------------------------------------
    cover_base = must_exist(os.path.join(FIXED_DIR, "cover.pdf"))
    cover_overlay = os.path.join(tmp_dir, "cover_overlay.pdf")
    cover_done    = os.path.join(tmp_dir, "00_cover_done.pdf")

    def draw_cover(c, w, h, _unused_font):
        font = setup_jp_font()
        c.setFont(font, NAME_FONT_SIZE)

        r, g, b = NAME_RGB
        c.setFillColorRGB(r/255, g/255, b/255)

        x, y = 680, 100
        c.drawString(x, y, reader_name)
        c.drawString(x+0.6, y, reader_name)
        c.drawString(x+1.2, y, reader_name)
        c.drawString(x+1.8, y, reader_name)

    make_overlay_for_base(cover_base, cover_overlay, draw_cover)
    merge_base_and_overlay(cover_base, cover_overlay, cover_done)

    #----------------------------------------------
    #2ページ目：common02.pdf に「お客様名＋誕生日」を重ねる
    #----------------------------------------------
    p2_base = must_exist(os.path.join(FIXED_DIR, "common02.pdf"))
    p2_overlay = os.path.join(tmp_dir, "common02_overlay.pdf")
    p2_done    = os.path.join(tmp_dir, "02_common02_done.pdf")

    birthday_ja = format_birthday_ja(birthday)

    def draw_p2(c, w, h, _unused_font):
        font = setup_jp_font()
        r, g, b = NAME_RGB
        c.setFillColorRGB(r/255, g/255, b/255)

        c.setFont(font, 44)
        x, y = 480, 250
        c.drawString(x, y, f"{client_name} 様")
        c.drawString(x+0.6, y, f"{client_name} 様")
        c.drawString(x+1.2, y, f"{client_name} 様")
        c.drawString(x+1.8, y, f"{client_name} 様")

        c.setFont(font, 44)
        x, y = 420, 150
        c.drawString(x, y, f"{birthday_ja}生")
        c.drawString(x+0.6, y, f"{birthday_ja}生")
        c.drawString(x+1.2, y, f"{birthday_ja}生")
        c.drawString(x+1.8, y, f"{birthday_ja}生")

    make_overlay_for_base(p2_base, p2_overlay, draw_p2)
    merge_base_and_overlay(p2_base, p2_overlay, p2_done)

    #----------------------------------------------
    # 11ページ目：common11.pdf に「4柱の神様PNG」を配置
    #----------------------------------------------
    p11_base = must_exist(os.path.join(FIXED_DIR, "common11.pdf"))
    p11_overlay = os.path.join(tmp_dir, "common11_overlay.pdf")
    p11_done    = os.path.join(tmp_dir, "11_common11_done.pdf")

    def draw_p11(c, w, h, _unused_font):
        paths = [
            os.path.join(KAMI_DIR, str(tenmei),   "photo.png"),
            os.path.join(KAMI_DIR, str(syukumei), "photo.png"),
            os.path.join(KAMI_DIR, str(shimei),   "photo.png"),
            os.path.join(KAMI_DIR, str(unmei),    "photo.png"),
        ]
        paths = [must_exist(p) for p in paths]

        titles = [
            load_kami_title(tenmei),
            load_kami_title(syukumei),
            load_kami_title(shimei),
            load_kami_title(unmei),
        ]

        s = 0.95
        base_w = 160
        base_h = 210
        box_w = base_w * s
        box_h = base_h * s
        y = 170

        cx_list = [100, 350, 600, 850]
        xs = [cx - box_w / 2 for cx in cx_list]
        labels = ["天命", "宿命", "使命", "運命"]

        title_up = 6
        label_y = y + box_h + 44 + title_up

        font = setup_jp_font()
        r, g, b = NAME_RGB
        c.setFillColorRGB(r/255, g/255, b/255)

        for i, (x, p) in enumerate(zip(xs, paths)):
            cx = x + box_w / 2
            kanji, kana = titles[i]

            kanji_y = y + box_h + 22 + title_up
            kana_y  = y + box_h + 0 + title_up

            c.setFont(font, 22)
            c.drawCentredString(cx, kanji_y, kanji)

            c.setFont(font, 20)
            c.drawCentredString(cx, kana_y, kana)

            img = ImageReader(p)
            c.drawImage(img, x, y, width=box_w, height=box_h, mask="auto",
                        preserveAspectRatio=True, anchor="c")

            c.setFont(font, 22)
            c.drawCentredString(cx, label_y, labels[i])
            c.drawCentredString(cx+0.6, label_y, labels[i])
            c.drawCentredString(cx+1.2, label_y, labels[i])

    make_overlay_for_base(p11_base, p11_overlay, draw_p11)
    merge_base_and_overlay(p11_base, p11_overlay, p11_done)

    #----------------------------------------------
    # 29ページ目：神社情報
    #----------------------------------------------
    p29_base    = must_exist(os.path.join(FIXED_DIR, "common29.pdf"))
    p29_overlay = os.path.join(tmp_dir, "common29_overlay.pdf")
    p29_done    = os.path.join(tmp_dir, "29_common29_done.pdf")

    def draw_p29(c, w, h, _unused_font):
        font = setup_jp_font()
        r, g, b = NAME_RGB
        c.setFillColorRGB(r/255, g/255, b/255)

        area_left  = 410
        area_right = w - 40
        area_width = area_right - area_left

        top_y    = h - 120
        bottom_y = 60

        kami_list = uniq[:]
        n = len(kami_list)
        if n == 0:
            return
        if n > 4:
            kami_list = kami_list[:4]
            n = 4

        card_w = 110
        card_h = 150
        gap = 18

        total_w = n * card_w + (n - 1) * gap
        start_x = area_left + (area_width - total_w) / 2

        text_size = 12
        line_h = 18
        max_lines_per_kami = 13

        for i, kami_no in enumerate(kami_list):
            x = start_x + i * (card_w + gap)
            y = top_y

            photo_path = os.path.join(KAMI_DIR, str(kami_no), "photo.png")
            if os.path.exists(photo_path):
                img = ImageReader(photo_path)
                c.drawImage(img, x, y - card_h, width=card_w, height=card_h,
                            mask="auto", preserveAspectRatio=True, anchor="c")
            else:
                c.rect(x, y - card_h, card_w, card_h)

            shrines = load_kami_shrines(kami_no)
            ty = y - card_h - 10 - line_h
            c.setFont(font, text_size)
            max_text_width = card_w

            SPECIAL_LINES = {
                11: [
                    "■裸形弁財天座像\n(二臂)鶴岡八幡宮\n(神奈川県)",
                    "■裸形弁天座像\n(二臂)江ノ島\n(神奈川県)",
                    "■弁財天立像\n(八臂)東大寺\n(奈良県)",
                    "■弁財天立像孝恩寺\n(大阪府)",
                ],
                2: [
                    "■内宮(皇大神宮)\n別宮の月讀宮\n(三重県)",
                    "■外宮(豊受大神宮)\n別宮に月夜見宮\n(三重県)",
                    "■出羽三山の\n一社の月山神社\n(山形県)",
                ],
                9: [
                    "■醍醐寺吉祥天\n立像(京都府)",
                    "■観世音寺吉祥天\n立像(福岡県)",
                    "■當麻寺立像\n(奈良県)",
                    "■園城寺立像\n(滋賀県)",
                    "■西宮神社\n(兵庫県)",
                ],
            }

            out_lines: list[str] = []

            if kami_no in SPECIAL_LINES:
                for s in SPECIAL_LINES[kami_no]:
                    parts2 = s.split("\n")
                    for j, part in enumerate(parts2):
                        if j >= 1:
                            part = "  " + part
                        out_lines.extend(wrap_text(font, text_size, part, max_text_width))
            else:
                if not shrines:
                    out_lines = ["■（神社情報なし）"]
                else:
                    for name, pref in shrines:
                        name = (name or "").strip()
                        parts3 = [p.strip() for p in name.split("・") if p.strip()]

                        if len(parts3) >= 2:
                            out_lines.extend(wrap_text(font, text_size, f"■{parts3[0]}", max_text_width))
                            for p in parts3[1:]:
                                out_lines.extend(wrap_text(font, text_size, f"  {p}", max_text_width))
                                out_lines.extend(wrap_text(font, text_size, f"（{pref}）", max_text_width))
                        else:
                            s = f"■{name}\n（{pref}）"
                            for part in s.split("\n"):
                                out_lines.extend(wrap_text(font, text_size, part, max_text_width))

            if len(out_lines) > max_lines_per_kami:
                out_lines = out_lines[:max_lines_per_kami]
                out_lines[-1] = out_lines[-1] + "…"

            for line in out_lines:
                if ty < bottom_y:
                    break
                LEFT_PAD = 6
                c.drawString(x + LEFT_PAD, ty, line)
                ty -= line_h

    make_overlay_for_base(p29_base, p29_overlay, draw_p29)
    merge_base_and_overlay(p29_base, p29_overlay, p29_done)

    # --- 結合台本 ---
    parts: list[str] = []
    parts.append(cover_done)
    parts.append(p2_done)
    parts.append(must_exist(os.path.join(FIXED_DIR, "common03.pdf")))
    parts.append(p11_done)

    role_map = {"tenmei": tenmei, "syukumei": syukumei, "shimei": shimei, "unmei": unmei}
    for role, kami_no in role_map.items():
        f = os.path.join(KAMI_DIR, str(kami_no), ROLE_FILE[role])
        parts.append(must_exist(f))

    parts.append(must_exist(os.path.join(FIXED_DIR, "common16.pdf")))

    for k in uniq:
        folder = os.path.join(KAMI_DIR, str(k))
        parts.append(must_exist(os.path.join(folder, "p1.pdf")))
        mask = build_mask(k, tenmei, syukumei, shimei, unmei)
        parts.append(must_exist(os.path.join(folder, "p2", f"mask_{mask}.pdf")))
        parts.append(must_exist(os.path.join(folder, "p3.pdf")))

    parts.append(p29_done)

    now = datetime.now()
    y_now = now.year

    if include_bonus:
        parts.append(must_exist(os.path.join(FIXED_DIR, "common_omake01_03.pdf")))

        om04_base = must_exist(os.path.join(FIXED_DIR, "common_omake_04.pdf"))

        kami_year = year_kami_no(y_now)
        om04_overlay = os.path.join(tmp_dir, "omake04_year_overlay.pdf")
        om04_done    = os.path.join(tmp_dir, "omake04_year_done.pdf")

        def draw_year(c, w, h, _):
            draw_omake04_kami(c, w, h, f"{y_now}年のご守護は", kami_year)

        make_overlay_for_base(om04_base, om04_overlay, draw_year)
        merge_base_and_overlay(om04_base, om04_overlay, om04_done)
        parts.append(om04_done)

        parts.append(must_exist(os.path.join(FIXED_DIR, "common_omake_05.pdf")))

        y_eff, m_eff = get_effective_year_month()
        kami_month = month_kami_no(y_eff, m_eff)
        kami_personal_month = personal_month_kami_no(kami_month, unmei)

        om04_overlay = os.path.join(tmp_dir, "omake04_month_overlay.pdf")
        om04_done    = os.path.join(tmp_dir, "omake04_month_done.pdf")

        def draw_month(c, w, h, _):
            draw_omake04_kami(c, w, h, f"{y_eff}年{m_eff}月のご守護は", kami_month)

        make_overlay_for_base(om04_base, om04_overlay, draw_month)
        merge_base_and_overlay(om04_base, om04_overlay, om04_done)
        parts.append(om04_done)

        parts.append(must_exist(os.path.join(FIXED_DIR, "common_omake_06.pdf")))

        kami_personal_year = personal_year_kami_no_from_unmei(y_now, unmei)

        om04_overlay = os.path.join(tmp_dir, "omake04_personal_year_overlay.pdf")
        om04_done    = os.path.join(tmp_dir, "omake04_personal_year_done.pdf")

        def draw_personal_year(c, w, h, _):
            draw_omake04_kami(c, w, h, f"{y_now}年のあなたのご守護は", kami_personal_year)

        make_overlay_for_base(om04_base, om04_overlay, draw_personal_year)
        merge_base_and_overlay(om04_base, om04_overlay, om04_done)
        parts.append(om04_done)

        parts.append(must_exist(os.path.join(FIXED_DIR, "common_omake_07.pdf")))

        base1 = must_exist(os.path.join(KAMI_DIR, str(kami_personal_month), "omake_month1.pdf"))
        base23 = must_exist(os.path.join(KAMI_DIR, str(kami_personal_month), "omake_month23.pdf"))

        overlay1 = os.path.join(tmp_dir, "omake_month1_overlay.pdf")
        done1    = os.path.join(tmp_dir, "omake_month1_done.pdf")

        def draw_month_title(c, w, h, _):
            font = setup_jp_font()
            r, g, b = OMAKE_RGB
            c.setFillColorRGB(r/255, g/255, b/255)
            c.setFont(font, 60)
            x = 260
            y = h - 70
            c.drawString(x, y, f"{y_eff}年{m_eff}月")
            c.drawString(x+0.6, y, f"{y_eff}年{m_eff}月")
            c.drawString(x+1.2, y, f"{y_eff}年{m_eff}月")

        make_overlay_for_base(base1, overlay1, draw_month_title)
        merge_base_and_overlay(base1, overlay1, done1)
        parts.append(done1)
        parts.append(base23)

    if include_course:
        parts.append(must_exist(os.path.join(FIXED_DIR, "common_present01.pdf")))

    writer = PdfWriter()
    for p in parts:
        reader = PdfReader(p)
        for page in reader.pages:
            writer.add_page(page)

    ensure_dir(os.path.dirname(out_pdf_path) or ".")
    with open(out_pdf_path, "wb") as f:
        writer.write(f)

    return out_pdf_path
