# Databricks notebook source
# MAGIC %md
# MAGIC # 02 — データ理解 (Bakehouse)
# MAGIC
# MAGIC このモジュールでは、コース全体で使うデータセット `samples.bakehouse` の5テーブルを
# MAGIC SQL で実際に眺め、各列が何を意味するか・テーブル同士がどう繋がるかを把握します。
# MAGIC 「データを知らずに Genie を整備できない」—— この理解が次のモジュール以降の土台になります。
# MAGIC
# MAGIC ### このモジュールの到達目標
# MAGIC - 5テーブルの主要列と役割を説明できる
# MAGIC - テーブル間の結合キーを特定できる
# MAGIC - 売上・地域分類のもとになる列（`totalPrice`・`country`）を見つけられる
# MAGIC
# MAGIC ### 所要時間
# MAGIC 約 15 分

# COMMAND ----------

# MAGIC %md
# MAGIC ## 環境セットアップ
# MAGIC 下のセルを実行すると、あなた専用の catalog / schema が用意され、
# MAGIC Bakehouse の5テーブルが複製されます。**何度実行しても安全**です（冪等）。
# MAGIC 完了すると使用する catalog / schema が青枠で表示されます。

# COMMAND ----------

# MAGIC %run ./Includes/Classroom-Setup-02

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 1 — Bakehouse データセットの概要
# MAGIC
# MAGIC `samples.bakehouse` は Databricks の全ワークスペースで共通して使えるサンプルデータです。
# MAGIC ある架空のベーカリーチェーンの販売・店舗・顧客・仕入先・レビューを模したデータで、
# MAGIC 以下の5テーブルで構成されています。
# MAGIC
# MAGIC | テーブル | 内容 |
# MAGIC |---|---|
# MAGIC | `sales_transactions_gold` | 取引明細（売上の中心） |
# MAGIC | `sales_franchises_gold` | 店舗マスタ（場所・地域） |
# MAGIC | `sales_customers_gold` | 顧客マスタ |
# MAGIC | `sales_suppliers_gold` | 仕入先マスタ |
# MAGIC | `media_customer_reviews_gold` | 顧客レビュー（テキスト） |
# MAGIC
# MAGIC まずは行数を確認してみましょう。

# COMMAND ----------

# MAGIC %sql
# MAGIC -- 5テーブルの行数を一覧で確認する
# MAGIC SELECT 'sales_transactions_gold'    AS table_name, COUNT(*) AS row_count FROM sales_transactions_gold
# MAGIC UNION ALL
# MAGIC SELECT 'sales_franchises_gold',     COUNT(*) FROM sales_franchises_gold
# MAGIC UNION ALL
# MAGIC SELECT 'sales_customers_gold',      COUNT(*) FROM sales_customers_gold
# MAGIC UNION ALL
# MAGIC SELECT 'sales_suppliers_gold',      COUNT(*) FROM sales_suppliers_gold
# MAGIC UNION ALL
# MAGIC SELECT 'media_customer_reviews_gold', COUNT(*) FROM media_customer_reviews_gold
# MAGIC ORDER BY table_name;

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #43a047;background:#e8f5e9;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#2e7d32;">✔ 期待される結果</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">
# MAGIC   5行の結果が表示されます。各テーブルに1行以上のデータがあれば準備完了です。
# MAGIC   `sales_transactions_gold` が最も行数が多く、他のテーブルはマスタなので行数が少なめです。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 2 — 取引明細テーブル（sales_transactions_gold）
# MAGIC
# MAGIC `sales_transactions_gold` はデータの中心です。1行 = 1件の購入取引を表します。
# MAGIC Genie への質問の多くは「売上はいくらか」「何が売れているか」なので、
# MAGIC このテーブルの列構造を最もよく理解しておく必要があります。
# MAGIC
# MAGIC まず先頭5行を見てみましょう。

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   transactionID,
# MAGIC   customerID,
# MAGIC   franchiseID,
# MAGIC   dateTime,
# MAGIC   product,
# MAGIC   quantity,
# MAGIC   unitPrice,
# MAGIC   totalPrice,
# MAGIC   paymentMethod,
# MAGIC   cardNumber
# MAGIC FROM sales_transactions_gold
# MAGIC LIMIT 5;

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #ff9800;background:#fff3e0;padding:14px 18px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#e65100;font-size:1.1em;">補足：これは合成サンプルデータです</strong>
# MAGIC   <div style="color:#333;margin-top:6px;">
# MAGIC   <code>samples.bakehouse</code> は Databricks の公式サンプル（合成データ）です。実在の個人情報ではありません。
# MAGIC   本コースは<strong>精度向上（キュレーション）</strong>に焦点を当て、売上・地域といった列を扱います。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC 売上分析でよく使う集計例も確認しておきます。
# MAGIC `totalPrice` が売上金額、`quantity` が数量です。

