import os
import re
from datetime import date
import pandas as pd
import streamlit as st

from build_pdf import build_pdf_from_payload

APP_TITLE = "金運の神様占い｜鑑定書メーカー（入力フォーム）"
DEFAULT_OUTPUT_DIR = "outputs"
DEFAULT_CSV_PATH = os.path.join("data", "gods.csv")

ROLE_ORDER = ["tenmei", "syukumei", "shimei", "unmei"]
ROLE_LABELS = {"tenmei": "天命", "syukumei": "宿命", "shimei": "使命", "unmei": "運命"}

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def sanitize_filename_component(text: str) -> str:
    if text is None:
        return ""
    text = text.strip()
    text = re.sub(r'[\\/:*?"<>|]+', "_", text)
    text = re.sub(r"_+", "_", text)
    return text

def make_base_filename(client_name: str, created: date) -> str:
    yy = f"{created.year % 100:02d}"
    mm = f"{created.month:02d}"
    dd = f"{created.day:02d}"
    safe_name = sanitize_filename_component(client_name) or "noname"
    return f"鑑定書_{safe_name}_{yy}{mm}{dd}.pdf"

def uniquify_path(directory: str, filename: str) -> str:
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(directory, filename)
    if not os.path.exists(candidate):
        return candidate
    i = 1
    while True:
        cand_name = f"{base}({i}){ext}"
        candidate = os.path.join(directory, cand_name)
        if not os.path.exists(candidate):
            return candidate
        i += 1

def load_gods_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    required = {"kami_no", "kami_id", "name_kanji", "name_kana"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSVに必要な列がありません: {missing}")

    for col in ["kami_id", "name_kanji", "name_kana"]:
        df[col] = df[col].astype(str).str.strip()

    df["kami_no"] = pd.to_numeric(df["kami_no"], errors="raise").astype(int)
    df["label"] = df.apply(lambda r: f'{r["kami_no"]} {r["name_kanji"]}（{r["name_kana"]}）', axis=1)
    return df.sort_values("kami_no").reset_index(drop=True)

st.set_page_config(page_title=APP_TITLE, layout="centered")
st.title(APP_TITLE)

#with st.sidebar:
    #st.header("設定")
    #csv_path = st.text_input("12柱CSVパス", value=DEFAULT_CSV_PATH)
    #output_dir = st.text_input("出力フォルダ", value=DEFAULT_OUTPUT_DIR)
    #st.caption("※ CSVと出力フォルダはローカルパス指定です。")

try:
    gods_df = load_gods_csv(DEFAULT_CSV_PATH)
except Exception as e:
    st.error(f"CSVの読み込みに失敗しました: {e}")
    st.stop()

labels = gods_df["label"].tolist()
label_to_no = dict(zip(labels, gods_df["kami_no"].tolist()))

st.subheader("基本情報")
reader_name = st.text_input("鑑定士名", value="")
client_name = st.text_input("クライアント名", value="")
from datetime import date

birthday = st.date_input(
    "クライアントの誕生日",
    min_value=date(1925, 1, 1),
    max_value=date.today(),
    format="YYYY/MM/DD"
)

st.caption("鑑定書内の表示は yyyy年mm月dd日 に整形します（内部は日付として保持）。")

st.subheader("4柱の神様（12柱から選択）")
cols = st.columns(2)
selected = {}

with cols[0]:
    selected["tenmei"] = st.selectbox("天命", options=labels, index=0)
    selected["syukumei"] = st.selectbox("宿命", options=labels, index=0)

with cols[1]:
    selected["shimei"] = st.selectbox("使命", options=labels, index=0)
    selected["unmei"] = st.selectbox("運命", options=labels, index=0)


selected_no = {role: int(label_to_no[selected[role]]) for role in ROLE_ORDER}

st.subheader("オプション")
include_bonus = st.checkbox("おまけページを付ける（運勢・年/月の神様など）", value=True)
include_course = st.checkbox("講座案内・プレゼントページを付ける（講座のお知らせ等）", value=False)

st.subheader("出力")
created = date.today()

def validate():
    if not reader_name.strip():
        return "鑑定士名が未入力です。"
    if not client_name.strip():
        return "クライアント名が未入力です。"
    if birthday is None:
        return "誕生日が未入力です。"
    return None

err = validate()
if err:
    st.warning(err)

if st.button("鑑定書PDF生成", type="primary", disabled=bool(err)):
    payload = {
        "reader_name": reader_name.strip(),
        "client_name": client_name.strip(),
        "birthday": birthday.isoformat(),
        "tenmei": selected_no["tenmei"],
        "syukumei": selected_no["syukumei"],
        "shimei": selected_no["shimei"],
        "unmei": selected_no["unmei"],
        "include_bonus": bool(include_bonus),
        "include_course": bool(include_course),
        "created": created.isoformat(),
    }
    with st.spinner("PDFを生成しています..."):
        try:
            out_pdf_path = build_pdf_from_payload(payload)
        except Exception as e:
            st.error(f"PDF生成に失敗しました: {e}")
            st.stop()

    st.success(f"PDFを生成しました: {out_pdf_path}")

    with open(out_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    st.download_button(
        label="PDFをダウンロード",
        data=pdf_bytes,
        file_name=os.path.basename(out_pdf_path),
        mime="application/pdf",
    )