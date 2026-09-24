# Databricks notebook source
# MAGIC %md
# MAGIC # 04 — ベンチマークで精度を測る
# MAGIC
# MAGIC ### このモジュールの到達目標
# MAGIC - **ベンチマーク**（質問 ＋ 正解の SQL）を Genie エージェントに登録する
# MAGIC - 素のエージェントの精度を **数値（正答数）で測る**（＝改善の出発点 = BEFORE スコア）
# MAGIC
# MAGIC ### 所要時間
# MAGIC 約 15 分
# MAGIC
# MAGIC 「なんとなく良くなった気がする」では改善は語れません。**正解のものさし（ベンチマーク）**を用意して、
# MAGIC 整備の前後を同じ基準で比べられるようにします。ここでは**業務でよく聞かれる 6 問**を登録します。

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #ff9800;background:#fff3e0;padding:14px 18px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#e65100;font-size:1.1em;">結果は異なる場合があります</strong>
# MAGIC   <div style="color:#333;margin-top:6px;">
# MAGIC   ベンチマークの採点はライブの Genie を使います。正答数は環境やタイミングで前後することがあります。
# MAGIC   下記の「期待される結果」は代表例です。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## 環境セットアップ

# COMMAND ----------

# MAGIC %run ./Includes/Classroom-Setup-04

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 1 — ベンチマークとは
# MAGIC ベンチマークは「**この質問には、この結果が正解**」という組を登録したものです。Genie は登録された
# MAGIC 質問に自分で答え、その結果を**正解の SQL の実行結果と突き合わせて採点**します。
# MAGIC
# MAGIC ここでは、業務でよく聞かれる 6 問を正解つきで登録します。素のエージェントは、**単純な集計は当たる**一方で、
# MAGIC **結合・区分・欠損の扱いといった業務ルールを含む問いは外し**がちです。その差を数値で捉えます。
# MAGIC
# MAGIC | # | 質問 | ねらい（何が難しいか） |
# MAGIC |---|------|------------------------|
# MAGIC | Q1 | 顧客数は何人？ | 単純な件数（当たりやすい） |
# MAGIC | Q2 | 売上トップ 5 の店舗は？ | 取引×店舗の結合・同名店舗の区別 |
# MAGIC | Q3 | 優良顧客（上位）は誰？ | 取引×顧客の結合・売上合計での並べ替え |
# MAGIC | Q4 | 仕入先ごとに何店舗を担当？ | **欠損を含む結合（LEFT JOIN）**・孤立行の扱い |
# MAGIC | Q5 | 地域別（APJ/AMER/EMEA）の売上は？ | **国→地域の業務区分**を知っているか |
# MAGIC | Q6 | 悪いレビューが多い店舗は？ | レビュー×店舗の結合・`flag` 列の意味 |

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 2 — 6 問のベンチマークを API で登録する
# MAGIC 03 で作ったエージェントに、6 問のベンチマーク（質問＋正解 SQL）を追加します。Genie の知識ストアは
# MAGIC 「現在の内容を取得 → 編集 → 書き戻し」の手順で更新します（`genie_get` → 編集 → `genie_update`）。
# MAGIC 正解 SQL のテーブルは作業スキーマを完全修飾（`fq(...)`）します。

# COMMAND ----------

space_id = load_space_id()
assert space_id, "先に 03 を実行して Genie エージェントを作成してください。"

# --- 6 問の正解 SQL（作業スキーマを完全修飾） -----------------------------------
Q1_SQL = f"SELECT COUNT(DISTINCT customerID) AS total_customers FROM {fq('sales_customers_gold')}"

Q2_SQL = (
    "WITH franchise_revenue AS ("
    "SELECT f.franchiseID, f.city, f.name, SUM(t.totalPrice) AS total_revenue "
    f"FROM {fq('sales_transactions_gold')} t "
    f"JOIN {fq('sales_franchises_gold')} f ON t.franchiseID = f.franchiseID "
    "WHERE t.franchiseID IS NOT NULL AND t.totalPrice IS NOT NULL AND f.city IS NOT NULL "
    "GROUP BY f.franchiseID, f.city, f.name) "
    "SELECT city, name, total_revenue FROM ("
    "SELECT city, name, total_revenue, RANK() OVER (ORDER BY total_revenue DESC) AS rank "
    "FROM franchise_revenue) WHERE rank <= 5"
)

Q3_SQL = (
    "SELECT c.customerID, c.first_name, c.last_name, SUM(t.totalPrice) AS total_spend "
    f"FROM {fq('sales_transactions_gold')} AS t "
    f"JOIN {fq('sales_customers_gold')} AS c ON t.customerID = c.customerID "
    "GROUP BY c.customerID, c.first_name, c.last_name ORDER BY total_spend DESC LIMIT 10"
)

