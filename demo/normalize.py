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

st.markdown(""""
# データ収集ポータル(仮)

## 利用手順

1. 項目定義のアップロード
    * 収集したいデータの項目と、収集方法を定義したファイルをアップロードします
2. 収集対象会社の選択
    * 収集したい対象の会社を選択します
3. ダウンロード
    * 結果をダウンロードします。

## 1. 項目定義のアップロード

収集したいデータの項目と、収集方法を定義したファイルをアップロードします。  
事前に伺った自然エネルギーについて、項目定義を行ったファイルをすでに作成しています。  
以下のリンクからダウンロードできますので、ダウンロードした後そのままアップロードしてみてください。

"""
)

# Upload Criteria

criteria_path = os.path.join(os.path.dirname(__file__), "./criteria.csv")
criteria_link = get_download_link(
                    pd.read_csv(criteria_path, index_col=False), 
                    "criteria.csv", "サンプル項目定義書")
st.markdown(criteria_link, unsafe_allow_html=True)

uploaded = st.file_uploader("アップロードはこちらから", type=["csv"])

if uploaded is not None:
    criteria = pd.read_csv(uploaded, index_col=False)
    st.dataframe(criteria)

st.markdown("""
ちなみに、項目定義の各項目の名前と意味は以下のようになっています。  
※現時点では暫定版です。

* name: チェック項目の名称
* type: チェック方法
* criteria: チェック条件(検索のためのキーワードなど)

""")

# Select Target

st.markdown("""
## 2. 収集対象会社の選択

データを収集したい対象の会社を選択します。  
※今のところ以下の会社のみ取得可能です。

* TIS株式会社
* エヌ・ティ・ティデータ株式会社

⇒選択した後、少し時間がたつと収集結果が表示されます。

""")
selected_indices = st.multiselect("対象会社の選択:", companies.name_ja.tolist())
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

st.markdown("""
## 3. ダウンロード

収集した結果をCSVでダウンロード可能です。  

""")

if len(normalized) > 0:
    link = get_download_link(normalized, "normalized_result.csv", "収集整理結果")
    st.markdown(link, unsafe_allow_html=True)

st.markdown("""
CSVはUTF-8でエンコードされているため、Excelで開く際は以下手順で開く必要があります(お手数をおかけします)。

http://www4.synapse.ne.jp/yone/excel2019/excel2019_csv_utf8_2.html

""")