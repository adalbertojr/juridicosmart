from playwright.sync_api import sync_playwright
import requests, re
from datetime import date
import time

NOME = "adalberto bueno junior"
OAB_NUMERO = "70659"
OAB_UF = "rs"
SERVIDOR = "https://juridicosmart.onrender.com"
DATA_INICIO = "2026-04-17"
DATA_FIM = "2026-04-17"
ITENS_POR_PAGINA = 50

def limpar_html(texto):
    if not texto: return ""
    texto = re.sub(r'<style[^>]*>.*?</style>', ' ', texto, flags=re.DOTALL)
    texto = re.sub(r'<script[^>]*>.*?</script>', ' ', texto, flags=re.DOTALL)
    texto = re.sub(r'<[^>]+>', ' ', texto)
    for ent, rep in [('&amp;','&'),('&lt;','<'),('&gt;','>'),('&nbsp;',' ')]:
        texto = texto.replace(ent, rep)
    texto = re.sub(r'\s*[{][^}]*[}]', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

def extrair_campos(texto):
    r = {}
    def pegar(*campos):
        for campo in campos:
            m = re.search(rf'{campo}[:\s]+(.+?)(?=\s+(?:Org|Par|Adv|Cla|Con|Dat|Tip|Mei|Int|com|$))', texto, re.IGNORECASE)
            if m: return m.group(1).strip()
        return ""
    r["processo"] = pegar("Publica..o Processo", "Publicacao Processo", "Publicação Processo", "Processo")
    r["orgao"] = pegar("Org.o", "Orgao")
    partes = re.findall(r'Parte[:\s]+(.+?)(?=\s+(?:Parte|Advogado|Classe|Conte|Intim|\|))', texto, re.IGNORECASE)
    r["partes"] = " x ".join([p.strip() for p in partes]) if partes else ""
    advs = re.findall(r'Advogado[:\s]+(.+?)(?=\s+(?:Advogado|Classe|Conte|\|))', texto, re.IGNORECASE)
    r["advogados"] = " | ".join([a.strip() for a in advs]) if advs else ""
    m = re.search(r'Conte.do[:\s]+(.+?)(?=\s*Intim|comunicacao_id|$)', texto, re.IGNORECASE | re.DOTALL)
    r["conteudo"] = m.group(1).strip() if m else ""
    intims = re.findall(r'Intimado.?\s*/\s*Citado.?[:\s]+(.+?)(?=\s*\||comunicacao_id|$)', texto, re.IGNORECASE)
    r["intimados"] = " | ".join([i.strip() for i in intims]) if intims else ""
    m2 = re.search(r'comunicacao_id[:\s]+(\d+)', texto, re.IGNORECASE)
    r["comunicacao_id"] = m2.group(1) if m2 else ""
    r["classe"] = pegar("Classe")
    r["tipo"] = pegar("Tipo de comunica.o")
    r["diario"] = pegar("di.rio", "Diario")
    return r

def buscar():
    print("="*60)
    print("  JuridicSmart — Buscando no DJN pelo nome")
    print(f"  {NOME.upper()} | {DATA_INICIO}")
    print("="*60)
    
    todas = {}
    textos_djn = []  # textos capturados da pagina do DJN

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36")
        page = ctx.new_page()

        def captura(response):
            if "comunicaapi.pje.jus.br" in response.url and response.status == 200:
                try:
                    todas[response.url] = response.json()
                    print(f"  API: ...{response.url[-50:]}")
                except: pass

        page.on("response", captura)

        # 1. Busca por OAB (para pegar IDs)
        url_oab = (f"https://comunica.pje.jus.br/consulta"
                   f"?dataDisponibilizacaoInicio={DATA_INICIO}&dataDisponibilizacaoFim={DATA_FIM}"
                   f"&numeroOab={OAB_NUMERO}&ufOab={OAB_UF}&pagina=1&itensPorPagina={ITENS_POR_PAGINA}")
        print("\n1. Buscando por OAB...")
        page.goto(url_oab, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(4000)

        # 2. Busca por NOME no DJN (para pegar texto completo)
        nome_url = NOME.replace(" ", "+")
        url_nome = (f"https://comunica.pje.jus.br/consulta"
                    f"?dataDisponibilizacaoInicio={DATA_INICIO}&dataDisponibilizacaoFim={DATA_FIM}"
                    f"&nomeAdvogado={nome_url}&pagina=1&itensPorPagina={ITENS_POR_PAGINA}")
        print("2. Buscando por nome...")
        page.goto(url_nome, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(4000)

        # 3. Captura texto da pagina (HTML renderizado)
        print("3. Capturando texto da pagina...")
        conteudo_pagina = limpar_html(page.content())
        
        # Extrai blocos de publicacao do texto da pagina
        # Cada publicacao comeca com "Publicacao Processo:" ou "comunicacao_id:"
        blocos = re.split(r'(?=Publica..o Processo:|comunicacao_id:)', conteudo_pagina, flags=re.IGNORECASE)
        for bloco in blocos:
            if "BUENO" in bloco.upper() or OAB_NUMERO in bloco:
                textos_djn.append(bloco)
                print(f"  Bloco DJN encontrado: {bloco[:80]}...")

        # 4. Busca teor individual de cada ID
        ids = []
        for u, d in todas.items():
            items = d if isinstance(d,list) else (d.get("comunicacoes") or d.get("content") or d.get("items") or d.get("data") or [])
            for item in items:
                id_ = item.get("id") or item.get("numeroComunicacao")
                if id_ and str(id_) not in ids: ids.append(str(id_))

        print(f"\n4. Buscando teor de {len(ids)} intimacao(oes)...")
        for id_ in ids[:30]:
            print(f"  ID {id_}...")
            try:
                page.goto(f"https://comunica.pje.jus.br/comunicacao/{id_}", wait_until="networkidle", timeout=15000)
                page.wait_for_timeout(2000)
            except: pass

        browser.close()

    # Processa dados da API
    print("\nProcessando...")
    mapa = {}
    
    for u, d in todas.items():
        items = d if isinstance(d,list) else (d.get("comunicacoes") or d.get("content") or d.get("items") or d.get("data") or ([d] if "id" in d else []))
        for item in items:
            id_ = str(item.get("id") or item.get("numeroComunicacao") or "")
            if not id_: continue

            teor_raw = item.get("teor") or item.get("texto") or item.get("conteudo") or item.get("inteiroTeor") or ""
            teor = limpar_html(teor_raw)
            
            # Tenta encontrar bloco DJN correspondente a este ID
            bloco_djn = ""
            for bloco in textos_djn:
                if id_ in bloco:
                    bloco_djn = bloco
                    break
            
            # Usa bloco DJN se disponivel, senao usa teor da API
            texto_base = bloco_djn if bloco_djn else teor
            campos = extrair_campos(texto_base) if texto_base else {}
            
            com_id = campos.get("comunicacao_id") or id_
            ant = mapa.get(com_id, {})

            partes_api = item.get("partes") or []
            nomes_api = " x ".join([p.get("nome","") for p in partes_api]) if isinstance(partes_api,list) else ""

            processo = campos.get("processo") or item.get("numeroProcesso") or ant.get("processo","")
            orgao = campos.get("orgao") or item.get("nomeOrgao") or ant.get("orgao","")
            partes = campos.get("partes") or nomes_api or ant.get("partes","")
            advogados = campos.get("advogados") or ant.get("advogados","")
            conteudo = campos.get("conteudo") or ant.get("conteudo","")
            intimados = campos.get("intimados") or ant.get("intimados","")
            diario = campos.get("diario") or item.get("siglaTribunal") or item.get("nomeOrgao") or ant.get("diario","DJN")

            txt = ""
            if processo: txt += f"Processo: {processo}\n"
            if orgao: txt += f"Orgao: {orgao}\n"
            if campos.get("tipo"): txt += f"Tipo: {campos['tipo']}\n"
            if campos.get("classe"): txt += f"Classe: {campos['classe']}\n"
            if partes: txt += f"Partes: {partes}\n"
            if advogados: txt += f"Advogados: {advogados}\n"
            if intimados: txt += f"Intimados: {intimados}\n"
            if conteudo: txt += f"\n{conteudo}"
            if not txt: txt = texto_base[:500] if texto_base else f"Intimacao {com_id}"

            novo = {
                "id": com_id,
                "diario": diario,
                "disponibilizacao": item.get("dataDisponibilizacao") or ant.get("disponibilizacao", DATA_INICIO),
                "publicacao": item.get("dataPublicacao") or ant.get("publicacao", DATA_FIM),
                "numero": str(item.get("numeroComunicacao") or com_id),
                "processo": processo,
                "orgao": orgao,
                "partes": partes,
                "texto": txt,
                "status": "pendente"
            }

            if len(novo["texto"]) >= len(ant.get("texto","")): mapa[com_id] = novo
            elif com_id not in mapa: mapa[com_id] = novo

    unicas = list(mapa.values())
    print(f"  {len(unicas)} intimacao(oes) encontrada(s)\n")
    
    if not unicas:
        print("Nenhuma intimacao encontrada.")
        input("\nEnter para fechar...")
        return

    print(f"Enviando para {SERVIDOR}...")
    ok = 0
    for i in unicas:
        for t in range(3):
            try:
                r = requests.post(f"{SERVIDOR}/api/intimacoes", json=i, timeout=30)
                if r.status_code == 200:
                    ok += 1; print(f"  OK: {i.get('processo') or i['id']}"); break
                elif t < 2: time.sleep(3)
            except:
                if t < 2: print(f"  Tentando {t+2}/3..."); time.sleep(5)
                else: print(f"  Falhou: {i['id']}")

    print(f"\n{'='*60}\n  {ok} enviada(s)!\n  Acesse: {SERVIDOR}\n{'='*60}")
    input("\nEnter para fechar...")

buscar()
