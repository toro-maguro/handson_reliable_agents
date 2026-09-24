# Databricks notebook source
# MAGIC %md
# MAGIC # 共通セットアップ (Classroom-Setup-Common)
# MAGIC
# MAGIC このノートブックは各モジュールの冒頭から `%run` で呼ばれ、**環境差を吸収しながら冪等に**
# MAGIC ハンズオン用の catalog / schema を用意します。何度実行しても・誰が実行しても壊れません。
# MAGIC
# MAGIC 呼び出し側には次を公開します:
# MAGIC - 変数 `my_catalog` / `my_schema` … 解決済みの書き込み先
# MAGIC - 関数 `setup_tables(...)` … `samples` などから冪等にテーブルを複製
# MAGIC - 関数 `checkpoint(...)` / `check_row_count(...)` … 受講者向けの ✅/❌ 検証表示
# MAGIC
# MAGIC > このノートブック自体は直接開かず、各モジュールから `%run ./Includes/...` してください。

# COMMAND ----------

import re

# --- ウィジェット（インストラクター/受講者が環境ごとに上書きできる） ---------------
# 既定は Free Edition 向けに固定（全受講者が同じ workspace.reliable_agents を使う＝案内が一本化）。
# catalog を空にすると自動解決（CREATE CATALOG 権限があれば labuser_<user>、無ければ現在の catalog）。
dbutils.widgets.text("catalog", "workspace", "1. Catalog (空=自動)")
dbutils.widgets.text("schema",  "reliable_agents", "2. Schema")

_req_catalog = dbutils.widgets.get("catalog").strip()
_schema      = dbutils.widgets.get("schema").strip() or "reliable_agents"


def _safe_uc_name(s: str) -> str:
    """UC 名として安全な文字だけに正規化（英小文字・数字・アンダースコア）。"""
    return re.sub(r"[^a-z0-9_]", "_", s.lower())


_user_email = spark.sql("SELECT current_user()").first()[0]
_user_key   = _safe_uc_name(_user_email.split("@")[0])[:30]


def _try_create_catalog(name: str) -> bool:
    """CREATE CATALOG を試す。権限が無ければ False（例外は握りつぶさず種類で判定）。"""
    try:
        spark.sql(f"CREATE CATALOG IF NOT EXISTS `{name}`")
        return True
    except Exception as e:                                   # noqa: BLE001
        msg = str(e)
        if "PERMISSION_DENIED" in msg or "CREATE CATALOG" in msg:
            return False
        raise


# --- catalog の解決（3経路を1本で吸収） -----------------------------------------
# 1) ウィジェット指定あり → それを使う（作れれば作る／作れなければ既存とみなす）
# 2) 指定なし & CREATE CATALOG 権限あり（Free Edition / Trial）→ labuser_<user> を自動作成
# 3) 指定なし & 権限なし（統制された顧客WS / FE sandbox）→ 現在の書き込み可能 catalog を利用
if _req_catalog:
    _catalog = _req_catalog
    _try_create_catalog(_catalog)
    _resolved_by = "ウィジェット指定"
else:
    _default = f"labuser_{_user_key}"
    if _try_create_catalog(_default):
        _catalog = _default
        _resolved_by = "自動作成 (CREATE CATALOG)"
    else:
        _catalog = spark.sql("SELECT current_catalog()").first()[0]
        _resolved_by = "既存 catalog を利用 (CREATE CATALOG 権限なし)"

