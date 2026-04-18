from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json, os
from datetime import datetime
import libsql_client

app = Flask(__name__, static_folder='static')
CORS(app)

TURSO_URL = "libsql://juridicosmart-adalbertojr.aws-us-east-2.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3NzY1MTk4NzgsImlkIjoiMDE5ZGEwZDUtNGEwMS03NzZjLWIzNGUtNDJmY2RkODVmMWM2IiwicmlkIjoiZjdiOWU5MjctZjBlMy00NzRmLWE3OGItZDBjMjdiYWVmMjFmIn0.jMq5FtUE-NX-yTEPq8OKLIFG1TvMl3XmgI35yhUSnBB7lZOiXIuZouQ5sM3kpQu66bQJEvm-vcLCh1-TsYqDAg"

def get_db():
    return libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_TOKEN)

def init_db():
    with get_db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS intimacoes (
            id TEXT PRIMARY KEY, dados TEXT,
            status TEXT DEFAULT 'pendente', criado_em TEXT)""")
        db.execute("""CREATE TABLE IF NOT EXISTS agenda (
            id TEXT PRIMARY KEY, dados TEXT,
            done INTEGER DEFAULT 0, criado_em TEXT)""")

@app.route('/
