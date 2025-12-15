import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import hashlib
import os
import plotly.express as px


# ================================
# Streamlit 設定
# ================================
st.set_page_config(page_title="MLB怪我分析（Plotly版）", layout="wide")
st.title("⚾ MLB怪我分析ツール B版（Plotly色付きヒートマップ・改善版）")

DATA_CSV = "injury_data.csv"
HASH_FILE = "html_hash.txt"

# ================================
# チームマップ
# ================================
team_map = {
    "Arizona Diamondbacks": "Arizona",
    "Atlanta Braves": "Atlanta",
    "Baltimore Orioles": "Baltimore",
    "Boston Red Sox": "Boston",
    "Chicago Cubs": "Chi. Cubs",
    "Chicago White Sox": "Chi. White Sox",
    "Cincinnati Reds": "Cincinnati",
    "Cleveland Guardians": "Cleveland",
    "Colorado Rockies": "Colorado",
    "Detroit Tigers": "Detroit",
    "Houston Astros": "Houston",
    "Kansas City Royals": "Kansas City",
    "Los Angeles Angels": "L.A. Angels",
    "Los Angeles Dodgers": "L.A. Dodgers",
    "Miami Marlins": "Miami",
    "Milwaukee Brewers": "Milwaukee",
    "Minnesota Twins": "Minnesota",
    "New York Mets": "N.Y. Mets",
    "New York Yankees": "N.Y. Yankees",
    "Oakland Athletics": "Athletics",
    "Philadelphia Phillies": "Philadelphia",
    "Pittsburgh Pirates": "Pittsburgh",
    "San Diego Padres": "San Diego",
    "San Francisco Giants": "San Francisco",
    "Seattle Mariners": "Seattle",
    "St. Louis Cardinals": "St. Louis",
    "Tampa Bay Rays": "Tampa Bay",
    "Texas Rangers": "Texas",
    "Toronto Blue Jays": "Toronto",
    "Washington Nationals": "Washington"
}

reverse_map = {v: k for k, v in team_map.items()}

# ================================
# ハッシュ処理
# ================================
def get_html_hash(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()

def save_hash(hash_value):
    with open(HASH_FILE, "w") as f:
        f.write(hash_value)

def load_hash():
    if not os.path.exists(HASH_FILE):
        return None
    return open(HASH_FILE).read().strip()

# ================================
# CSV 読み込み
# ================================
def load_data_from_csv():
    if not os.path.exists(DATA_CSV):
        return None
    return pd.read_csv(DATA_CSV)

# ================================
# スクレイピング
# ================================
def scrape_injury_data():
    url = "https://www.cbssports.com/mlb/injuries/"
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")
    tables = pd.read_html(url)

    team_names = [h4.get_text(strip=True) for h4 in soup.find_all("h4")]

    all_records = []
    for team_short, df_tmp in zip(team_names, tables):
        full_name = None
        for full, short in team_map.items():
            if short == team_short:
                full_name = full

        df_tmp["TEAM"] = full_name
        all_records.append(df_tmp)

    df = pd.concat(all_records, ignore_index=True)

    df.to_csv(DATA_CSV, index=False)
    save_hash(get_html_hash(html))
    return df

# ================================
# データ取得（更新検知 & キャッシュ）
# ================================
def fetch_injury_data(force_update=False):
    url = "https://www.cbssports.com/mlb/injuries/"

    if force_update:
        st.warning("🔄 手動更新：最新データ取得中…")
        return scrape_injury_data()

    html = requests.get(url).text
    current_hash = get_html_hash(html)
    old_hash = load_hash()

    if os.path.exists(DATA_CSV) and current_hash == old_hash:
        st.info("✔ キャッシュを使用（HTML変更なし）")
        return load_data_from_csv()

    st.warning("🔄 データ更新を検知 → 最新データ取得")
    return scrape_injury_data()

# ================================
# 分類処理
# ================================
def classify_player(pos):
    if isinstance(pos, str) and any(p in pos for p in ["SP", "RP", "P"]):
        return "Pitcher"
    return "Fielder"

def extract_injury_part(text):
    if not isinstance(text, str):
        return "その他"

    keywords = {
        "肘": ["elbow"],
        "肩": ["shoulder"],
        "膝": ["knee"],
        "背中": ["back"],
        "前腕": ["forearm"],
        "手首": ["wrist"],
        "股関節": ["hip"],
        "ハムストリング": ["hamstring"],
        "腹部": ["abdomen"],
        "指": ["finger"],
        "手": ["hand"]
    }

    t = text.lower()
    for jp, keys in keywords.items():
        if any(k in t for k in keys):
            return jp

    return "その他"

# ================================
# Pivot作成
# ================================
def create_pivot(df):
    df["TeamFull"] = df["TEAM"]

    pivot = df.pivot_table(
        index="TeamFull",
        columns="injury_part_jp",
        values="Player",
        aggfunc="count",
        fill_value=0
    )

    pivot = pivot.reindex(list(team_map.keys()), fill_value=0)
    pivot = pivot[pivot.sum().sort_values(ascending=False).index]

    return pivot

# ================================
# Plotly 色付きヒートマップ
# ================================
def plotly_heatmap(pivot, title, colorscale):
    st.subheader(title)

    fig = px.imshow(
        pivot,
        text_auto=True,
        aspect="auto",
        color_continuous_scale=colorscale,
        labels=dict(color="人数"),
        zmin=0,
        zmax=pivot.values.max(),
    )

    # 日本語フォント対応 + レイアウト調整
    fig.update_layout(
        xaxis_title="怪我部位",
        yaxis_title="チーム名",
        font=dict(size=14, family="Arial, Yu Gothic, Hiragino Sans"),
        height=900,
        margin=dict(l=40, r=40, t=40, b=40),
    )

    fig.update_xaxes(
        side="top"
    )
    st.plotly_chart(fig, use_container_width=True)





# ================================
# メイン処理
# ================================
force_update = st.button("🔄 手動更新（最新データ取得）")

st.markdown(
    """
    <div style="font-size: 12px; color: gray; margin-top: -6px; padding-bottom: 20px;">
    ※ データ取得元：
    <a href="https://www.cbssports.com/mlb/injuries/" target="_blank">
    CBS Sports – MLB Injuries
    </a>
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown(
    """
    ※ 本アプリは公開情報をもとにした分析・可視化ツールです。  
    データの正確性・完全性を保証するものではありません。
    """
)

df = fetch_injury_data(force_update)

df["PlayerType"] = df["Position"].apply(classify_player)
df["injury_part_jp"] = df["Injury"].apply(extract_injury_part)

pitcher_df = df[df["PlayerType"] == "Pitcher"]
fielder_df = df[df["PlayerType"] == "Fielder"]

pivot_pitcher = create_pivot(pitcher_df)
pivot_fielder = create_pivot(fielder_df)

# ================================
# 表示（投手：赤 / 野手：青）
# ================================
plotly_heatmap(pivot_pitcher, "🔴 投手のチーム別怪我人数", "Reds")
plotly_heatmap(pivot_fielder, "🔵 野手のチーム別怪我人数", "Blues")