Q4_SQL = (
    "SELECT COALESCE(s.name, 'No Matching Supplier') AS supplier_name, "
    "COUNT(f.franchiseID) AS franchise_count "
    f"FROM {fq('sales_franchises_gold')} AS f "
    f"LEFT JOIN {fq('sales_suppliers_gold')} AS s ON f.supplierID = s.supplierID "
    "GROUP BY s.name ORDER BY franchise_count DESC"
)

Q5_SQL = (
    "SELECT CASE "
    "WHEN f.country IN ('Japan','Australia') THEN 'APJ' "
    "WHEN f.country IN ('US','Canada') THEN 'AMER' "
    "WHEN f.country IN ('Netherlands','France','Germany','Italy','Sweden') THEN 'EMEA' "
    "ELSE 'Other' END AS region, SUM(t.totalPrice) AS total_sales "
    f"FROM {fq('sales_franchises_gold')} AS f "
    f"JOIN {fq('sales_transactions_gold')} AS t ON f.franchiseID = t.franchiseID "
    "GROUP BY region ORDER BY total_sales DESC"
)

Q6_SQL = (
    "SELECT r.ref, f.name AS franchise_name, f.city, COUNT(*) AS negative_review_count "
    f"FROM {fq('media_customer_reviews_gold')} r "
    f"JOIN {fq('sales_franchises_gold')} f ON r.ref = f.franchiseID "
    "WHERE r.flag = 'negative' GROUP BY r.ref, f.name, f.city ORDER BY negative_review_count DESC"
)

# ベンチマーク ID は 32 桁小文字 hex・昇順（固定なので再実行しても増えない）。
BENCH = [
    ("cc000000000000000000000000000001", "顧客数は何人ですか？", Q1_SQL),
    ("cc000000000000000000000000000002", "売上トップ 5 の店舗（ロケーション）はどこですか？", Q2_SQL),
    ("cc000000000000000000000000000003", "優良顧客（購入金額の上位）は誰ですか？", Q3_SQL),
    ("cc000000000000000000000000000004", "仕入先ごとに何店舗を担当していますか？", Q4_SQL),
    ("cc000000000000000000000000000005", "地域別（APJ / AMER / EMEA）の総売上を教えて", Q5_SQL),
    ("cc000000000000000000000000000006", "悪いレビューが多い店舗はどこですか？", Q6_SQL),
]
BENCH_IDS = [b[0] for b in BENCH]

ss, etag = genie_get(space_id)
ss["benchmarks"] = {"questions": [
    {"id": bid, "question": [q], "answer": [{"format": "SQL", "content": [sql]}]}
    for bid, q, sql in BENCH
]}
genie_update(space_id, ss, etag)
print(f"ベンチマークを登録しました（質問 {len(BENCH)} 件）")

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #43a047;background:#e8f5e9;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#2e7d32;">✔ 期待される結果</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">「ベンチマークを登録しました（質問 6 件）」と表示される。</div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 3 — 素のエージェントを採点する（BEFORE スコア）
# MAGIC 登録した 6 問で、**まだ何も作り込んでいない**エージェントを採点します。採点には少し時間が
# MAGIC かかります（1 問あたり 15〜30 秒目安・6 問で数分）。完了まで待ちます。

# COMMAND ----------

before_correct, before_total, status = genie_run_and_wait(space_id, BENCH_IDS)
save_score("before", before_correct, before_total)

displayHTML(f"""
<div style="border-left:4px solid #607d8b;background:#eceff1;padding:14px 18px;border-radius:4px;
     margin:12px 0;font-family:sans-serif;color:#333;">
  <strong style="font-size:1.1em;">BEFORE スコア（素のエージェント）</strong>
  <div style="font-size:1.6em;margin-top:6px;"><b>{before_correct} / {before_total}</b> 問 正解</div>
  <div style="color:#666;margin-top:4px;">採点ステータス: {status}</div>
</div>
""")

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #43a047;background:#e8f5e9;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#2e7d32;">✔ 期待される結果</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">
# MAGIC   代表例では BEFORE は <b>2〜3 / 6</b> 問正解（単純な件数や単純な結合は当たり、
# MAGIC   売上トップ N・LEFT JOIN・地域区分・レビュー感情など業務ルールを含む問いは外しがち。
# MAGIC   ライブ採点なので正答数は前後します）。これが改善の出発点です。06 / 07 で作り込んだあと、同じ 6 問で再採点して比べます。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ チェックポイント

# COMMAND ----------

checkpoint(
    f"BEFORE スコアを記録: {before_correct} / {before_total} 問正解",
    status == "DONE",
    "このスコアを 07 の AFTER と比較します。",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## まとめ
# MAGIC - 「質問 ＋ 正解 SQL」のベンチマークを **6 問**登録し、素のエージェントの精度を**数値で**測りました。
# MAGIC - BEFORE スコアを保存しました（07 の AFTER と比較します）。
# MAGIC
# MAGIC **次のモジュール 05「効果的なキュレーション設計」** で、何を整備すると精度が上がるのかを整理してから、
# MAGIC 06 / 07 で実際に作り込みます。
