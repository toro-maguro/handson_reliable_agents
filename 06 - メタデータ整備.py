# Databricks notebook source
# MAGIC %md
# MAGIC # 06 — メタデータ整備
# MAGIC
# MAGIC ### このモジュールの到達目標
# MAGIC - 列に**説明（UC コメント）**を付け、テーブル・列の意味を Genie に伝える
# MAGIC - 業務の言葉と列をつなぐ**同義語（シノニム）**を登録する
# MAGIC - サンプル質問を登録して、利用者が使い始めやすくする
# MAGIC
# MAGIC ### 所要時間
# MAGIC 約 15 分
# MAGIC
# MAGIC メタデータは「Genie に業務の言葉を教える」いちばん手軽な一歩です。列の意味・別名・欠損の注意を
# MAGIC 伝えるだけで、「売上」「店舗」「悪いレビュー」などの言葉を正しい列・正しい集計に対応づけられます。

# COMMAND ----------

# MAGIC %md
# MAGIC ## 環境セットアップ

# COMMAND ----------

# MAGIC %run ./Includes/Classroom-Setup-06

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 1 — 列とテーブルに説明（UC コメント）を付ける
# MAGIC Genie は **Unity Catalog の列コメント／テーブルコメント**を自動で参照します。まず、6 問に効く
# MAGIC 「意味・結合キー・欠損の注意」を `ALTER TABLE ... COMMENT` で付けます。何度実行しても同じ結果です。

# COMMAND ----------

def set_comment(table: str, column: str, comment: str):
    """列コメントを冪等に付与（Genie が自動参照）。"""
    c = comment.replace("'", "''")
    spark.sql(f"ALTER TABLE {fq(table)} ALTER COLUMN {column} COMMENT '{c}'")


def set_table_comment(table: str, comment: str):
    c = comment.replace("'", "''")
    spark.sql(f"COMMENT ON TABLE {fq(table)} IS '{c}'")


# --- 取引 ---------------------------------------------------------------------
set_table_comment("sales_transactions_gold", "1 行 = 1 購入。customerID / franchiseID で顧客・店舗に結合する。")
set_comment("sales_transactions_gold", "totalPrice",
            "1 取引の売上金額。売上・収益はこの列。SUM(totalPrice) で総売上や店舗別・地域別のパフォーマンスを比較する。")
set_comment("sales_transactions_gold", "customerID", "顧客への外部キー（sales_customers_gold.customerID）。")
set_comment("sales_transactions_gold", "franchiseID", "店舗への外部キー（sales_franchises_gold.franchiseID）。")
set_comment("sales_transactions_gold", "quantity", "販売数量。")

# --- 顧客 ---------------------------------------------------------------------
set_table_comment("sales_customers_gold", "1 行 = 1 顧客。重複や null は無い。総顧客数は COUNT(DISTINCT customerID)。customerID で取引に結合する。")
set_comment("sales_customers_gold", "customerID", "主キー。非 null で一意。総顧客数は COUNT(DISTINCT customerID)。取引への結合キー。")

# --- 店舗 ---------------------------------------------------------------------
set_table_comment("sales_franchises_gold", "1 行 = 1 店舗（フランチャイズ）。同名店舗が別ロケーションに複数ある。仕入先の結合は LEFT JOIN を使う。")
set_comment("sales_franchises_gold", "franchiseID",
            "一意な店舗 ID。取引（transactions.franchiseID）とレビュー（reviews.ref）の結合キー。集計時は franchiseID と city を必ず GROUP BY に入れる（同名店舗があるため）。")
set_comment("sales_franchises_gold", "name", "店舗名。同名店舗が複数あるため、franchiseID / city で一意化する。")
set_comment("sales_franchises_gold", "country",
            "店舗の国。地域区分（APJ / AMER / EMEA）の元。取り得る値: US, Canada, Japan, Australia, Netherlands, France, Germany, Italy, Sweden。")
set_comment("sales_franchises_gold", "supplierID",
            "仕入先への外部キー。48 店舗中 27 のみ一致し 21 は不一致（孤立）。仕入先と結合するときは silent drop を避けるため LEFT JOIN を使う。")

# --- 仕入先 -------------------------------------------------------------------
set_table_comment("sales_suppliers_gold", "1 行 = 1 仕入先。supplierID で店舗に結合する。")
set_comment("sales_suppliers_gold", "supplierID", "一意な仕入先 ID。店舗（franchises.supplierID）への結合キー。")

# --- レビュー -----------------------------------------------------------------
set_table_comment("media_customer_reviews_gold", "1 行 = 1 レビュー。ref で店舗に結合する。flag が感情（sentiment）。")
set_comment("media_customer_reviews_gold", "ref",
            "店舗への外部キー（sales_franchises_gold.franchiseID）。集計は ref・name・city を SELECT / GROUP BY する（店名は非一意）。")
set_comment("media_customer_reviews_gold", "flag",
            "レビューの感情（sentiment）。値は positive / negative / mixed。悪いレビュー=negative、良い=positive、どちらでもない=mixed。生テキストではなくこの列で絞り込む。")

