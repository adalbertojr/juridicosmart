from playwright.sync_api import sync_playwright
import requests, re
from datetime import date
import time

OAB_NUMERO = "70659"
OAB_UF = "rs"
NOME = "adalberto bueno junior"
SERVIDOR = "https://juridicosmart.onrender.com"
DATA_INICIO = date.today().strftime("%Y-%m-%d")
DATA_FIM = date.today().strftime("%Y-%m-%d")
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

def e_minha_intimacao(item, teor):
    oab_patterns = [f"RS-{OAB_NUMERO}", f"RS {OAB_NUMERO}", f"RS0{OAB_NUMERO}", f"RS070659", NOME.upper()]
    texto_check = (teor + str(item)).upper()
    return any(p.upper() in texto_check for p in oab_patterns)

def extrair_campos(texto):
    r = {}
    def pegar(campos_lista):
        for campo in campos_lista:
            m = re.search(rf'{campo}[:\s]+(.+?)(?=\s+(?:Orgao|Parte|Advogado|Classe|Conteudo|Data de|Tipo|Meio|Inteiro|Intimado|comunicacao_id|$))', texto, re.IGNORECASE)
            if m: return m.group(1).strip()
        return ""
    r["processo"] = pegar(["Publicacao Processo", "Publicação Processo", "Processo"])
    r["orgao"] = pegar(["Orgao", "Órgão"])
    partes = re.findall(r'Parte[:\s]+(.+?)(?=\s+(?:Parte|Advogado|Classe|Conteudo|\|))', texto, re.IGNORECASE)
    r["partes"] = " x ".join([p.strip() for p in partes]) if partes else ""
    advs = re.findall(r'Advogado[:\s]+(.+?)(?=\s+(?:Advogado|Classe|Conteudo|\|))', texto, re.IGNORECASE)
    r["advogados"] = " | ".join([a.strip() for a in advs]) if advs else ""
    m = re.search(r'Conteudo[:\s]+(.+?)(?=\s*Intimado|comunicacao_id|$)', texto, re.IGNORECASE | re.DOTALL)
    r["conteudo"] = m.group(1).strip() if m else ""
    intimados = re.findall(r'Intimado[s]?\s*/\s*Citado[s]?[:\s]+(.+?)(?=\s*\||comunicacao_id|$)', texto, re.IGNORECASE)
    r["intimados"] = " | ".join([i.strip() for i in intimados]) if intimados else ""
    m2 = re.search(r'comunicacao_id[:\s]+(\d+)', texto, re.IGNORECASE)
    r["comunicacao_id"] = m2.group(1) if m2 else ""
    r["classe"] = pegar(["Classe"])
    r["tipo"] = pegar(["Tipo de comunicacao", "Tipo de comunicação"])
    return r

def buscar():
    print("="*60)
    print("  JuridicSmart — Buscando intimacoes")
    print(f"  OAB/RS {OAB_NUMERO} | Data: {DATA_INICIO}")
    print("="*60)
    todas = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36")
        page = ctx.new_page()

        def captura(response):
            if "comunicaapi.pje.jus.br" in response.url and response.status == 200:
                try:
                    todas[response.url] = response.json()
                    print(f"  API: ...{response.url[-55:]}")
                except: pass

        page.on("response", captura)

        url_oab = (f"https://comunica.pje.jus.br/consulta"
                   f"?dataDisponibilizacaoInicio={DATA_INICIO}&dataDisponibilizacaoFim={DATA_FIM}"
                   f"&numeroOab={OAB_NUMERO}&ufOab={OAB_UF}&pagina=1&itensPorPagina={ITENS_POR_PAGINA}")
        print("Buscando por OAB...")
        page.goto(url_oab, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(4000)

        ids = []
        for u, d in todas.items():
            items = d if isinstance(d,list) else (d.get("comunicacoes") or d.get("content") or d.get("items") or d.get("data") or [])
            for item in items:
                id_ = item.get("id") or item.get("numeroComunicacao")
                if id_ and str(id_) not in ids: ids.append(str(id_))

        print(f"\nBuscando teor de {len(ids)} intimacao(oes)...")
        for id_ in ids[:30]:
            print(f"  ID {id_}...")
            try:
                page.goto(f"https://comunica.pje.jus.br/comunicacao/{id_}", wait_until="networkidle", timeout=15000)
                page.wait_for_timeout(2000)
            except: pass

        browser.close()

    print("\nProcessando e filtrando...")
    mapa = {}
    for u, d in todas.items():
        items = d if isinstance(d,list) else (d.get("comunicacoes") or d.get("content") or d.get("items") or d.get("data") or ([d] if "id" in d else []))
        for item in items:
            id_ = str(item.get("id") or item.get("numeroComunicacao") or "")
            if not id_: continue

            teor_raw = item.get("teor") or item.get("texto") or item.get("conteudo") or item.get("inteiroTeor") or ""
            teor = limpar_html(teor_raw)
            campos = extrair_campos(teor) if teor else {}
            com_id = campos.get("comunicacao_id") or id_

            # Filtra apenas suas intimacoes
            if not e_minha_intimacao(item, teor):
                print(f"  IGNORADO (nao e sua): {com_id}")
                continue

            partes_api = item.get("partes") or []
            nomes_api = " x ".join([p.get("nome","") for p in partes_api]) if isinstance(partes_api,list) else ""

            ant = mapa.get(com_id, {})
            processo = campos.get("processo") or item.get("numeroProcesso") or ant.get("processo","")
            orgao = campos.get("orgao") or item.get("nomeOrgao") or ant.get("orgao","")
            partes = campos.get("partes") or nomes_api or ant.get("partes","")
            advogados = campos.get("advogados") or ant.get("advogados","")
            conteudo = campos.get("conteudo") or ant.get("conteudo","")
            intimados = campos.get("intimados") or ant.get("intimados","")

            txt = ""
            if processo: txt += f"Processo: {processo}\n"
            if orgao: txt += f"Orgao: {orgao}\n"
            if campos.get("tipo"): txt += f"Tipo: {campos['tipo']}\n"
            if campos.get("classe"): txt += f"Classe: {campos['classe']}\n"
            if partes: txt += f"Partes: {partes}\n"
            if advogados: txt += f"Advogados: {advogados}\n"
            if intimados: txt += f"Intimados: {intimados}\n"
            if conteudo: txt += f"\n{conteudo}"
            if not txt: txt = teor or f"Intimacao {com_id}"

            novo = {
                "id": com_id,
                "diario": item.get("siglaTribunal") or item.get("nomeOrgao") or ant.get("diario","DJN"),
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
    print(f"\n  {len(unicas)} intimacao(oes) suas encontrada(s)\n")
    if not unicas:
        print("Nenhuma intimacao sua hoje.")
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