# COMMAND ----------

# MAGIC %sql
# MAGIC -- 商品別の売上合計と販売数量（上位10商品）
# MAGIC SELECT
# MAGIC   product,
# MAGIC   SUM(totalPrice)  AS total_revenue,
# MAGIC   SUM(quantity)    AS total_quantity
# MAGIC FROM sales_transactions_gold
# MAGIC GROUP BY product
# MAGIC ORDER BY total_revenue DESC
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #43a047;background:#e8f5e9;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#2e7d32;">✔ 期待される結果</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">
# MAGIC   商品名とその売上合計・販売数量が降順で表示されます。
# MAGIC   Genie で「どの商品が一番売れているか」と聞いたとき、この集計に近い SQL が生成される想定です。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 3 — 店舗マスタ（sales_franchises_gold）
# MAGIC
# MAGIC `sales_franchises_gold` は店舗の所在地情報を持つマスタテーブルです。
# MAGIC `country` 列が地域分類（APJ/AMER/EMEA）の元データになるため、
# MAGIC このテーブルはモジュール 08 の「地域ロジック登録」で中心的な役割を果たします。

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   franchiseID,
# MAGIC   name,
# MAGIC   city,
# MAGIC   district,
# MAGIC   country,
# MAGIC   size,
# MAGIC   supplierID
# MAGIC FROM sales_franchises_gold
# MAGIC LIMIT 5;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- country の値の種類を確認する（地域分類ロジックを設計するために必要）
# MAGIC SELECT DISTINCT country
# MAGIC FROM sales_franchises_gold
# MAGIC ORDER BY country;

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #43a047;background:#e8f5e9;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#2e7d32;">✔ 期待される結果</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">
# MAGIC   国名の一覧が表示されます。Japan・Australia などが APJ、US・Canada などが AMER、
# MAGIC   Netherlands・France・Germany・Italy・Sweden などが EMEA に分類されます。
# MAGIC   モジュール 08 で CASE 式として Genie に登録します。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 4 — 顧客マスタ（sales_customers_gold）
# MAGIC
# MAGIC `sales_customers_gold` は顧客の属性情報を持ちます。
# MAGIC `customerID` で `sales_transactions_gold` と結合できます。
# MAGIC `email_address` や `phone_number` など個人情報列が含まれる点も把握しておきます。

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   customerID,
# MAGIC   first_name,
# MAGIC   last_name,
# MAGIC   city,
# MAGIC   state,
# MAGIC   country,
# MAGIC   continent,
# MAGIC   gender
# MAGIC FROM sales_customers_gold
# MAGIC LIMIT 5;

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 5 — 仕入先マスタ（sales_suppliers_gold）
# MAGIC
# MAGIC `sales_suppliers_gold` は食材・原材料の仕入先情報です。
# MAGIC `supplierID` で `sales_franchises_gold` と結合でき、
# MAGIC 「どの仕入先の食材を使った店舗で売上が高いか」などの分析が可能です。
# MAGIC `approved` 列は承認済みかどうかのフラグです（True/False）。

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   supplierID,
# MAGIC   name,
# MAGIC   ingredient,
# MAGIC   continent,
# MAGIC   city,
# MAGIC   approved
# MAGIC FROM sales_suppliers_gold
# MAGIC LIMIT 5;

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 6 — 顧客レビュー（media_customer_reviews_gold）
# MAGIC
# MAGIC `media_customer_reviews_gold` は顧客が残したテキストレビューです。
# MAGIC `ref` 列（店舗の `franchiseID`）で `sales_franchises_gold` と結合できます。
# MAGIC 感情は `flag` 列（`positive` / `negative` / `mixed`）で表され、
# MAGIC 「悪いレビューが多い店舗は？」のような問いは、生テキストではなくこの `flag` 列で判定します。

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   ref,
# MAGIC   flag,
# MAGIC   review_date,
# MAGIC   left(review, 80) AS review_head
# MAGIC FROM media_customer_reviews_gold
# MAGIC LIMIT 5;

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 7 — テーブル間の関係
# MAGIC
# MAGIC 5テーブルがどう繋がるかを整理します。Genie に JOIN を覚えさせるために必要な知識です。
# MAGIC
# MAGIC ```
# MAGIC sales_transactions_gold
# MAGIC   ├─ customerID ──→ sales_customers_gold.customerID
# MAGIC   └─ franchiseID ─→ sales_franchises_gold.franchiseID
# MAGIC                          └─ supplierID ─→ sales_suppliers_gold.supplierID （48 中 27 のみ一致・要 LEFT JOIN）
# MAGIC                          └─ franchiseID ←─ media_customer_reviews_gold.ref
# MAGIC ```
# MAGIC
# MAGIC 結合を試してみましょう。「取引ごとに店舗名と顧客名を添付する」クエリです。

