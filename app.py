from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json, os, sqlite3
from datetime import datetime

app = Flask(__name__, static_folder='static')
CORS(app)

DB_PATH = "/tmp/juridicosmart.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS intimacoes (id TEXT PRIMARY KEY, dados TEXT, status TEXT DEFAULT 'pendente', criado_em TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS agenda (id TEXT PRIMARY KEY, dados TEXT, done INTEGER DEFAULT 0, criado_em TEXT)")
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route("/api/status")
def status():
    return jsonify({"status": "ok", "versao": "4.1", "data": datetime.now().isoformat()})

@app.route("/api/intimacoes", methods=["GET"])
def listar_intimacoes():
    conn = get_db()
    rows = conn.execute("SELECT dados, status FROM intimacoes ORDER BY criado_em DESC").fetchall()
    conn.close()
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
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO intimacoes (id,dados,status,criado_em) VALUES (?,?,?,?)",
        [str(data["id"]), json.dumps(data), data.get("status","pendente"), datetime.now().isoformat()])
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/intimacoes/<id>/status", methods=["PATCH"])
def atualizar_status(id):
    data = request.json
    conn = get_db()
    conn.execute("UPDATE intimacoes SET status=? WHERE id=?", [data["status"], id])
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/agenda", methods=["GET"])
def listar_agenda():
    conn = get_db()
    rows = conn.execute("SELECT dados, done FROM agenda ORDER BY criado_em DESC").fetchall()
    conn.close()
    result = []
    for row in rows:
        try: item = json.loads(row[0])
        except: item = {}
        item["done"] = bool(row[1])
        result.append(item)
    return jsonify(result)

@app.route("/api/agenda", methods=["POST"])
def criar_prazo():
    data = request.json
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO agenda (id,dados,done,criado_em) VALUES (?,?,?,?)",
        [str(data["id"]), json.dumps(data), 0, datetime.now().isoformat()])
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/agenda/<id>/finalizar", methods=["PATCH"])
def finalizar_prazo(id):
    data = request.json
    conn = get_db()
    conn.execute("UPDATE agenda SET done=? WHERE id=?", [1 if data.get("done") else 0, id])
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/agenda/<id>", methods=["DELETE"])
def deletar_prazo(id):
    conn = get_db()
    conn.execute("DELETE FROM agenda WHERE id=?", [id])
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