print("UC 列コメント・テーブルコメントを付与しました（Genie が自動参照します）")

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #43a047;background:#e8f5e9;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#2e7d32;">✔ 期待される結果</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">
# MAGIC   コメント付与のメッセージが表示される。カタログエクスプローラでテーブルを開くと、列に説明が付いています。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 2 — 同義語（シノニム）とサンプル質問を Genie に登録する
# MAGIC 利用者は「売上」「感情」「地域」といった**業務の言葉**で質問します。列名（`totalPrice`, `flag` …）と
# MAGIC これらの言葉をつなぐのが**同義語（synonyms）**です。あわせて、よく使う**サンプル質問**を登録します。
# MAGIC これらは知識ストア（`column_configs` / `config.sample_questions`）に **API で書き込み**ます。

# COMMAND ----------

space_id = load_space_id()
assert space_id, "先に 03 / 04 を実行してください。"

ss, etag = genie_get(space_id)


def _set_column_configs(ss, table, configs):
    """指定テーブルに column_configs を設定（column_name 昇順が必須）。"""
    fqid = fq(table)
    for t in ss["data_sources"]["tables"]:
        if t["identifier"] == fqid:
            t["column_configs"] = sorted(configs, key=lambda c: c["column_name"])
            return
    raise ValueError(f"テーブルが見つかりません: {fqid}")


# 取引: 売上金額・数量の別名
_set_column_configs(ss, "sales_transactions_gold", [
    {"column_name": "totalPrice",
     "description": ["売上・収益。SUM(totalPrice) で総売上やパフォーマンス比較。"],
     "synonyms": ["売上", "売上金額", "収益", "revenue", "sales", "total sales", "total revenue"]},
    {"column_name": "quantity", "description": ["販売数量。"], "synonyms": ["数量", "個数"]},
])

# 店舗: 国（地域区分の元）・店舗名
_set_column_configs(ss, "sales_franchises_gold", [
    {"column_name": "country",
     "description": ["店舗の国。地域区分（APJ / AMER / EMEA）の元。"], "synonyms": ["国"]},
    {"column_name": "name", "description": ["店舗名。同名あり→city / franchiseID で一意化。"],
     "synonyms": ["店舗", "支店", "店", "ロケーション"]},
])

# レビュー: 感情
_set_column_configs(ss, "media_customer_reviews_gold", [
    {"column_name": "flag",
     "description": ["レビューの感情。negative=悪い / positive=良い / mixed=どちらでもない。"],
     "synonyms": ["感情", "評価", "sentiment", "review sentiment"]},
])

# よく使う質問を最初から提示（固定 ID・昇順なので再実行しても増えない）
ss.setdefault("config", {})["sample_questions"] = sorted([
    {"id": "51000000000000000000000000000001", "question": ["地域別（APJ / AMER / EMEA）の総売上を教えて"]},
    {"id": "51000000000000000000000000000002", "question": ["売上トップ 5 の店舗はどこですか？"]},
    {"id": "51000000000000000000000000000003", "question": ["悪いレビューが多い店舗はどこですか？"]},
], key=lambda x: x["id"])

genie_update(space_id, ss, etag)
print("同義語・サンプル質問を登録しました")

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #43a047;background:#e8f5e9;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#2e7d32;">✔ 期待される結果</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">
# MAGIC   登録完了のメッセージが表示される。Genie の画面を開くと、サンプル質問が表示され、
# MAGIC   列に同義語が付いていることが確認できます。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 3 — 反映されたことを確認する
# MAGIC 書き戻した内容をもう一度取得し、同義語・サンプル質問が入っているかを確かめます。

# COMMAND ----------

ss2, _ = genie_get(space_id)
tx = next(t for t in ss2["data_sources"]["tables"] if t["identifier"] == fq("sales_transactions_gold"))
cfgs = {c["column_name"]: c for c in tx.get("column_configs", [])}
has_syn = "totalPrice" in cfgs and bool(cfgs["totalPrice"].get("synonyms"))
n_sample = len(ss2.get("config", {}).get("sample_questions", []))

checkpoint(
    f"メタデータ反映: 同義語つき列 {len(cfgs)} 件 / サンプル質問 {n_sample} 件",
    has_syn and n_sample >= 1,
    "UC 列コメント・同義語・サンプル質問が知識ストアに入りました。",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## まとめ
# MAGIC - 列とテーブルに **UC コメント**を付け、意味・結合キー・欠損の注意を Genie に伝えました。
# MAGIC - 業務の言葉をつなぐ**同義語**と**サンプル質問**を登録しました。
# MAGIC
# MAGIC ただし、これだけでは **地域区分（APJ / AMER / EMEA）や LEFT JOIN のような「複数テーブルを結合して
# MAGIC 計算するルール」**はまだ十分に教えられていません。**次のモジュール 07「SQL ロジックと指示」** で
# MAGIC そのルールを SQL 例・結合・指示として教え込み、04 の BEFORE スコアと比べて効果を確かめます。
