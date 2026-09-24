# Databricks notebook source
# MAGIC %md
# MAGIC # 信頼できる Genie エージェントの構築 — コース概要
# MAGIC
# MAGIC ## このコースで学ぶこと
# MAGIC Genie は、自然言語の質問を SQL に翻訳して答える Databricks の機能です。ただし **「素のまま」では
# MAGIC 業務のルールを知らないため、地域区分や独自の定義がからむ質問を外します。** このコースでは、
# MAGIC 架空の飲食チェーン（Bakehouse）のデータを題材に、**Genie エージェントを「作り込み（キュレーション）」して
# MAGIC 正確に答えられるようにする**一連の流れを、手を動かしながら体験します。
# MAGIC
# MAGIC ## いちばん大事な体験 — 「素 → 整備」で精度が上がる
# MAGIC このコースの背骨は次の弧です。同じ質問に対して、整備の前後で答えがどう変わるかを**数値で**確かめます。
# MAGIC
# MAGIC <div style="border-left:4px solid #1976d2;background:#e3f2fd;padding:14px 18px;border-radius:4px;margin:12px 0;color:#333;">
# MAGIC <b>素の Genie</b>（テーブルを登録しただけ） → 地域別売上のような業務ルールを含む質問を<b>外す</b><br>
# MAGIC &nbsp;&nbsp;&nbsp;&nbsp;↓ メタデータ・SQL ロジック・指示・ベンチマークで<b>作り込む</b><br>
# MAGIC <b>整備後の Genie</b> → 同じ質問に<b>正しく</b>答える（ベンチマークの正答数が増える）
# MAGIC </div>
# MAGIC
# MAGIC ## 到達目標
# MAGIC - Genie エージェントを作成し、なぜ「素のまま」では外すのかを体験できる
# MAGIC - ベンチマーク（正解のものさし）で精度を**数値化**できる
# MAGIC - メタデータ・SQL ロジック・指示を追加して、精度を上げられる
# MAGIC - 整備の前後（BEFORE / AFTER）を比べて、作り込みの効果を説明できる

# COMMAND ----------

# MAGIC %md
# MAGIC ## モジュール構成
# MAGIC | # | タイプ | 内容 | 目安 |
# MAGIC |---|--------|------|------|
# MAGIC | 00 | 概要 | このノートブック | 5分 |
# MAGIC | 01 | 講義 | Genie エージェント入門（Genie One・ダッシュボードとの違い、なぜ作り込みが要るか） | 10分 |
# MAGIC | 02 | ハンズオン | データ理解（Bakehouse の5テーブルと関係を SQL で概観） | 15分 |
# MAGIC | 03 | ハンズオン | 素の Genie エージェントを作る（単純な質問は当たる／地域別は外すを体験） | 15分 |
# MAGIC | 04 | ハンズオン | ベンチマークで精度を測る（**BEFORE スコア**） | 15分 |
# MAGIC | 05 | 講義 | 効果的なキュレーション設計（何を整備すると精度が上がるか） | 10分 |
# MAGIC | 06 | ハンズオン | メタデータ整備（列の説明・同義語・サンプル質問） | 15分 |
# MAGIC | 07 | ハンズオン | SQL ロジックと指示（地域区分を教える → **AFTER スコア** → BEFORE/AFTER 比較） | 20分 |
# MAGIC | 08 | まとめ | 学びの振り返りと次の一歩（＋クリーンアップ） | 10分 |
# MAGIC
# MAGIC > 各モジュールは独立したノートブックです。**この番号順に、上から下へ**実行してください。
# MAGIC > 03〜07 は同じ 1 つの Genie エージェントを少しずつ育てていきます。

# COMMAND ----------

# MAGIC %md
# MAGIC ## 前提条件
# MAGIC <div style="border-left:4px solid #f44336;background:#ffebee;padding:16px 20px;border-radius:4px;margin:16px 0;">
# MAGIC   <strong style="color:#c62828;font-size:1.1em;">実行前に必要なもの</strong>
# MAGIC   <ul style="margin:8px 0 0 0;color:#333;">
# MAGIC     <li>Databricks <b>Free Edition</b> アカウント（各自でサインアップ。1 アカウント = 1 ワークスペース）</li>
# MAGIC     <li>Serverless SQL Warehouse が使えること（Free Edition の「Serverless Starter Warehouse」でOK）</li>
# MAGIC     <li><b>Genie / Databricks Assistant が有効</b>であること（Free Edition は既定で有効。設定 → 管理者 で確認可）</li>
# MAGIC     <li>Unity Catalog の <b>samples.bakehouse</b> にアクセスできること（全ワークスペース共通の公式サンプル）</li>
# MAGIC   </ul>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## 作業場所（全員共通）
# MAGIC このコースは、あなたのワークスペースの **`workspace` カタログの中に `reliable_agents` スキーマ**を作り、
# MAGIC そこで作業します。受講者はそれぞれ自分のワークスペースを使うため、**全員が同じ名前でも衝突しません**。
# MAGIC 案内が一本化できるよう、名前は固定しています。
# MAGIC
# MAGIC <div style="border-left:4px solid #1976d2;background:#e3f2fd;padding:14px 18px;border-radius:4px;margin:12px 0;color:#333;">
# MAGIC <b>書き込み先</b>: <code>workspace.reliable_agents</code>（各モジュール冒頭のセットアップが自動で用意します）<br>
# MAGIC <b>データ</b>: <code>samples.bakehouse</code> の販売系テーブルを、上記スキーマに冪等コピーして使います。<br>
# MAGIC ※ 別の場所を使いたい場合だけ、各モジュール上部の <b>catalog / schema ウィジェット</b>で上書きできます。
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #ff9800;background:#fff3e0;padding:14px 18px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#e65100;font-size:1.1em;">結果は異なる場合があります</strong>
# MAGIC   <div style="color:#333;margin-top:6px;">
# MAGIC   本コースの 03〜08 はライブの Genie / LLM を使います。応答は実行ごとに変わりうるため、
# MAGIC   示される期待結果は代表例です。ベンチマークの正答数も、環境やタイミングで前後することがあります。
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC 準備ができたら、モジュール **01 — Genie エージェント入門** に進んでください。