# schema は最も広く許可される操作。ここを主軸にする。
spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{_catalog}`.`{_schema}`")
spark.sql(f"USE CATALOG `{_catalog}`")
spark.sql(f"USE SCHEMA `{_schema}`")

my_catalog, my_schema = _catalog, _schema

# COMMAND ----------

# --- 冪等なテーブル複製ヘルパー ---------------------------------------------------
def copy_table(table: str, source: str = "samples.bakehouse", reset: bool = False):
    """source.<table> を my_catalog.my_schema へ複製。既存ならスキップ（reset=True で作り直し）。"""
    tgt = f"`{my_catalog}`.`{my_schema}`.`{table}`"
    if reset:
        spark.sql(f"DROP TABLE IF EXISTS {tgt}")
    spark.sql(f"CREATE TABLE IF NOT EXISTS {tgt} AS SELECT * FROM {source}.`{table}`")


def setup_tables(tables, source: str = "samples.bakehouse", reset: bool = False):
    """テーブル名のリストをまとめて冪等複製。"""
    for t in tables:
        copy_table(t, source=source, reset=reset)


def reset_gold_curation(tables):
    """gold テーブルの列・テーブルコメントを消し、真に『素』の状態に戻す。
    03/04（整備前）の setup から呼ぶ。前回パスの 06 で付与したコメントが残っていても、
    Genie が UC コメントを自動参照して『素なのに正答してしまう』のを防ぐ（失敗ケースの再現性を担保）。
    整備を行う 06/07 の setup からは呼ばない（06 のコメントを消さないため）。"""
    for t in tables:
        fqt = f"`{my_catalog}`.`{my_schema}`.`{t}`"
        try:
            spark.sql(f"COMMENT ON TABLE {fqt} IS ''")
            for f in spark.table(fqt).schema.fields:
                spark.sql(f"ALTER TABLE {fqt} ALTER COLUMN `{f.name}` COMMENT ''")
        except Exception:                                       # noqa: BLE001
            pass


# COMMAND ----------

# --- 受講者向けチェックポイント（詰まりを可視化し、動いたか分からず止まるのを防ぐ） -----------
def checkpoint(label: str, ok: bool, detail: str = ""):
    """✅/❌ の枠を描画。当日「動いたか分からず詰まる」を防ぐ。"""
    color, bg, icon = (("#2e7d32", "#e8f5e9", "✅") if ok else ("#c62828", "#ffebee", "❌"))
    extra = f'<div style="color:#333;margin-top:4px;">{detail}</div>' if detail else ""
    displayHTML(
        f'<div style="border-left:4px solid {color};background:{bg};'
        f'padding:10px 14px;border-radius:4px;margin:8px 0;font-family:sans-serif;">'
        f'<strong style="color:{color};font-size:1.05em;">{icon} {label}</strong>{extra}</div>'
    )


def check_row_count(table: str, expected_min: int = 1) -> int:
    """テーブルの行数を検証してチェックポイント表示。"""
    n = spark.table(f"`{my_catalog}`.`{my_schema}`.`{table}`").count()
    checkpoint(f"{table}: {n:,} 行", n >= expected_min, f"期待: {expected_min:,} 行以上")
    return n


# COMMAND ----------

# --- Genie Agent ヘルパー（03/04/07/08 が使用） -----------------------------------
# Free Edition の Notebook では CLI を前提にできないため REST を api_client 経由で叩く（版に強い）。
# エンドポイント/ボディ形は Free Edition 実機で確定済み（2026-09-24）。eval 系は Beta。
import json, uuid
from databricks.sdk import WorkspaceClient

_w = WorkspaceClient()


def newid() -> str:
    """serialized_space の各要素に必須の 32桁小文字hex ID（ハイフン無し）。"""
    return uuid.uuid4().hex


def genie_warehouse_id() -> str:
    """このWSで使える SQL warehouse の id を自動取得（Free Edition は1台）。id はハードコードしない。"""
    whs = list(_w.warehouses.list())
    if not whs:
        raise RuntimeError("SQL warehouse が見つかりません。Serverless Starter Warehouse を確認してください。")
    return whs[0].id


def fq(table: str) -> str:
    """短いテーブル名を my_catalog.my_schema で完全修飾。"""
    return f"{my_catalog}.{my_schema}.{table}"


def genie_create_space(title: str, tables: list) -> str:
    """tables だけ登録した『素の』Genie space を作成し space_id を返す。"""
    ss = {"version": 2, "data_sources": {"tables": [{"identifier": fq(t)} for t in sorted(tables)]}}
    resp = _w.api_client.do(
        "POST", "/api/2.0/genie/spaces",
        body={"warehouse_id": genie_warehouse_id(), "serialized_space": json.dumps(ss), "title": title})
    return resp["space_id"]


def genie_get(space_id: str):
    """(serialized_space を dict にしたもの, etag) を返す。"""
    g = _w.api_client.do("GET", f"/api/2.0/genie/spaces/{space_id}",
                         query={"include_serialized_space": "true"})
    return json.loads(g["serialized_space"]), g["etag"]


def genie_update(space_id: str, ss: dict, etag: str) -> str:
    """serialized_space を『フル置換』で書き戻す（etag 必須）。新しい etag を返す。"""
    r = _w.api_client.do("PATCH", f"/api/2.0/genie/spaces/{space_id}",
                         body={"serialized_space": json.dumps(ss), "etag": etag})
    return r["etag"]


def genie_run_benchmarks(space_id: str, benchmark_ids: list):
    """登録済み benchmark を eval-run で実行（Beta）。eval_run_id 等を返す。"""
    return _w.api_client.do("POST", f"/api/2.0/genie/spaces/{space_id}/eval-runs",
                            body={"benchmark_ids": benchmark_ids})


def genie_run_and_wait(space_id: str, benchmark_ids: list, poll_sec: int = 15, max_wait: int = 600):
    """eval-run を実行し DONE まで待つ（Beta）。(num_correct, num_questions, status) を返す。"""
    import time
    run = genie_run_benchmarks(space_id, benchmark_ids)
    rid = run["eval_run_id"]
    st = run
    waited = 0
    while waited < max_wait:
        time.sleep(poll_sec)
        waited += poll_sec
        st = _w.api_client.do("GET", f"/api/2.0/genie/spaces/{space_id}/eval-runs/{rid}")
        if st.get("eval_run_status") == "DONE":
            break
    return st.get("num_correct"), st.get("num_questions"), st.get("eval_run_status")


def save_score(tag: str, correct: int, total: int):
    """BEFORE/AFTER のスコアを1テーブルに保存し、モジュールをまたいで比較できるようにする。"""
    t = f"`{my_catalog}`.`{my_schema}`.`_genie_scores`"
    spark.sql(f"CREATE TABLE IF NOT EXISTS {t} (tag STRING, num_correct INT, num_questions INT)")
    spark.sql(f"DELETE FROM {t} WHERE tag = '{tag}'")
    spark.sql(f"INSERT INTO {t} VALUES ('{tag}', {int(correct)}, {int(total)})")


def load_score(tag: str):
    """保存済みスコア (num_correct, num_questions) を返す（無ければ None）。"""
    try:
        r = spark.sql(
            f"SELECT num_correct, num_questions FROM `{my_catalog}`.`{my_schema}`.`_genie_scores` WHERE tag = '{tag}'"
        ).collect()
        return (r[0][0], r[0][1]) if r else None
    except Exception:
        return None


def genie_ask(space_id: str, question: str, max_wait: int = 300, poll_sec: int = 8):
    """エージェントに質問し、(回答テキスト, 生成SQL) を返す。会話 API を使用。
    素→整備で答えがどう変わるかを Notebook 内でそのまま見せるためのヘルパー。"""
    import time
    start = _w.api_client.do("POST", f"/api/2.0/genie/spaces/{space_id}/start-conversation",
                             body={"content": question})
    cid, mid = start["conversation_id"], start["message_id"]
    terminal = {"COMPLETED", "FAILED", "CANCELLED", "QUERY_RESULT_EXPIRED"}
    msg, waited = {}, 0
    while waited < max_wait:
        msg = _w.api_client.do(
            "GET", f"/api/2.0/genie/spaces/{space_id}/conversations/{cid}/messages/{mid}")
        if msg.get("status") in terminal:
            break
        time.sleep(poll_sec)
        waited += poll_sec
    answer, sql = None, None
    for a in msg.get("attachments", []) or []:
        if "text" in a and a["text"].get("purpose") == "TEXT_ATTACHMENT_PURPOSE_ANSWER":
            answer = a["text"].get("content")
        if "query" in a and sql is None:
            sql = a["query"].get("query") or a["query"].get("statement")
    return answer, sql


def genie_show_answer(space_id: str, question: str):
    """質問と回答（＋生成 SQL）を見やすく表示する。返り値は (回答, SQL)。"""
    answer, sql = genie_ask(space_id, question)
    displayHTML(f"""
    <div style="border-left:4px solid #1976d2;background:#e3f2fd;padding:14px 18px;border-radius:4px;
         margin:12px 0;font-family:sans-serif;color:#333;">
      <div style="color:#666;">質問</div>
      <div style="font-size:1.1em;margin:2px 0 10px 0;">{question}</div>
      <div style="color:#666;">Genie の回答</div>
      <div style="font-size:1.05em;margin-top:2px;">{answer or '（回答を取得できませんでした）'}</div>
    </div>
    """)
    if sql:
        print("Genie が生成した SQL:\n" + sql)
    return answer, sql


def genie_trash_space(space_id: str):
    """Genie エージェント（space）をゴミ箱に移動（DELETE）。"""
    _w.api_client.do("DELETE", f"/api/2.0/genie/spaces/{space_id}")


def genie_workspace_link(space_id: str) -> str:
    """このWSの Genie space を開くリンク。"""
    host = _w.config.host.rstrip("/")
    return f"{host}/genie/rooms/{space_id}"


def save_space_id(space_id: str):
    """space_id を1行テーブルに保存し、後続モジュールが引き継げるようにする。"""
    t = f"`{my_catalog}`.`{my_schema}`.`_genie_space`"
    spark.sql(f"CREATE TABLE IF NOT EXISTS {t} (space_id STRING)")
    spark.sql(f"TRUNCATE TABLE {t}")
    spark.sql(f"INSERT INTO {t} VALUES ('{space_id}')")


def load_space_id():
    """保存済み space_id を返す（無ければ None）。"""
    try:
        rows = spark.sql(f"SELECT space_id FROM `{my_catalog}`.`{my_schema}`.`_genie_space`").collect()
        return rows[0]["space_id"] if rows else None
    except Exception:
        return None


# COMMAND ----------

# --- セットアップ情報バナー ------------------------------------------------------
displayHTML(f"""
<div style="border-left:4px solid #1976d2;background:#e3f2fd;padding:14px 18px;
     border-radius:4px;margin:12px 0;font-family:sans-serif;">
  <strong style="color:#0d47a1;font-size:1.1em;">✅ セットアップ完了</strong>
  <table style="margin-top:10px;color:#333;border-collapse:collapse;">
    <tr><td style="padding:2px 16px 2px 0;"><b>ユーザー</b></td><td>{_user_email}</td></tr>
    <tr><td style="padding:2px 16px 2px 0;"><b>Catalog</b></td><td><code>{my_catalog}</code> <span style="color:#666;">（{_resolved_by}）</span></td></tr>
    <tr><td style="padding:2px 16px 2px 0;"><b>Schema</b></td><td><code>{my_schema}</code></td></tr>
  </table>
</div>
""")
