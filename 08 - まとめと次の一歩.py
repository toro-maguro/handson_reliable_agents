# Databricks notebook source
# MAGIC %md
# MAGIC # 08 — まとめと次の一歩
# MAGIC
# MAGIC このモジュールはコースの最終章です。
# MAGIC モジュール 03 から 07 まで積み上げてきた内容を振り返り、学んだことを実務でどう活かすかを整理します。
# MAGIC 最後に、後片付け（クリーンアップ）も行えます。
# MAGIC
# MAGIC ### このモジュールの到達目標
# MAGIC - コース全体の学びを自分の言葉で3点にまとめられる
# MAGIC - BEFORE/AFTER スコアの差が何を意味するかを説明できる
# MAGIC - 本番環境への展開に向けた次のアクションを挙げられる
# MAGIC
# MAGIC ### 所要時間
# MAGIC 約 10 分（クリーンアップは任意）

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 1 — コース全体の弧を振り返る
# MAGIC
# MAGIC このコースは「**素の状態 → 整備した状態**」という一本の弧で構成されていました。
# MAGIC
# MAGIC ```
# MAGIC 01 入門 → 02 データ理解
# MAGIC   → 03 素の Genie を作る（簡単な質問は当たる／地域別は外す を体験）
# MAGIC   → 04 BEFORE スコアを測る（6 問で精度の現状確認）
# MAGIC   → 05 キュレーション設計の考え方
# MAGIC   → 06 メタデータ整備（UC 列コメント・シノニム・サンプル質問）
# MAGIC   → 07 SQL 例・join・指示を追記（地域区分・LEFT JOIN・レビュー感情）→ AFTER スコア
# MAGIC   → 08 まとめ（このモジュール）
# MAGIC ```
# MAGIC
# MAGIC 各モジュールでの主な学び：
# MAGIC
# MAGIC | モジュール | 一言まとめ |
# MAGIC |---|---|
# MAGIC | 01 | Genie エージェントは「業務専用の会話 AI」。Genie One は全員向けの入り口 |
# MAGIC | 02 | Bakehouse の5テーブルとキー（franchiseID・customerID）を把握 |
# MAGIC | 03 | API で素の Genie を作成。単純な質問は当たり、地域別は外すことを体験 |
# MAGIC | 04 | 業務でよく聞かれる 6 問のベンチマークを登録し BEFORE スコアを測定 |
# MAGIC | 05 | 精度を上げる整備の要素・優先順位・Human-in-the-loop の原則 |
# MAGIC | 06 | UC 列コメント・シノニム・サンプル質問を API で書き込む |
# MAGIC | 07 | SQL 例・join 仕様・テキスト指示（地域区分・LEFT JOIN・レビュー感情）を追記 → AFTER スコアで改善を確認 |

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 2 — BEFORE/AFTER の差が意味するもの
# MAGIC
# MAGIC モジュール 04 と 07 でそれぞれ評価スコアを測りました。
# MAGIC
# MAGIC 整備前（BEFORE）のスコアが低かった原因：
# MAGIC - 「APJ」「地域別」という業務区分を Genie が知らず、自己流で推測していた
# MAGIC - 欠損を含む結合（LEFT JOIN）や同名店舗の扱いを教えていなかった
# MAGIC - レビューの感情が `flag` 列にあることを知らなかった
# MAGIC
# MAGIC 整備後（AFTER）でスコアが上がった理由：
# MAGIC - example_question_sql が地域分類・LEFT JOIN・優良顧客の SQL を固定した
# MAGIC - join_specs と text_instruction が結合と業務ルールを宣言した
# MAGIC - UC 列コメント・シノニムが「言葉の橋渡し」をした
# MAGIC
# MAGIC <div style="border-left:4px solid #43a047;background:#e8f5e9;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#2e7d32;">✔ BEFORE/AFTER の読み方</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">
# MAGIC   スコアは「6 問のベンチマークへの正答数」です。数値の絶対値より <strong>差分（改善幅）</strong> に注目します。
# MAGIC   本コースの代表例は <b>2〜3 / 6 → ほぼ全問（6 / 6 目安）</b>（素で当たるのは単純な件数・単純な結合が中心、
# MAGIC   整備後は売上トップ N・LEFT JOIN・地域区分・レビュー感情を含む問いも正答に変わる）。
# MAGIC   どの設問で外れたかを見ると、次に何を整備すべきかが分かります。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 3 — 実務への展開（共有・運用・モニタリング）
# MAGIC
# MAGIC ### 3-1. Genie エージェントをチームに共有する
# MAGIC Genie エージェントは特定のユーザーやグループに公開できます。
# MAGIC Unity Catalog の権限設定を使い、必要な人だけがアクセスできる状態にします。
# MAGIC
# MAGIC ### 3-2. 定期的にベンチマークを走らせる
# MAGIC データやビジネスルールが変わると、整備済みの設定が古くなることがあります。
# MAGIC ベンチマーク（eval-run）を月次・四半期ごとに走らせ、精度の劣化を早期発見します。
# MAGIC
# MAGIC ### 3-3. フィードバックを整備に還元する
# MAGIC Genie の画面には「この回答は正しくない」とフィードバックできる機能があります。
# MAGIC 集まったフィードバックを見て、example_question_sql や instruction を定期的に更新します。
# MAGIC
# MAGIC <div style="border-left:4px solid #1976d2;background:#e3f2fd;padding:14px 18px;border-radius:4px;margin:12px 0;color:#333;">
# MAGIC <strong>Genie One との使い分け</strong><br>
# MAGIC Genie エージェントは特定業務向けに作り込んだ専用版、Genie One は全ユーザーが会社のデータを広く探索する入り口です。
# MAGIC 用途に応じて使い分けます。
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 4 — クリーンアップ（任意）
# MAGIC
# MAGIC このハンズオンで作成した **Genie エージェント**と**学習用スキーマ**を削除できます。
# MAGIC もう一度最初から試したいとき（初回状態での再実行）にも、ここで片付けてから 02 / 03 に戻れます。
# MAGIC
# MAGIC 次のセルはヘルパーを読み込みます。続くセルの **`cleanup` ウィジェットを `yes`** にして実行すると削除します
# MAGIC （既定は `no`＝削除しません）。

