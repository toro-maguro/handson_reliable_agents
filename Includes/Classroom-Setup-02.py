# Databricks notebook source
# MAGIC %md
# MAGIC ## モジュール 02 用セットアップ
# MAGIC 共通セットアップ（catalog/schema 解決・Genie ヘルパー）と、コース用の gold テーブル群を
# MAGIC 冪等に用意します。何度・誰が実行しても壊れません。

# COMMAND ----------

# MAGIC %run ./Classroom-Setup-Common

# COMMAND ----------

# MAGIC %run ./Classroom-Setup-gold-tables

# COMMAND ----------

# データが入ったことを受講者に見せる（このコースは *_gold テーブルを使う）
check_row_count("sales_transactions_gold", expected_min=1)
check_row_count("media_customer_reviews_gold", expected_min=1)
