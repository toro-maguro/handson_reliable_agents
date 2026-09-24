# Databricks notebook source
# MAGIC %md
# MAGIC # 07 — SQL ロジックと指示
# MAGIC
# MAGIC ### このモジュールの到達目標
# MAGIC - **業務ルール**（地域区分・LEFT JOIN・トップ N・レビュー感情）を Genie に教える
# MAGIC - ★**教え方の使い分け（ベスプラ）を体で覚える**:
# MAGIC   **SQL ロジックは「例（`example_question_sqls`）」**、**テーブルの結び付きは「結合（`join_specs`）」**、
# MAGIC   **列の意味・別名は「列コメント／シノニム（06）」**で教える。**指示（`text_instructions`）は書式や回答方針など
# MAGIC   “全体の振る舞い”だけ**にとどめる（SQL ロジックや値の列挙をテキストに詰め込まない＝コンテキストの無駄と矛盾のもと）。
# MAGIC - 教え込む作業を **手動 1 回 → 残りは API で自動反映**（GUI のコピー＆ペーストを繰り返さない）で行う
# MAGIC - **再採点（AFTER スコア）**して、04 の BEFORE と比較し、作り込みの効果を数値で確かめる
# MAGIC
# MAGIC ### 所要時間
# MAGIC 約 20 分

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #ff9800;background:#fff3e0;padding:14px 18px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#e65100;font-size:1.1em;">結果は異なる場合があります</strong>
# MAGIC   <div style="color:#333;margin-top:6px;">
# MAGIC   再採点はライブの Genie を使います。正答数は環境やタイミングで前後することがあります。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## 環境セットアップ

# COMMAND ----------

# MAGIC %run ./Includes/Classroom-Setup-07

# COMMAND ----------

# MAGIC %md
# MAGIC ## この作業の進め方 — 手動 1 回 ＋ API で自動反映
# MAGIC 業務ルールを Genie に教える設定は、ふつう画面で 1 つずつ入力します。数が増えると
# MAGIC **同じ手作業の繰り返し**になりがちです。このモジュールでは効率よく進めます。
# MAGIC
# MAGIC 1. **手を動かして覚える（1 回だけ）**: 設定を「どこに・どう入れるか」を画面で 1 つ体験する。
# MAGIC 2. **残りは API で一括反映**: 同じことをコードで書き込む（画面操作は不要）。
# MAGIC
# MAGIC 貼り付ける内容は、次のセルで **Python が組み立てて表示**します（コピーしやすい形にします）。

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 1 — 教える内容を組み立てる（コピーしやすい形で表示）
# MAGIC 素で外しがちだった問い（地域別売上・仕入先ごとの店舗数・優良顧客・トップ N・レビュー感情）に効く
# MAGIC **SQL 例（6 本）**と、**全体の振る舞いだけの指示（3 件）**を Python で組み立てて表示します。
# MAGIC SQL ロジックは指示に書かず「例」に置くのがベスプラです（テーブルは `fq(...)` で完全修飾）。

# COMMAND ----------

space_id = load_space_id()
assert space_id, "先に 03 / 04 を実行してください。"

# --- 教え込む SQL 例（6 本。ここが SQL ロジックの置き場） ----------------------
# C1: 優良顧客（取引×顧客・売上合計の上位）
BEST_CUSTOMERS_SQL = (
    "SELECT c.customerID, c.first_name, c.last_name, SUM(t.totalPrice) AS total_spend "
    f"FROM {fq('sales_transactions_gold')} AS t "
    f"JOIN {fq('sales_customers_gold')} AS c ON t.customerID = c.customerID "
    "GROUP BY c.customerID, c.first_name, c.last_name ORDER BY total_spend DESC LIMIT 10"
)

# C2: 仕入先ごとの店舗数（LEFT JOIN ＋ 孤立行を 'No Matching Supplier' に）
SUPPLIER_FRANCHISES_SQL = (
    "SELECT COALESCE(s.name, 'No Matching Supplier') AS supplier_name, "
    "COUNT(f.franchiseID) AS franchise_count "
    f"FROM {fq('sales_franchises_gold')} AS f "
    f"LEFT JOIN {fq('sales_suppliers_gold')} AS s ON f.supplierID = s.supplierID "
    "GROUP BY s.name ORDER BY franchise_count DESC"
)

