from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime, date
import sqlite3

app = Flask(__name__, static_folder='static')
CORS(app)

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

DB_PATH = "juridicosmart.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS intimacoes (
        id TEXT PRIMARY KEY, dados TEXT, status TEXT DEFAULT 'pendente', criado_em TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS agenda (
        id TEXT PRIMARY KEY, dados TEXT, done INTEGER DEFAULT 0, criado_em TEXT
    )''')
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def buscar_com_playwright(oab, uf, data_inicio, data_fim):
    try:
        from playwright.sync_api import sync_playwright
        url = (f"https://comunica.pje.jus.br/consulta"
               f"?dataDisponibilizacaoInicio={data_inicio}&dataDisponibilizacaoFim={data_fim}"
               f"&numeroOab={oab}&ufOab={uf.lower()}")
        respostas_api = []
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage']
            )
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()

            def handle_response(response):
                if 'comunicacao' in response.url and response.status == 200:
                    try:
                        respostas_api.append(response.json())
                    except:
                        pass

            page.on('response', handle_response)
            page.goto(url, wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(5000)
            browser.close()

        if respostas_api:
            return {"sucesso": True, "dados": respostas_api[0], "fonte": "playwright"}
        return {"sucesso": False, "dados": [], "erro": "Nenhum dado retornado pela página"}
    except Exception as e:
        return {"sucesso": False, "dados": [], "erro": str(e)}

@app.route("/api/status")
def status():
    return jsonify({"status": "ok", "versao": "2.0", "data": datetime.now().isoformat()})

@app.route("/api/intimacoes/buscar")
def buscar_intimacoes():
    oab = request.args.get("oab", "70659")
    uf = request.args.get("uf", "RS")
    data_inicio = request.args.get("inicio", date.today().strftime("%Y-%m-%d"))
    data_fim = request.args.get("fim", date.today().strftime("%Y-%m-%d"))
    print(f"Buscando OAB {oab}/{uf} de {data_inicio} a {data_fim}")
    resultado = buscar_com_playwright(oab, uf, data_inicio, data_fim)
    print(f"Resultado: {resultado}")
    return jsonify(resultado)

@app.route("/api/intimacoes", methods=["GET"])
def listar_intimacoes():
    conn = get_db()
    rows = conn.execute("SELECT * FROM intimacoes ORDER BY criado_em DESC").fetchall()
    conn.close()
    return jsonify([{**json.loads(r["dados"]), "status": r["status"]} for r in rows])

@app.route("/api/intimacoes", methods=["POST"])
def salvar_intimacao():
    data = request.json
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO intimacoes (id,dados,status,criado_em) VALUES (?,?,?,?)",
                 (data["id"], json.dumps(data), data.get("status","pendente"), datetime.now().isoformat()))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

@app.route("/api/intimacoes/<id>/status", methods=["PATCH"])
def atualizar_status(id):
    data = request.json
    conn = get_db()
    conn.execute("UPDATE intimacoes SET status=? WHERE id=?", (data["status"], id))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

@app.route("/api/agenda", methods=["GET"])
def listar_agenda():
    conn = get_db()
    rows = conn.execute("SELECT * FROM agenda ORDER BY criado_em DESC").fetchall()
    conn.close()
    return jsonify([{**json.loads(r["dados"]), "done": bool(r["done"])} for r in rows])

@app.route("/api/agenda", methods=["POST"])
def criar_prazo():
    data = request.json
    conn = get_db()
    conn.execute("INSERT INTO agenda (id,dados,done,criado_em) VALUES (?,?,?,?)",
                 (str(data["id"]), json.dumps(data), 0, datetime.now().isoformat()))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

@app.route("/api/agenda/<id>/finalizar", methods=["PATCH"])
def finalizar_prazo(id):
    data = request.json
    conn = get_db()
    conn.execute("UPDATE agenda SET done=? WHERE id=?", (1 if data.get("done") else 0, id))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

@app.route("/api/agenda/<id>", methods=["DELETE"])
def deletar_prazo(id):
    conn = get_db()
    conn.execute("DELETE FROM agenda WHERE id=?", (id,))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
