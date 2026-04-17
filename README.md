# JurídicoSmart — Deploy no Render

## Passo a passo completo

### 1. Criar conta no GitHub (grátis)
Acesse https://github.com e crie uma conta gratuita com seu e-mail.

### 2. Criar repositório
- Clique em "New repository"
- Nome: `juridicosmart`
- Marque "Public"
- Clique "Create repository"

### 3. Fazer upload dos arquivos
- Clique em "uploading an existing file"
- Arraste todos os arquivos desta pasta (app.py, requirements.txt, render.yaml)
- Clique "Commit changes"

### 4. Conectar Render ao GitHub
- Acesse https://render.com
- Clique "New +" → "Web Service"
- Conecte sua conta GitHub
- Selecione o repositório "juridicosmart"
- Clique "Connect"

### 5. Configurar o serviço
- Name: juridicosmart
- Environment: Python 3
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`
- Clique "Create Web Service"

### 6. Aguardar o deploy
O Render vai instalar as dependências e iniciar o servidor.
Quando aparecer "Live", copie a URL (ex: https://juridicosmart.onrender.com)

### 7. Configurar o frontend
- Abra o arquivo index.html no navegador
- Vá na aba "Configurações"
- Cole a URL do Render
- Clique "Salvar"

Pronto! O sistema está funcionando.

## Estrutura dos arquivos
```
juridicosmart/
├── app.py              # Servidor Flask (backend)
├── requirements.txt    # Dependências Python
├── render.yaml         # Configuração do Render
└── static/
    └── index.html      # Interface web (frontend)
```

## Endpoints da API
- GET  /api/status                    → Status do servidor
- GET  /api/intimacoes/buscar         → Busca no comunica.pje.jus.br
- GET  /api/intimacoes                → Lista intimações salvas
- POST /api/intimacoes                → Salva uma intimação
- PATCH /api/intimacoes/:id/status   → Atualiza status
- GET  /api/agenda                    → Lista prazos
- POST /api/agenda                    → Cria prazo
- PATCH /api/agenda/:id/finalizar    → Finaliza prazo
