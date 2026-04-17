from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import json
import os
from datetime import datetime, date
import sqlite3

app = Flask(__name__)
CORS(app)

DB_PATH = "juridicosmart.db"

# ─── BANCO DE DADOS ───────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS intimacoes (
        id TEXT PRIMARY KEY,
        dados TEXT,
        status TEXT DEFAULT 'pendente',
        criado_em TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS agenda (
        id TEXT PRIMARY KEY,
        dados TEXT,
        done INTEGER DEFAULT 0,
        criado_em TEXT
    )''')
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ─── BUSCAR INTIMAÇÕES NO COMUNICA.PJE ────────────
def buscar_intimacoes_api(oab_numero="70659", oab_uf="RS", data_inicio=None, data_fim=None):
    """Tenta buscar via API REST do comunica.pje.jus.br"""
    if not data_inicio:
        data_inicio = date.today().strftime("%Y-%m-%d")
    if not data_fim:
        data_fim = date.today().strftime("%Y-%m-%d")

    # Endpoint da API que o SPA usa internamente
    endpoints = [
        f"https://comunicaapi.pje.jus.br/api/v1/comunicacao",
        f"https://comunica.pje.jus.br/api/v1/comunicacao",
    ]

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://comunica.pje.jus.br/",
        "Origin": "https://comunica.pje.jus.br"
    }

    params = {
        "numeroOab": oab_numero,
        "ufOab": oab_uf.upper(),
        "dataDisponibilizacaoInicio": data_inicio,
        "dataDisponibilizacaoFim": data_fim,
        "pagina": 1,
        "tamanhoPagina": 50
    }

    for endpoint in endpoints:
        try:
            resp = requests.get(endpoint, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                return {"sucesso": True, "dados": resp.json(), "fonte": endpoint}
        except Exception as e:
            print(f"Endpoint {endpoint} falhou: {e}")
            continue

    return {"sucesso": False, "dados": [], "erro": "API não respondeu"}

# ─── ROTAS API ────────────────────────────────────

@app.route("/api/status")
def status():
    return jsonify({"status": "ok", "versao": "1.0", "data": datetime.now().isoformat()})

@app.route("/api/intimacoes/buscar")
def buscar_intimacoes():
    """Busca intimações no comunica.pje.jus.br"""
    oab = request.args.get("oab", "70659")
    uf = request.args.get("uf", "RS")
    data_inicio = request.args.get("inicio", date.today().strftime("%Y-%m-%d"))
    data_fim = request.args.get("fim", date.today().strftime("%Y-%m-%d"))

    resultado = buscar_intimacoes_api(oab, uf, data_inicio, data_fim)
    return jsonify(resultado)

@app.route("/api/intimacoes", methods=["GET"])
def listar_intimacoes():
    """Lista intimações salvas no banco"""
    conn = get_db()
    rows = conn.execute("SELECT * FROM intimacoes ORDER BY criado_em DESC").fetchall()
    conn.close()
    result = []
    for row in rows:
        item = json.loads(row["dados"])
        item["status"] = row["status"]
        result.append(item)
    return jsonify(result)

@app.route("/api/intimacoes", methods=["POST"])
def salvar_intimacao():
    """Salva uma intimação capturada"""
    data = request.json
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO intimacoes (id, dados, status, criado_em) VALUES (?,?,?,?)",
        (data["id"], json.dumps(data), data.get("status","pendente"), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/intimacoes/<id>/status", methods=["PATCH"])
def atualizar_status(id):
    """Atualiza status de uma intimação (pendente/confirmada/apagada)"""
    data = request.json
    conn = get_db()
    conn.execute("UPDATE intimacoes SET status=? WHERE id=?", (data["status"], id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/agenda", methods=["GET"])
def listar_agenda():
    """Lista todos os prazos da agenda"""
    conn = get_db()
    rows = conn.execute("SELECT * FROM agenda ORDER BY criado_em DESC").fetchall()
    conn.close()
    result = []
    for row in rows:
        item = json.loads(row["dados"])
        item["done"] = bool(row["done"])
        result.append(item)
    return jsonify(result)

@app.route("/api/agenda", methods=["POST"])
def criar_prazo():
    """Cria um novo prazo na agenda"""
    data = request.json
    conn = get_db()
    conn.execute(
        "INSERT INTO agenda (id, dados, done, criado_em) VALUES (?,?,?,?)",
        (str(data["id"]), json.dumps(data), 0, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/agenda/<id>/finalizar", methods=["PATCH"])
def finalizar_prazo(id):
    """Marca prazo como finalizado"""
    data = request.json
    done = 1 if data.get("done") else 0
    conn = get_db()
    conn.execute("UPDATE agenda SET done=? WHERE id=?", (done, id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/agenda/<id>", methods=["DELETE"])
def deletar_prazo(id):
    conn = get_db()
    conn.execute("DELETE FROM agenda WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

# ─── INICIALIZAÇÃO ────────────────────────────────
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

init_db()
