# Databricks notebook source
# MAGIC %md
# MAGIC ## モジュール 01 用セットアップ
# MAGIC 共通セットアップを呼び、このモジュールで使うテーブルだけを冪等に用意します。
# MAGIC モジュールごとにこのファイルを1枚コピーし、`setup_tables([...])` の中身を差し替えるだけ。

# COMMAND ----------

# MAGIC %run ./Classroom-Setup-Common

# COMMAND ----------

# このモジュールが必要とするテーブルだけを列挙（samples.bakehouse から冪等複製）
setup_tables([
    "sales_customers",
    "sales_franchises",
    "sales_suppliers",
    "sales_transactions",
])

# 受講者に「データが入ったか」を見せる
check_row_count("sales_transactions", expected_min=1)
