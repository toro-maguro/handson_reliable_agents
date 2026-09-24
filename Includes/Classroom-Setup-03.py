# Databricks notebook source
# MAGIC %md
# MAGIC ## モジュール 03 用セットアップ
# MAGIC 共通セットアップ（catalog/schema 解決・Genie ヘルパー）と、コース用の gold テーブル群を
# MAGIC 冪等に用意します。整備前のモジュールなので、gold のコメントを『素』に戻します
# MAGIC （前回パスの 06 で付いたコメントが残っていても、素の失敗ケースが再現するように）。

# COMMAND ----------

# MAGIC %run ./Classroom-Setup-Common

# COMMAND ----------

# MAGIC %run ./Classroom-Setup-gold-tables

# COMMAND ----------

# 整備前（素）の状態に戻す: gold の列・テーブルコメントを消す（06 で付与→ここで消す＝再実行でも素を再現）
reset_gold_curation([
    "sales_transactions_gold", "sales_franchises_gold", "sales_customers_gold",
    "sales_suppliers_gold", "media_customer_reviews_gold",
])

# データが入ったことを受講者に見せる（このコースは *_gold テーブルを使う）
check_row_count("sales_transactions_gold", expected_min=1)
check_row_count("media_customer_reviews_gold", expected_min=1)