# COMMAND ----------

# MAGIC %run ./Includes/Classroom-Setup-Common

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #ff9800;background:#fff3e0;padding:14px 18px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#e65100;font-size:1.1em;">削除前に確認してください</strong>
# MAGIC   <div style="color:#333;margin-top:6px;">
# MAGIC   <code>cleanup</code> を <b>yes</b> にして実行すると、Genie エージェントをゴミ箱に移動し、
# MAGIC   <code>workspace.reliable_agents</code> スキーマとテーブルを削除します。学習内容を今後も参照したい場合は <b>no</b> のままにしてください。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# 既定は no（削除しない）。削除したいときだけ上部の cleanup ウィジェットを yes にして再実行。
dbutils.widgets.dropdown("cleanup", "no", ["no", "yes"], "クリーンアップ実行")

if dbutils.widgets.get("cleanup") == "yes":
    sid = load_space_id()
    if sid:
        genie_trash_space(sid)
        print(f"Genie エージェントをゴミ箱に移動しました: {sid}")
    spark.sql(f"DROP SCHEMA IF EXISTS `{my_catalog}`.`{my_schema}` CASCADE")
    print(f"✅ {my_catalog}.{my_schema} を削除しました。02 / 03 から作り直せます。")
else:
    print("クリーンアップは未実行です。削除する場合は上部の cleanup ウィジェットを yes にして再実行してください。")

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ コース完了 — このコースで学んだこと
# MAGIC
# MAGIC 1. **Genie の役割の違い** — Genie One は全ユーザー向けの入り口、Genie エージェントは業務専用に作り込む専用版
# MAGIC 2. **素の得意・不得意** — 単純な集計は当たるが、業務ルール（地域区分・結合）は教えないと外す
# MAGIC 3. **精度を上げる整備** — 列説明・シノニム・SQL ロジック・指示・サンプル質問
# MAGIC 4. **BEFORE/AFTER の数値検証** — 整備が効いたかを感覚でなくスコアで確認する
# MAGIC 5. **API によるキュレーション自動化** — `get → 編集 → update` の往復パターン（画面のコピペを繰り返さない）
# MAGIC
# MAGIC **次のアクション候補:**
# MAGIC - 自分のデータで同じ流れを試す（別スキーマで実験）
# MAGIC - ベンチマーク質問を増やして精度をさらに測る
# MAGIC - 共有設定を行いチームメンバーに Genie エージェントを提供する
# MAGIC - フィードバック収集の仕組みを作り、継続的改善サイクルを回す
# MAGIC
# MAGIC おつかれさまでした！
