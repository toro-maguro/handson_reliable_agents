# Databricks notebook source
# MAGIC %md
# MAGIC # 03 — Genie エージェントを作る
# MAGIC
# MAGIC ### このモジュールの到達目標
# MAGIC - 販売データを対象にした **Genie エージェントを API で作成**する
# MAGIC - **単純な質問は素のままでも当たる**ことを体験する（成功ケース）
# MAGIC - **業務ルールを含む質問（地域別売上）は素のままだと外す**ことを体験する（失敗ケース）
# MAGIC
# MAGIC ### 所要時間
# MAGIC 約 15 分
# MAGIC
# MAGIC ここで作るのは、**テーブルを登録しただけの「素の」エージェント**です。指示・SQL 例・ベンチマークは
# MAGIC まだ入れません。この素の状態で「当たる質問」と「外す質問」の両方を体験し、次モジュール以降で作り込みます。

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #ff9800;background:#fff3e0;padding:14px 18px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#e65100;font-size:1.1em;">結果は異なる場合があります</strong>
# MAGIC   <div style="color:#333;margin-top:6px;">
# MAGIC   このモジュールはライブの Genie に質問します。回答は実行ごとに変わりうるため、下記の「期待される結果」は代表例です。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## 環境セットアップ
# MAGIC 次のセルは、作業用の `workspace.reliable_agents` スキーマと必要なテーブルを冪等に用意し、
# MAGIC Genie 操作用のヘルパー関数を読み込みます。何度実行しても壊れません。

# COMMAND ----------

# MAGIC %run ./Includes/Classroom-Setup-03

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 1 — まず画面で「作り方」を体験する（🖱️ 任意・学習用）
# MAGIC Genie エージェントは、ふだん画面から作ります。仕組みを理解するために、一度だけ手で作ってみましょう。
# MAGIC
# MAGIC 手順（画面）:
# MAGIC 1. 左メニューの **Genie**（Genie Agents）を開き、**新規作成**を選ぶ
# MAGIC 2. データとして `workspace.reliable_agents` の **販売系 4 テーブル＋レビュー** を選ぶ
# MAGIC 3. SQL warehouse を選び、エージェントを作成する
# MAGIC
# MAGIC 「テーブルを選ぶだけで会話できるエージェントができる」——この手軽さと、この時点では**まだ何も
# MAGIC 教えていない“素”の状態**であることを、画面で体験してください。
# MAGIC
# MAGIC <div style="border-left:4px solid #1976d2;background:#e3f2fd;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#0d47a1;">💻 このあとは同じ処理をコードで実行します</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">
# MAGIC   ハンズオンとして<b>誰が何度実行しても同じ結果</b>になる安定した内容を提供するため、
# MAGIC   以降のモジュールでは<b>コードで作ったエージェント</b>を使います（画面で作ったものは見学用です）。
# MAGIC   時間がなければ上の画面ステップは読み飛ばして、次のコードから始めても構いません。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 2 —（コードで）素の Genie エージェントを作成する
# MAGIC 販売系の 4 テーブル（取引・店舗・顧客・仕入先）に、レビュー（口コミ）テーブルを加えた
# MAGIC 計 5 テーブルを登録したエージェントを、`genie_create_space(...)`（内部は Genie の REST API）で作ります。
# MAGIC 作成した `space_id` は、後続モジュールが引き継げるよう保存します。

# COMMAND ----------

# 既に作成済みなら再利用（受講者が再実行してもエージェントが増殖しない）
space_id = load_space_id()
if space_id:
    print(f"既存の Genie エージェントを再利用します: {space_id}")
else:
    space_id = genie_create_space(
        title="信頼できる販売エージェント (HOL)",
        tables=["sales_customers_gold", "sales_franchises_gold", "sales_suppliers_gold",
                "sales_transactions_gold", "media_customer_reviews_gold"],
    )
    save_space_id(space_id)
    print(f"Genie エージェントを作成しました: {space_id}")

print("画面で開く: " + genie_workspace_link(space_id))

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 3 —（成功ケース）単純な質問は素のままでも当たる
# MAGIC 作りたてのエージェントに、まず**単純な集計**を聞いてみます。回答と、Genie が生成した SQL を
# MAGIC その場で表示します（画面を開かなくても Notebook の中で確認できます）。

# COMMAND ----------

genie_show_answer(space_id, "総売上はいくらですか？")

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #43a047;background:#e8f5e9;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#2e7d32;">✔ 期待される結果</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">
# MAGIC   総売上が正しく返る（代表例: <b>66,471 円</b>）。素のままでも <code>SUM(totalPrice)</code> のような
# MAGIC   単純な集計は正確に答えられます。「AI は簡単なデータなら理解できる」がここで体験できます。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 4 —（失敗ケース）業務ルールを含む質問は素のままだと外す
# MAGIC 次に、**地域区分（APJ / AMER / EMEA）**という業務ルールを含む質問を聞きます。
# MAGIC このルールを教えていないので、Genie は**自己流の区分を推測**して答えます。

# COMMAND ----------

genie_show_answer(space_id, "地域別（APJ / AMER / EMEA）の総売上を教えて")

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #ff9800;background:#fff3e0;padding:14px 18px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#e65100;font-size:1.1em;">一見それらしいが、業務的に誤り</strong>
# MAGIC   <div style="color:#333;margin-top:6px;">
# MAGIC   代表例では、Genie が国→地域の対応を勝手に推測します（例: Japan/China/India を APJ に入れる等）。
# MAGIC   その結果、<b>本来 AMER に入るはずの主要市場（米国）を「その他」に落とす</b>など、
# MAGIC   もっともらしい数字なのに<b>業務定義とズレた内訳</b>になりがちです。
# MAGIC   <br>「AI は簡単なデータなら理解できるが、<b>業務ルール（メタデータ）がないと精度が出ない</b>」——これが体験できます。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ チェックポイント
# MAGIC エージェントが「素の状態（テーブルのみ・指示なし）」で作られていることを確認します。

# COMMAND ----------

ss, _etag = genie_get(space_id)
n_tables = len(ss.get("data_sources", {}).get("tables", []))
has_curation = bool(ss.get("instructions")) or bool(ss.get("benchmarks"))
checkpoint(
    f"エージェント作成: テーブル {n_tables} 件を登録",
    n_tables >= 5 and not has_curation,
    "この時点では指示・SQL 例・ベンチマークは未設定（＝素の状態）です。",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## まとめ
# MAGIC - テーブルだけを登録した「素の」Genie エージェントを作成しました。
# MAGIC - **単純な質問は当たる／業務ルールを含む質問は外す**——素の状態の得意・不得意を体験しました。
# MAGIC
# MAGIC **次のモジュール 04「ベンチマークで精度を測る」** では、この「外し具合」を正解データと突き合わせて
# MAGIC **数値（正答数）で測り**、改善の出発点（BEFORE スコア）にします。