# COMMAND ----------

# MAGIC %sql
# MAGIC -- 取引と店舗・顧客を結合して確認する
# MAGIC SELECT
# MAGIC   t.transactionID,
# MAGIC   t.dateTime,
# MAGIC   t.product,
# MAGIC   t.totalPrice,
# MAGIC   f.name        AS franchise_name,
# MAGIC   f.country     AS franchise_country,
# MAGIC   c.first_name  AS customer_first_name,
# MAGIC   c.last_name   AS customer_last_name
# MAGIC FROM sales_transactions_gold t
# MAGIC JOIN sales_franchises_gold   f ON t.franchiseID = f.franchiseID
# MAGIC JOIN sales_customers_gold    c ON t.customerID  = c.customerID
# MAGIC LIMIT 5;

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #43a047;background:#e8f5e9;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#2e7d32;">✔ 期待される結果</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">
# MAGIC   取引ごとに店舗名・所在国・顧客名が付いた5行が表示されます。
# MAGIC   この結合構造を Genie に教えると、「日本の店舗の常連顧客の売上は？」
# MAGIC   といった複数テーブルを跨ぐ質問にも正確に答えられるようになります。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ チェックポイント
# MAGIC ここまでで正しく進んでいるかを自動確認します。❌ が出たら、上のステップを見直してください。

# COMMAND ----------

check_row_count("sales_transactions_gold",      expected_min=1)
check_row_count("sales_franchises_gold",        expected_min=1)
check_row_count("sales_customers_gold",         expected_min=1)
check_row_count("sales_suppliers_gold",         expected_min=1)
check_row_count("media_customer_reviews_gold",  expected_min=1)

checkpoint("5テーブルの確認完了", True, "全テーブルにデータが入っていれば次へ進めます")

# COMMAND ----------

# MAGIC %md
# MAGIC ## まとめ
# MAGIC
# MAGIC このモジュールでは `samples.bakehouse` の5テーブルを SQL で確認しました。
# MAGIC
# MAGIC - `sales_transactions_gold` が売上の中心（`totalPrice`・`quantity`・`product` などが主要列）
# MAGIC - `sales_franchises_gold` の `country` 列が地域分類ロジックの元データ
# MAGIC - 結合キー: transactions → customers（`customerID`）、transactions → franchises（`franchiseID`）、franchises → suppliers（`supplierID`）
# MAGIC
# MAGIC データの構造を把握したので、次はいよいよ Genie エージェント本体を作ります。
# MAGIC
# MAGIC **次のモジュール 03「Genie エージェントを作る」** では、
# MAGIC テーブルだけを登録した「素の状態」の Genie を API で作成し、
# MAGIC 自然言語で質問してみることで整備前の精度を体感します。
