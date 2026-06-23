"""
Investigação profunda de Gupy e Catho - Buscando alternativas e soluções
"""

import requests
from bs4 import BeautifulSoup
import json
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

print("\n" + "="*80)
print("🔬 INVESTIGAÇÃO PROFUNDA: Gupy e Catho")
print("="*80 + "\n")

# ──────────────────────────────────────────────────────────────────────────────
# GUPY - Investigação completa
# ──────────────────────────────────────────────────────────────────────────────

print("1️⃣  GUPY - Investigação Completa")
print("-" * 80 + "\n")

# Teste 1: Verificar página principal
print("Teste 1: Verificar página principal do Gupy")
try:
    r = requests.get("https://gupy.io", headers=HEADERS, timeout=10)
    print(f"  https://gupy.io — Status: {r.status_code}")
except Exception as e:
    print(f"  Erro: {e}")

# Teste 2: Verificar se há API pública alternativa
print("\nTeste 2: Testar endpoints alternativos da API")
api_endpoints = [
    "https://api.portal.gupy.io/api/v1/jobs",
    "https://api.gupy.io/v1/jobs",
    "https://gupy.io/api/v1/jobs",
    "https://portal.gupy.io/api/v2/jobs",  # v2
    "https://api.gupy.io/jobs",
]

for endpoint in api_endpoints:
    try:
        r = requests.get(endpoint, params={"jobName": "logistica"}, timeout=8)
        print(f"  {endpoint}")
        print(f"    Status: {r.status_code} | Content-Type: {r.headers.get('content-type', 'N/A')[:50]}")
        
        if r.status_code == 200 and "json" in r.headers.get("content-type", "").lower():
            try:
                data = r.json()
                print(f"    ✓ JSON válido! Dados: {list(data.keys())}")
            except:
                print(f"    Content length: {len(r.text)} bytes")
    except Exception as e:
        print(f"  {endpoint} — ❌ {type(e).__name__}")

# Teste 3: Tentar fazer scraping direto do site
print("\nTeste 3: Scraping direto de https://portal.gupy.io")
try:
    r = requests.get("https://portal.gupy.io", headers=HEADERS, timeout=10)
    print(f"  Status: {r.status_code}")
    
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Procurar por elementos que contenham vagas
        scripts = soup.find_all("script", type="application/json")
        print(f"  Scripts JSON encontrados: {len(scripts)}")
        
        if scripts:
            for i, script in enumerate(scripts[:2]):
                try:
                    data = json.loads(script.string)
                    print(f"  Script {i}: {list(data.keys())[:5]} vagas potenciais")
                except:
                    print(f"  Script {i}: Não é JSON válido")
        
        # Procurar por elementos de vaga
        vagas = soup.find_all(["article", "div"], {"data-testid": lambda x: x and "job" in x.lower()})
        print(f"  Elementos de vaga encontrados: {len(vagas)}")
        
except Exception as e:
    print(f"  Erro: {e}")

# ──────────────────────────────────────────────────────────────────────────────
# CATHO - Investigação completa
# ──────────────────────────────────────────────────────────────────────────────

print("\n\n2️⃣  CATHO - Investigação Completa")
print("-" * 80 + "\n")

# Teste 1: Diferentes URLs
print("Teste 1: Testar diferentes URLs do Catho")
catho_urls = [
    "https://www.catho.com.br/vagas/logistica/",
    "https://www.catho.com.br/vagas/logistica-sao-paulo/",
    "https://www.catho.com.br/vagas/logistica-aerea/",
    "https://www.catho.com.br/vagas?q=logistica&city=sao-paulo",
    "https://catho.com.br/vagas/logistica",
    "https://mobile.catho.com.br/vagas/logistica",
]

for url in catho_urls:
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        print(f"  {url[:60]}... — Status: {r.status_code}")
    except Exception as e:
        print(f"  {url[:60]}... — ❌ {type(e).__name__}")

# Teste 2: API do Catho
print("\nTeste 2: Testar API do Catho")
api_urls = [
    "https://api.catho.com.br/api/v2/vagas",
    "https://api.catho.com.br/api/vagas",
    "https://api.catho.com.br/vagas",
]

for url in api_urls:
    try:
        r = requests.get(url, params={"q": "logistica"}, headers=HEADERS, timeout=8)
        print(f"  {url} — Status: {r.status_code}")
    except Exception as e:
        print(f"  {url} — ❌ {type(e).__name__}")

# Teste 3: Busca com JavaScript (verificar se página é dinâmica)
print("\nTeste 3: Verificar se Catho usa conteúdo dinâmico (JavaScript)")
try:
    r = requests.get("https://www.catho.com.br/vagas/", headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    
    # Procurar por React/Vue/Angular
    html_str = r.text[:5000]
    if "react" in html_str.lower():
        print("  ⚠️  Detectado React — Pode precisar de Selenium/Playwright")
    if "vue" in html_str.lower():
        print("  ⚠️  Detectado Vue — Pode precisar de Selenium/Playwright")
    if "angular" in html_str.lower():
        print("  ⚠️  Detectado Angular — Pode precisar de Selenium/Playwright")
    
    # Procurar por dados em atributos
    elements_with_data = soup.find_all(True, {"data-*": True})
    print(f"  Elementos com data-* attributes: {len(elements_with_data)}")
    
except Exception as e:
    print(f"  Erro: {e}")

# ──────────────────────────────────────────────────────────────────────────────
# ALTERNATIVAS RECOMENDADAS
# ──────────────────────────────────────────────────────────────────────────────

print("\n\n3️⃣  ALTERNATIVAS RECOMENDADAS")
print("-" * 80 + "\n")

print("Opções para corrigir Gupy:")
print("  a) Usar Selenium/Playwright — Para sites dinâmicos")
print("  b) Verificar GitHub — Ver se há lib oficial do Gupy")
print("  c) Usar Indeed ou LinkedIn — Alternativas populares")
print()

print("Opções para corrigir Catho:")
print("  a) Usar Selenium — Para scraping com JavaScript")
print("  b) Encontrar nova URL/API — Pesquisar estrutura atual")
print("  c) Adicionar User-Agent rotativo — Pode estar bloqueando")
print()

# ──────────────────────────────────────────────────────────────────────────────
# TESTAR INDEED COMO ALTERNATIVA
# ──────────────────────────────────────────────────────────────────────────────

print("\n4️⃣  TESTAR INDEED COMO ALTERNATIVA")
print("-" * 80 + "\n")

try:
    url = "https://br.indeed.com/jobs?q=logistica+aerea&l=sao+paulo&sort=date"
    print(f"Testando Indeed: {url}\n")
    
    r = requests.get(url, headers=HEADERS, timeout=10)
    print(f"Status: {r.status_code}")
    
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Procurar por job cards
        jobs = soup.find_all("div", {"data-testid": "job-item"})
        print(f"Job items encontrados: {len(jobs)}")
        
        if jobs:
            print("\nPrimeiro resultado:")
            job = jobs[0]
            title = job.find("h2")
            company = job.find("span", {"data-testid": "company-name"})
            print(f"  Título: {title.get_text(strip=True) if title else 'N/A'}")
            print(f"  Empresa: {company.get_text(strip=True) if company else 'N/A'}")
    else:
        print("❌ Status não 200")
        
except Exception as e:
    print(f"❌ Erro: {e}")

print("\n" + "="*80)
print("✅ Investigação concluída!")
print("="*80 + "\n")
