import os
import base64
import unicodedata
import streamlit as st
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup


file_path = os.path.join(os.path.dirname(__file__), "./companies.csv")
companies = pd.read_csv(file_path, index_col=False)


def normalize_name(t):
    if isinstance(t, str):
        return unicodedata.normalize("NFKC", t)
    else:
        return t

companies["name"] = companies["name"].apply(normalize_name)
companies["name_ja"] = companies["name_ja"].apply(normalize_name)


# Download
def get_download_link(df, file_name, file_label):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{file_name}">Download {file_label}</a>'
    return href

# Application

st.title("Sustainability Data Labo")

# Upload Criteria

st.write("正規化の定義をアップロードしてください")
st.markdown("""
* name: チェック項目の名称
* type: チェック方法
* criteria: チェック条件(検索のためのキーワードなど)

以下からサンプルの定義書をダウンロードできるので、それを使うことも可能です。
""")

criteria_path = os.path.join(os.path.dirname(__file__), "./criteria.csv")
criteria_link = get_download_link(
                    pd.read_csv(criteria_path, index_col=False), 
                    "criteria.csv", "サンプル定義書")
st.markdown(criteria_link, unsafe_allow_html=True)

uploaded = st.file_uploader("Upload Normalize Definition", type=["csv"])

if uploaded is not None:
    criteria = pd.read_csv(uploaded, index_col=False)
    st.dataframe(criteria)

# Select Target

st.write("データを取得したい会社を選択してください。")
st.markdown("""
※今のところ以下の会社のみデータを入れています。
* TIS株式会社
* エヌ・ティ・ティデータ株式会社
""")
selected_indices = st.multiselect("Select companies:", companies.name_ja.tolist())
selecteds = companies[companies["name_ja"].isin(selected_indices)]


# Normalize
def search(source, query):
    bodies = []
    if source.endswith(".pdf"):
        content = read_pdf(source)
    else:
        url, selector = source.split()
        r = requests.get(url)
        soup = BeautifulSoup(r.content, "html.parser")
        contents = soup.select(selector)
        if contents is not None:
            for c in contents:
                text = c.get_text("\n")
                texts = text.split("\n\n")
                bodies += texts

    result = []
    for b in bodies:
        keywords = query.split()
        for k in keywords:
            if k in b:
                result.append(b)
                break
    
    return result


normalized = []

for i, row in selecteds.iterrows():
    r = {}
    source = None
    if "website" in row:
        source = row["website"]

    for j, c in criteria.iterrows():
        if c["type"] == "check_column":
            if c["criteria"] in row:
                r[c["name"]] = "〇"
            else:
                r[c["name"]] = "×"
        elif c["type"] == "content_exist":
            query = c["criteria"]
            result = search(source, query)
            r[c["name"]] = "〇" if len(result) > 0 else "×"
        elif c["type"] == "content_extract":
            result = search(source, query)
            if len(result) > 0:
                r[c["name"]] = result[0]
    r["ソース"] = source
    normalized.append(r)


normalized = pd.DataFrame(normalized)

if len(normalized) > 0:
    st.dataframe(normalized)
    link = get_download_link(normalized, "normalized_result.csv", "収集整理結果")
    st.markdown(link, unsafe_allow_html=True)