# C3: 地域別売上（国→地域の企業定義）
REGION_SQL = (
    "SELECT CASE "
    "WHEN f.country IN ('Japan','Australia') THEN 'APJ' "
    "WHEN f.country IN ('US','Canada') THEN 'AMER' "
    "WHEN f.country IN ('Netherlands','France','Germany','Italy','Sweden') THEN 'EMEA' "
    "ELSE 'Other' END AS region, SUM(t.totalPrice) AS total_sales "
    f"FROM {fq('sales_franchises_gold')} AS f "
    f"JOIN {fq('sales_transactions_gold')} AS t ON f.franchiseID = t.franchiseID "
    "GROUP BY region ORDER BY total_sales DESC"
)

# C4: 売上トップ N の店舗（RANK による上位抽出・同名店舗は city で区別）
TOP5_SQL = (
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

# C5: ネガティブなレビューが多い店舗（flag='negative' で絞り、ref で店舗に結合）
NEG_REVIEWS_SQL = (
    "SELECT r.ref, f.name AS franchise_name, f.city, COUNT(*) AS negative_review_count "
    f"FROM {fq('media_customer_reviews_gold')} r "
    f"JOIN {fq('sales_franchises_gold')} f ON r.ref = f.franchiseID "
    "WHERE r.flag = 'negative' GROUP BY r.ref, f.name, f.city ORDER BY negative_review_count DESC"
)

# C6: 良いレビューが多い店舗（flag='positive'。良い/悪いの両方を例で教える）
POS_REVIEWS_SQL = (
    "SELECT r.ref, f.name AS franchise_name, f.city, COUNT(*) AS positive_review_count "
    f"FROM {fq('media_customer_reviews_gold')} r "
    f"JOIN {fq('sales_franchises_gold')} f ON r.ref = f.franchiseID "
    "WHERE r.flag = 'positive' GROUP BY r.ref, f.name, f.city ORDER BY positive_review_count DESC"
)

# 質問 → SQL 例（SQL ロジックはここで教える。ベンチと少しずらした自然な言い回しにする＝汎化を促す）
EXAMPLES = [
    ("購入金額が多い顧客のトップ 10 は？", BEST_CUSTOMERS_SQL),
    ("各サプライヤーが担当している店舗数は？", SUPPLIER_FRANCHISES_SQL),
    ("リージョン別（APJ / AMER / EMEA）の売上は？", REGION_SQL),
    ("売上が高い店舗のトップ 5 は？", TOP5_SQL),
    ("ネガティブな評価が多い店舗は？", NEG_REVIEWS_SQL),
    ("良いレビューが多い店舗はどこですか？", POS_REVIEWS_SQL),
]

# --- 指示（text_instructions）は“全体の振る舞い”だけ。SQL ロジック・列値・結合は書かない ---
# ベスプラ: ロジックは example_question_sql / join_specs / 列コメント(06)へ。テキスト指示は書式・回答方針の最終手段。
INSTRUCTIONS = [
    "金額は日本円で表示し、小数 2 桁に丸める。",
    "店舗を答えるときは、常に店舗名（name）と店舗 ID（franchiseID）を併記する。",
    "質問に必要な情報が足りないときは、推測で答えず、不足している点を確認する質問を返す。",
    "ランキングや一覧を求める質問では、結果を LIMIT で切り詰めず全件返す。"
    "ユーザーが『トップ N』のように件数を明示した場合だけ LIMIT を使う。",
]

print("―― SQL 例（6 本・SQL ロジックはここで教える）――")
for q, sql in EXAMPLES:
    print(f"\n# {q}\n{sql}")
print("\n―― 指示（text_instructions・全体の振る舞いだけ）――")
for line in INSTRUCTIONS:
    print("- " + line)

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 2 —（手動・1 回だけ）画面で「SQL 例」を 1 つ登録する
# MAGIC Genie エージェントの画面を開き、上で表示された SQL 例のうち **1 組（たとえば地域別売上）**を手で登録します。
# MAGIC 「知識ストアのどこに設定が入るか」を体で覚えるのが目的です。
# MAGIC
# MAGIC 手順（画面）:
# MAGIC 1. 03 で表示した「画面で開く」リンク（または `/genie` から本エージェント）を開く
# MAGIC 2. **Settings（設定） → Instructions / Example queries（指示・SQL 例）**を開く
# MAGIC 3. 「SQL 例」を追加し、上の**質問**と**SQL**を貼り付けて**保存**する
# MAGIC
# MAGIC <div style="border-left:4px solid #43a047;background:#e8f5e9;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#2e7d32;">✔ 期待される結果</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">画面上に、登録した SQL 例が保存された状態で表示される。</div>
# MAGIC </div>
# MAGIC
# MAGIC <div style="border-left:4px solid #ff9800;background:#fff3e0;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <div style="color:#333;">この手動ステップは「学習のため」です。時間がなければ読み飛ばして次のステップ（API 反映）に進んでも、最終結果は同じになります。</div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 3 —（自動）残りの設定を API で一括反映する
# MAGIC ここからは画面操作なしで、**指示（instructions）・SQL 例・テーブル結合の定義**をコードで書き込みます。
# MAGIC 手順は知識ストアの基本と同じ「取得 → 編集 → 書き戻し」です。**先に現在の内容を取得する**ので、
# MAGIC ステップ 2 で手動登録した分があっても消えません（06 のメタデータもそのまま残ります）。

# COMMAND ----------

ss, etag = genie_get(space_id)
inst = ss.setdefault("instructions", {})

# 指示（text_instructions は最大 1 件・content は文字列の配列）
inst["text_instructions"] = [{
    "id": "aa000000000000000000000000000001",
    "content": INSTRUCTIONS,
}]

# SQL 例（質問 → 正しい SQL。固定 ID・昇順なので再実行しても増えない）
# ここが SQL ロジックの正しい置き場。テキスト指示には書かない（ベスプラ）。
inst["example_question_sqls"] = [
    {"id": f"bb{(i + 1):030d}", "question": [q], "sql": [sql]}
    for i, (q, sql) in enumerate(EXAMPLES)
]

# テーブル結合の定義（列は必ずテーブル別名で修飾する）。固定 ID・昇順。
inst["join_specs"] = [
    {"id": "dd000000000000000000000000000001",
     "left": {"identifier": fq("sales_transactions_gold"), "alias": "transactions"},
     "right": {"identifier": fq("sales_franchises_gold"), "alias": "franchises"},
     "sql": ["`transactions`.`franchiseID` = `franchises`.`franchiseID`",
             "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"]},
    {"id": "dd000000000000000000000000000002",
     "left": {"identifier": fq("sales_transactions_gold"), "alias": "transactions"},
     "right": {"identifier": fq("sales_customers_gold"), "alias": "customers"},
     "sql": ["`transactions`.`customerID` = `customers`.`customerID`",
             "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"]},
    {"id": "dd000000000000000000000000000003",
     "left": {"identifier": fq("sales_franchises_gold"), "alias": "franchises"},
     "right": {"identifier": fq("sales_suppliers_gold"), "alias": "suppliers"},
     "sql": ["`franchises`.`supplierID` = `suppliers`.`supplierID`",
             "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"]},
    {"id": "dd000000000000000000000000000004",
     "left": {"identifier": fq("media_customer_reviews_gold"), "alias": "reviews"},
     "right": {"identifier": fq("sales_franchises_gold"), "alias": "franchises"},
     "sql": ["`reviews`.`ref` = `franchises`.`franchiseID`",
             "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"]},
]

genie_update(space_id, ss, etag)
print("指示（全体の振る舞い 3 件）・SQL 例（6 本）・結合定義（4 本）を API で反映しました（画面操作なし）")

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #43a047;background:#e8f5e9;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#2e7d32;">✔ 期待される結果</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">反映完了のメッセージが表示される。画面を再読み込みすると、指示・SQL 例・結合が入っています。</div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 4 —（体験）同じ質問をもう一度聞いてみる
# MAGIC 数値の前に、まず体感します。03 で外した**地域別売上**の質問を、作り込んだあとのエージェントに
# MAGIC もう一度聞きます。回答と生成 SQL をその場で表示します。
# MAGIC
# MAGIC <div style="border-left:4px solid #1976d2;background:#e3f2fd;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#0d47a1;">🖱️ ここは画面でも試すのがおすすめ（任意）</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">
# MAGIC   03 で開いた Genie の画面（チャット）で、<b>まったく同じ質問</b>をもう一度聞いてみてください。
# MAGIC   03 のときは自己流の区分（例: Oceania / Asia / North America）で外していた答えが、
# MAGIC   整備後は <b>APJ / AMER / EMEA の正しい内訳</b>に変わります。「教えたら直る」瞬間を画面で見るのが、
# MAGIC   このコースいちばんの見せ場です。下のセルは同じことを Notebook 内で表示します。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

genie_show_answer(space_id, "地域別（APJ / AMER / EMEA）の総売上を教えて")

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #43a047;background:#e8f5e9;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#2e7d32;">✔ 期待される結果</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">
# MAGIC   03 のときと違い、教え込んだ地域区分（Japan・Australia→APJ / US・Canada→AMER / …）に沿った
# MAGIC   正しい内訳（主要市場の米国が AMER に入る等）が返ります。生成 SQL にも教えた CASE 式が現れます。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ 5 — 再採点して BEFORE / AFTER を比べる
# MAGIC 04 と同じ **6 問**のベンチマークで、**作り込んだあと**のエージェントを採点します（AFTER スコア）。
# MAGIC 採点には少し時間がかかります（6 問で数分）。完了まで待ちます。

# COMMAND ----------

# 04 で登録した 6 問（同じ ID）を再採点する
BENCH_IDS = [f"cc00000000000000000000000000000{i}" for i in range(1, 7)]

after_correct, after_total, status = genie_run_and_wait(space_id, BENCH_IDS)
save_score("after", after_correct, after_total)

before = load_score("before")
b_txt = f"{before[0]} / {before[1]}" if before else "（04 未実行）"

displayHTML(f"""
<div style="border-left:4px solid #43a047;background:#e8f5e9;padding:16px 20px;border-radius:4px;
     margin:12px 0;font-family:sans-serif;color:#333;">
  <strong style="color:#2e7d32;font-size:1.15em;">BEFORE / AFTER の比較（6 問）</strong>
  <table style="margin-top:12px;border-collapse:collapse;font-size:1.05em;">
    <tr><td style="padding:4px 24px 4px 0;color:#666;">BEFORE（素のエージェント）</td>
        <td style="font-size:1.3em;"><b>{b_txt}</b> 問正解</td></tr>
    <tr><td style="padding:4px 24px 4px 0;color:#666;">AFTER（作り込み後）</td>
        <td style="font-size:1.3em;color:#2e7d32;"><b>{after_correct} / {after_total}</b> 問正解</td></tr>
  </table>
  <div style="color:#666;margin-top:8px;">採点ステータス: {status}</div>
</div>
""")

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #43a047;background:#e8f5e9;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#2e7d32;">✔ 期待される結果</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">
# MAGIC   代表例では <b>BEFORE 2〜3 / 6 → AFTER ほぼ全問（6 / 6 目安）</b>。素で外していた問い（売上トップ N・
# MAGIC   LEFT JOIN・地域区分・レビュー感情）が作り込み後は正しく答えられるようになります。
# MAGIC   実際、上の地域別売上も 03 の自己流区分から APJ / AMER / EMEA の正しい内訳に変わります。
# MAGIC   画面でも同じ質問を試して、答えが変わったことを確認してください。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ チェックポイント

# COMMAND ----------

ok = (after_correct is not None) and (before is None or after_correct >= before[0])
checkpoint(
    f"AFTER スコア: {after_correct} / {after_total} 問正解",
    bool(ok) and status == "DONE",
    f"BEFORE: {b_txt} 問正解 → 作り込みで精度が上がりました。" if before else "BEFORE 未取得（04 を実行すると比較できます）。",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## まとめ
# MAGIC - 業務ルール（地域区分・LEFT JOIN・同名店舗・レビュー感情）を、**指示・SQL 例・結合定義**として教えました。
# MAGIC - 教え込みを「手動 1 回 ＋ API で一括反映」で行い、GUI のコピー＆ペーストの繰り返しを避けました。
# MAGIC - 同じ 6 問で再採点し、**BEFORE → AFTER の精度向上を数値で**確認しました。
# MAGIC
# MAGIC **次のモジュール 08「まとめと次の一歩」** で、ここまでの弧を振り返り、実務への展開（共有・運用・監視）を整理します。
