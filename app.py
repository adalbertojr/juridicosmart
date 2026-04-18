from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime
import requests as req

app = Flask(__name__, static_folder='static')
CORS(app)

SUPABASE_URL = "https://ukuvgtentpxlepdnwin.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVrdXZndGVucnRweGxlcGRyd2xuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY0NzMyMTQsImV4cCI6MjA5MjA0OTIxNH0.VATwEG7-WxcTLGjG8sg6Rj5h1sOqgpFF7VFdOBs92w8"
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def sb_get(table, params=""):
    r = req.get(f"{SUPABASE_URL}/rest/v1/{table}?{params}", headers=HEADERS)
    return r.json() if r.ok else []

def sb_post(table, data):
    r = req.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=HEADERS, json=data)
    return r.ok

def sb_patch(table, match, data):
    r = req.patch(f"{SUPABASE_URL}/rest/v1/{table}?{match}", headers=HEADERS, json=data)
    return r.ok

def sb_delete(table, match):
    r = req.delete(f"{SUPABASE_URL}/rest/v1/{table}?{match}", headers=HEADERS)
    return r.ok

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route("/api/status")
def status():
    return jsonify({"status": "ok", "versao": "3.0", "data": datetime.now().isoformat()})

@app.route("/api/intimacoes", methods=["GET"])
def listar_intimacoes():
    rows = sb_get("intimacoes", "order=criado_em.desc")
    result = []
    for row in rows:
        item = row.get("dados", {})
        if isinstance(item, str):
            item = json.loads(item)
        item["status"] = row.get("status", "pendente")
        result.append(item)
    return jsonify(result)

@app.route("/api/intimacoes", methods=["POST"])
def salvar_intimacao():
    data = request.json
    sb_post("intimacoes", {
        "id": data["id"],
        "dados": data,
        "status": data.get("status", "pendente")
    })
    return jsonify({"ok": True})

@app.route("/api/intimacoes/<id>/status", methods=["PATCH"])
def atualizar_status(id):
    data = request.json
    sb_patch("intimacoes", f"id=eq.{id}", {"status": data["status"]})
    return jsonify({"ok": True})

@app.route("/api/agenda", methods=["GET"])
def listar_agenda():
    rows = sb_get("agenda", "order=criado_em.desc")
    result = []
    for row in rows:
        item = row.get("dados", {})
        if isinstance(item, str):
            item = json.loads(item)
        item["done"] = row.get("done", False)
        result.append(item)
    return jsonify(result)

@app.route("/api/agenda", methods=["POST"])
def criar_prazo():
    data = request.json
    sb_post("agenda", {
        "id": str(data["id"]),
        "dados": data,
        "done": False
    })
    return jsonify({"ok": True})

@app.route("/api/agenda/<id>/finalizar", methods=["PATCH"])
def finalizar_prazo(id):
    data = request.json
    sb_patch("agenda", f"id=eq.{id}", {"done": data.get("done", True)})
    return jsonify({"ok": True})

@app.route("/api/agenda/<id>", methods=["DELETE"])
def deletar_prazo(id):
    sb_delete("agenda", f"id=eq.{id}")
    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
