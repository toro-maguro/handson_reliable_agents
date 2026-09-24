# Databricks notebook source
# MAGIC %md
# MAGIC # 05 — 効果的なキュレーション設計
# MAGIC
# MAGIC モジュール 04 で BEFORE スコアを測りました。
# MAGIC 「整備ゼロだと業務ルールをこれだけ外す」という数字を持った状態で、
# MAGIC このモジュールでは「**何を整備すると精度がどれだけ上がるか**」の考え方を学びます。
# MAGIC コードは実行しません。次のモジュール（06・07）で実際に手を動かすための地図を描きます。
# MAGIC
# MAGIC ### このモジュールの到達目標
# MAGIC - 精度を上げるキュレーション（curation）の要素を説明できる
# MAGIC - 何から手をつけると費用対効果が高いかを判断できる
# MAGIC - Human-in-the-loop（人間による確認ステップ）が必要な理由を説明できる
# MAGIC
# MAGIC ### 所要時間
# MAGIC 約 10 分（コード実行なし）

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 1 — キュレーションとは何か
# MAGIC
# MAGIC **キュレーション（curation）** とは、Genie エージェントに「業務知識を教え込む」作業です。
# MAGIC テーブルを登録しただけの状態では、Genie はデータの構造は分かっても、
# MAGIC 業務の文脈や集計ルールは分かりません（04 で見たとおり、地域区分を自己流で推測して外しました）。
# MAGIC
# MAGIC 精度を上げるキュレーションは、大きく次に分かれます。
# MAGIC
# MAGIC | 種類 | 内容 | 効く場面 |
# MAGIC |---|---|---|
# MAGIC | **列の説明（description）** | 列名に日本語説明を付ける | 英語の技術名称を日本語の質問に対応させる |
# MAGIC | **シノニム（synonym）** | 業務用語の別名・揺らぎを登録する | 「売上」「収益」「レベニュー」を同じ列に向ける |
# MAGIC | **SQL ロジック（example_question_sql）** | 頻出の集計・分類式を「質問→正解 SQL」で登録する | 地域 CASE、割引率計算など毎回外れる式 |
# MAGIC | **テキスト指示（instruction）** | 業務ルールを文章で宣言する | 「地域は country から APJ/AMER/EMEA に分類する」等 |
# MAGIC | **サンプル質問** | 想定質問を提示し、利用者が使い始めやすくする | 「こう聞けばよい」を利用者に示す |
# MAGIC
# MAGIC <div style="border-left:4px solid #1976d2;background:#e3f2fd;padding:14px 18px;border-radius:4px;margin:12px 0;color:#333;">
# MAGIC Databricks では、これらをまとめて <strong>「知識ストア（Knowledge Store）」</strong> と呼びます。
# MAGIC Genie エージェントの画面の設定から編集できますが、
# MAGIC このコースでは Notebook から <strong>API を通じて同じ内容を書き込む</strong>方法を学びます（画面のコピペを繰り返さずに済みます）。
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 2 — 何から手をつけるか（優先度）
# MAGIC
# MAGIC 全部を一度に整備しようとすると時間がかかります。
# MAGIC BEFORE スコアの間違いのパターンを見て、効果が大きい順に手をつけます。
# MAGIC
# MAGIC **優先順位の目安：**
# MAGIC
# MAGIC 1. **列の説明とシノニム**（モジュール 06）
# MAGIC    - 費用対効果が最も高い。質問の言葉とデータの列名を橋渡しするだけで正答率が上がります。
# MAGIC    - 例: `totalPrice` → 「売上金額」（シノニム: 売上・収益）、`country` → 「店舗の国」
# MAGIC 2. **SQL ロジック（example_question_sql）とテーブル結合**（モジュール 07）
# MAGIC    - 毎回間違える集計式を「質問→正解 SQL」で固定します。「地域で集計して」に対する
# MAGIC      APJ/AMER/EMEA への CASE 式変換は、教えないと出てきません。
# MAGIC 3. **テキスト指示**（モジュール 07）
# MAGIC    - 業務ルールを文章で宣言します。例:「地域は country から APJ/AMER/EMEA に分類する。
# MAGIC      売上は totalPrice の合計で、地域別は取引と店舗を franchiseID で結合して集計する」。
# MAGIC 4. **サンプル質問**（モジュール 06）
# MAGIC    - 利用者が使い始めやすいよう、想定質問を提示します。
# MAGIC
# MAGIC <div style="border-left:4px solid #1976d2;background:#e3f2fd;padding:14px 18px;border-radius:4px;margin:12px 0;color:#333;">
# MAGIC <strong>整備の上限</strong>: テキスト指示（text_instruction）は最大1件、
# MAGIC 知識ストア全体は合計 3.5MB 以内です。量より質を意識して書きます。
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 3 — Human-in-the-loop を正直に理解する
# MAGIC
# MAGIC Genie は AI ですが、**100% 正確なわけではありません**。
# MAGIC 整備後であっても、予期しない質問や複雑な集計では外れることがあります。
# MAGIC これは Genie の欠陥ではなく、LLM（大規模言語モデル）の性質です。
# MAGIC だからこそ、「確認フロー」を設計に組み込むことが重要です。
# MAGIC
# MAGIC **Human-in-the-loop の考え方：**
# MAGIC
# MAGIC - Genie が生成した SQL を **人間が確認**してから重要な意思決定に使う
# MAGIC - 「この回答は SQL から生成されています」という**透明性の表示**を残す（Genie は生成 SQL を提示します）
# MAGIC - 定期的に **ベンチマーク（eval-run）** を走らせ、精度の劣化を早期発見する（モジュール 04 / 07）
# MAGIC
# MAGIC <div style="border-left:4px solid #ff9800;background:#fff3e0;padding:14px 18px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#e65100;font-size:1.1em;">整備 = 完成ではありません</strong>
# MAGIC   <div style="color:#333;margin-top:6px;">
# MAGIC   キュレーションで精度は大きく上がりますが、ゼロにはなりません。
# MAGIC   重要な意思決定では、Genie の回答を<strong>出発点</strong>として扱い、人間が確認する運用を設計してください。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 4 — 整備の効果を測る仕組み（ベンチマーク）
# MAGIC
# MAGIC 整備の効果を「感覚」でなく「数値」で確認するのがベンチマーク評価です。
# MAGIC
# MAGIC 流れは以下のとおりです：
# MAGIC 1. 想定される質問と正解 SQL を事前に登録する（モジュール 04）
# MAGIC 2. `eval-run`（評価実行）を走らせる → Genie が各質問に答える
# MAGIC 3. 生成した結果を正解と比較 → 正答数（スコア）を算出
# MAGIC 4. 整備の前後でスコアを比べる（BEFORE → AFTER）
# MAGIC
# MAGIC このコースではモジュール 04 で BEFORE スコアを、モジュール 07 で AFTER スコアを測ります。
# MAGIC 数値の改善が「キュレーションが効いた証拠」になります。
# MAGIC
# MAGIC <div style="border-left:4px solid #43a047;background:#e8f5e9;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#2e7d32;">✔ このステップの確認</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">
# MAGIC   次の3点が言えれば、このモジュールは完了です。<br>
# MAGIC   ① 精度を上げる整備は「列説明・シノニム・SQL ロジック・テキスト指示・サンプル質問」<br>
# MAGIC   ② 列の説明とシノニムから始めると費用対効果が高い<br>
# MAGIC   ③ 整備後も Human-in-the-loop と定期評価が必要
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## まとめ
# MAGIC
# MAGIC このモジュールでは、精度を上げるキュレーションの要素・優先順位・Human-in-the-loop の考え方を整理しました。
# MAGIC
# MAGIC - 整備の要素: 列説明・シノニム・SQL ロジック・テキスト指示・サンプル質問
# MAGIC - 費用対効果の高い順: 列説明/シノニム → SQL ロジック/結合 → テキスト指示 → サンプル質問
# MAGIC - Genie は補助ツール。重要な意思決定には人間確認のフローを設ける
# MAGIC
# MAGIC **次のモジュール 06「メタデータ整備」** では、
# MAGIC 列の説明・シノニム・サンプル質問を実際に Genie の知識ストアに API で書き込みます。
# MAGIC 画面でコピペしていた作業を Notebook から自動化します。
