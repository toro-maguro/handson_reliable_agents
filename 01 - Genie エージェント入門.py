# Databricks notebook source
# MAGIC %md
# MAGIC # 01 — Genie エージェント入門
# MAGIC
# MAGIC このモジュールでは、Databricks **Genie エージェント**（Genie Agent）が何者で、
# MAGIC AI/BI ダッシュボードや **Genie One** とどう違うのかを整理します。
# MAGIC そして「素のまま使うと業務ルールを外す」理由を理解し、このコース全体で何を目指すかを共有します。
# MAGIC
# MAGIC ### このモジュールの到達目標
# MAGIC - Genie エージェント・Genie One・AI/BI ダッシュボードの違いを自分の言葉で説明できる
# MAGIC - Genie エージェントは「誰が作り、誰に提供するもの」かを説明できる
# MAGIC - 「素の状態では業務ルールを含む質問の精度が不十分」な理由を説明できる
# MAGIC
# MAGIC ### 所要時間
# MAGIC 約 10 分（コード実行なし・読み進めるだけ）

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 1 — Genie エージェントとは何か
# MAGIC
# MAGIC **Genie エージェント**（Genie Agent）は、
# MAGIC 「特定のデータに絞り込み、業務の知識を教え込んだ**会話型の AI エージェント**」です。
# MAGIC 自然言語の質問を SQL に翻訳して実行し、結果を会話で返します。
# MAGIC
# MAGIC 大事なのは **誰が作り、誰が使うか**です。
# MAGIC
# MAGIC - **作る人** — データ / AI チーム（ドメインエキスパート）。対象データを絞り、業務ルールを教え込み、
# MAGIC   ベンチマークで精度を確かめてから公開します。
# MAGIC - **使う人** — ビジネスユーザー。作り込まれたエージェントに、日本語で安心して質問できます。
# MAGIC
# MAGIC <div style="border-left:4px solid #1976d2;background:#e3f2fd;padding:14px 18px;border-radius:4px;margin:12px 0;color:#333;">
# MAGIC <b>「Genie Space」という名前を聞いたことがあるかもしれません。</b>
# MAGIC Genie Space は、検証済みロジックとベンチマークを備え、特定トピックに絞った厳選されたチャット体験でした。
# MAGIC これが<b>進化して Genie エージェント（Genie Agent）</b>になりました（自律的にアクションを実行する力が加わっています）。
# MAGIC 「旧名の言い換え」ではなく<b>進化</b>である、と理解してください。<br>
# MAGIC （API の世界ではいまも <code>spaces</code> という語が使われます。このコースの Notebook でもその API を使います。）
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 2 — Genie One・AI/BI ダッシュボードとの違い
# MAGIC
# MAGIC 名前の似た機能があるので整理します。
# MAGIC
# MAGIC | 機能 | 何をするか | 誰のためのものか |
# MAGIC |---|---|---|
# MAGIC | **AI/BI ダッシュボード** | あらかじめ作った**固定の可視化**を表示する | 数字を眺める人（経営者・現場マネージャー） |
# MAGIC | **Genie One** | 会社のデータに**すべてのユーザーが自然言語で質問できる**「データに強い AI 同僚」 | **すべてのユーザー**（ビジネスユーザーを含む） |
# MAGIC | **Genie エージェント** | **特定のデータに絞り込み、業務ルールを作り込んだ**専用の会話 AI | 作る=データ/AI チーム、使う=ビジネスユーザー |
# MAGIC
# MAGIC ポイントを3つに絞ると：
# MAGIC
# MAGIC 1. **ダッシュボード vs Genie** — ダッシュボードは静的な可視化。Genie は自然言語で対話し、その場で
# MAGIC    SQL を生成・実行して答えます。
# MAGIC 2. **Genie One vs Genie エージェント** — Genie One は全社のデータに誰でも広く問える入り口。
# MAGIC    Genie エージェントは、特定業務向けに**スコープを絞り・業務知識を作り込んだ**専用版です。
# MAGIC 3. **作り込み（キュレーション）ができる** — Genie エージェントには、列の説明・業務用語・集計ルール・
# MAGIC    SQL の例を登録できます。**この作り込みこそが精度を左右する**——本コースの主題です。

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 3 — なぜ「素のまま」では外れるのか
# MAGIC
# MAGIC 作りたての Genie エージェントは、テーブルの構造しか知りません。
# MAGIC **単純な集計はかなり正確に答えます**（例:「総売上は？」）。問題は、**業務ルールを含む質問**です。
# MAGIC
# MAGIC **（例）「地域別（APJ / AMER / EMEA）の総売上は？」**
# MAGIC - `sales_franchises` に `country`（国）はありますが、「APJ / AMER / EMEA」という地域区分は入っていません。
# MAGIC - どの国がどの地域かを教えていないと、Genie は**自己流の区分を推測**します。
# MAGIC   （たとえば主要市場の国を取り違え、一見それらしいが**業務的に誤った内訳**を返すことがあります。）
# MAGIC
# MAGIC やっかいなのは、**間違っていても「それらしく」答えてしまう**点です。だからこそ、業務ルールを
# MAGIC 教え込み、さらに**ベンチマークで精度を測る**ことが必要になります。
# MAGIC
# MAGIC <div style="border-left:4px solid #f44336;background:#ffebee;padding:16px 20px;border-radius:4px;margin:16px 0;">
# MAGIC   <strong style="color:#c62828;font-size:1.1em;">素のままでは「業務の言葉」を知らない</strong>
# MAGIC   <ul style="margin:8px 0 0 0;color:#333;">
# MAGIC     <li>列名が英語の技術名称のとき、日本語の業務用語との対応を知りません</li>
# MAGIC     <li>「APJ」「地域」などビジネス固有の区分は、教えないと推測で埋めます</li>
# MAGIC     <li>複数テーブルをどう結合すべきかも、教えないと外します</li>
# MAGIC   </ul>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 4 — このコースで「素 → 整備」の弧を体験する
# MAGIC
# MAGIC このコースは次の流れを一本で通します。
# MAGIC
# MAGIC ```
# MAGIC 00 概要 → 01 入門 → 02 データ理解
# MAGIC   → 03 素の Genie を作る（簡単な質問は当たる／地域別は外す を体験）
# MAGIC   → 04 ベンチマークで BEFORE スコアを測る
# MAGIC   → 05 キュレーション設計の考え方
# MAGIC   → 06 メタデータ整備 → 07 SQL ロジックと指示を追記（→ AFTER スコア → BEFORE/AFTER 比較）
# MAGIC   → 08 まとめ
# MAGIC ```
# MAGIC
# MAGIC - **03 / 04** で「整備ゼロだと業務ルールをどれだけ外すか」を、体験と数値（BEFORE スコア）で確認します。
# MAGIC - **06 / 07** で整備を加えたあと**同じ問題を再評価**し、精度の変化を数値で見ます（AFTER スコア）。
# MAGIC
# MAGIC 「作り込みが効いた」を体で分かるのが、このコースの山場です。
# MAGIC
# MAGIC <div style="border-left:4px solid #43a047;background:#e8f5e9;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#2e7d32;">✔ このステップの確認</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">
# MAGIC   次の3つが言えれば、このモジュールは完了です。<br>
# MAGIC   ① Genie One は全ユーザー向けの入り口、Genie エージェントは特定業務向けに作り込む専用版<br>
# MAGIC   ② Genie エージェントはデータ/AI チームが作り込み、ビジネスユーザーに提供する<br>
# MAGIC   ③ 素の状態では業務ルールを含む質問を外す → 作り込みとベンチマークで直す
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## まとめ
# MAGIC
# MAGIC - **Genie エージェント** = 特定データに絞り業務知識を作り込んだ会話型 AI（Genie Space が進化したもの）。
# MAGIC   データ/AI チームが作り、ビジネスユーザーに提供する。
# MAGIC - **Genie One** = すべてのユーザー向けの、会社のデータに自然言語で問える AI 同僚。
# MAGIC - **AI/BI ダッシュボード** = 固定の可視化。Genie は自然言語で対話し、その場で SQL を生成・実行する。
# MAGIC - 素の状態では業務ルールを外す → このコースで段階的に作り込み、効果を数値で確かめる。
# MAGIC
# MAGIC **次のモジュール 02「データ理解 (Bakehouse)」** では、
# MAGIC このコースで使うデータ（`samples.bakehouse` の5テーブル）を SQL で眺め、
# MAGIC どの列が何を意味するかを把握します。テーブルを知ることが、良い作り込みの第一歩です。
