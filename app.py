from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json, os, requests as httpx
from datetime import datetime

app = Flask(__name__, static_folder='static')
CORS(app)

TURSO_URL = "https://juridicosmart-adalbertojr.aws-us-east-2.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3NzY1MTk4NzgsImlkIjoiMDE5ZGEwZDUtNGEwMS03NzZjLWIzNGUtNDJmY2RkODVmMWM2IiwicmlkIjoiZjdiOWU5MjctZjBlMy00NzRmLWE3OGItZDBjMjdiYWVmMjFmIn0.jMq5FtUE-NX-yTEPq8OKLIFG1TvMl3XmgI35yhUSnBB7lZOiXIuZouQ5sM3kpQu66bQJEvm-vcLCh1-TsYqDAg"
HEADERS = {"Authorization": f"Bearer {TURSO_TOKEN}", "Content-Type": "application/json"}

def sql(stmt, args=[]):
    body = {"requests": [{"type": "execute", "stmt": {"sql": stmt, "args": [{"type": "text", "value": str(a)} for a in args]}}, {"type": "close"}]}
    r = httpx.post(f"{TURSO_URL}/v3/pipeline", headers=HEADERS, json=body, timeout=15)
    print(f"SQL {r.status_code}: {stmt[:60]}")
    if not r.ok:
        print(f"Error: {r.text[:200]}")
        return []
    try:
        res = r.json()
        rows = res["results"][0]["response"]["result"]["rows"]
        return [[col["value"] for col in row] for row in rows]
    except Exception as e:
        print(f"Parse error: {e} | {r.text[:200]}")
        return []

def init_db():
    sql("CREATE TABLE IF NOT EXISTS intimacoes (id TEXT PRIMARY KEY, dados TEXT, status TEXT DEFAULT 'pendente', criado_em TEXT)")
    sql("CREATE TABLE IF NOT EXISTS agenda (id TEXT PRIMARY KEY, dados TEXT, done INTEGER DEFAULT 0, criado_em TEXT)")

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route("/api/status")
def status():
    return jsonify({"status": "ok", "versao": "6.0-turso", "data": datetime.now().isoformat()})

@app.route("/api/intimacoes", methods=["GET"])
def listar_intimacoes():
    rows = sql("SELECT dados, status FROM intimacoes ORDER BY criado_em DESC")
    result = []
    for row in rows:
        try: item = json.loads(row[0])
        except: item = {}
        item["status"] = row[1]
        result.append(item)
    return jsonify(result)

@app.route("/api/intimacoes", methods=["POST"])
def salvar_intimacao():
    data = request.json
    sql("INSERT OR REPLACE INTO intimacoes (id,dados,status,criado_em) VALUES (?,?,?,?)",
        [str(data["id"]), json.dumps(data), data.get("status","pendente"), datetime.now().isoformat()])
    return jsonify({"ok": True})

@app.route("/api/intimacoes/<id>/status", methods=["PATCH"])
def atualizar_status(id):
    data = request.json
    sql("UPDATE intimacoes SET status=? WHERE id=?", [data["status"], id])
    return jsonify({"ok": True})

@app.route("/api/agenda", methods=["GET"])
def listar_agenda():
    rows = sql("SELECT dados, done FROM agenda ORDER BY criado_em DESC")
    result = []
    for row in rows:
        try: item = json.loads(row[0])
        except: item = {}
        item["done"] = bool(int(row[1]))
        result.append(item)
    return jsonify(result)

@app.route("/api/agenda", methods=["POST"])
def criar_prazo():
    data = request.json
    sql("INSERT OR REPLACE INTO agenda (id,dados,done,criado_em) VALUES (?,?,?,?)",
        [str(data["id"]), json.dumps(data), "0", datetime.now().isoformat()])
    return jsonify({"ok": True})

@app.route("/api/agenda/<id>/finalizar", methods=["PATCH"])
def finalizar_prazo(id):
    data = request.json
    sql("UPDATE agenda SET done=? WHERE id=?", ["1" if data.get("done") else "0", id])
    return jsonify({"ok": True})

@app.route("/api/agenda/<id>", methods=["DELETE"])
def deletar_prazo(id):
    sql("DELETE FROM agenda WHERE id=?", [id])
    return jsonify({"ok": True})

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
