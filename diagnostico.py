"""
Diagnóstico para encontrar problemas nos URLs do scraper
Testa URLs geradas e verifica estrutura HTML dos sites
"""

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
}

print("\n" + "="*60)
print("🔍 DIAGNÓSTICO: Testando URLs e estrutura HTML")
print("="*60 + "\n")

# ── Teste 1: Catho ─────────────────────────────────────────────

print("1️⃣  CATHO - Testando URL e seletores CSS")
print("-" * 60)

catho_url = "https://www.catho.com.br/vagas/logistica-aerea-sao-paulo/?q=logistica%20aerea%20sao%20paulo&page=1"
print(f"URL: {catho_url}\n")

try:
    r = requests.get(catho_url, headers=HEADERS, timeout=15)
    print(f"Status HTTP: {r.status_code}")
    
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Teste de seletores
        selectors_test = [
            ("[data-testid='job-card']", "job-card data-testid"),
            (".job-list-item", "job-list-item class"),
            ("article", "article tag"),
            (".job-item", "job-item class"),
            (".resultado", "resultado class"),
        ]
        
        print("\nTentando encontrar vagas com diferentes seletores:")
        for selector, desc in selectors_test:
            found = soup.select(selector)
            print(f"  ✓ Seletor '{selector}' ({desc}): {len(found)} elementos")
            if found and len(found) > 0:
                print(f"    → Primeiro elemento: {str(found[0])[:100]}...")
        
        # Procura por links
        links = soup.find_all("a", href=True)
        print(f"\n  Total de links na página: {len(links)}")
        job_links = [l for l in links if "vaga" in l.get("href", "").lower()]
        print(f"  Links que parecem ser vagas: {len(job_links)}")
        if job_links:
            print(f"  Exemplo: {job_links[0]['href'][:80]}")
            
    else:
        print(f"❌ Erro HTTP {r.status_code}")
except Exception as e:
    print(f"❌ Erro: {e}")

# ── Teste 2: Vagas.com ─────────────────────────────────────────

print("\n\n2️⃣  VAGAS.COM - Testando URL e seletores CSS")
print("-" * 60)

vagas_url = "https://www.vagas.com.br/vagas-de-logistica-aerea-em-sao-paulo-sp"
print(f"URL: {vagas_url}\n")

try:
    r = requests.get(vagas_url, headers=HEADERS, timeout=15)
    print(f"Status HTTP: {r.status_code}")
    
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Teste de seletores
        selectors_test = [
            (".job-shortdescription", "job-shortdescription class"),
            ("li.vaga", "li.vaga class"),
            (".vaga-item", "vaga-item class"),
            (".resultado", "resultado class"),
            ("[data-testid]", "data-testid"),
        ]
        
        print("\nTentando encontrar vagas com diferentes seletores:")
        for selector, desc in selectors_test:
            found = soup.select(selector)
            print(f"  ✓ Seletor '{selector}' ({desc}): {len(found)} elementos")
            if found and len(found) > 0:
                print(f"    → Primeiro elemento: {str(found[0])[:100]}...")
        
        # Procura por links de vaga
        links = soup.find_all("a", href=True)
        print(f"\n  Total de links na página: {len(links)}")
        job_links = [l for l in links if "/vaga/" in l.get("href", "").lower()]
        print(f"  Links que parecem ser vagas: {len(job_links)}")
        if job_links:
            print(f"  Exemplo: {job_links[0]['href'][:80]}")
            
    else:
        print(f"❌ Erro HTTP {r.status_code}")
except Exception as e:
    print(f"❌ Erro: {e}")

# ── Teste 3: Gupy API ──────────────────────────────────────────

print("\n\n3️⃣  GUPY API - Testando endpoints")
print("-" * 60)

gupy_tests = [
    ("https://portal.api.gupy.io/api/v1/jobs", {"jobName": "logistica", "cityName": "São Paulo"}),
    ("https://portal.api.gupy.io/api/v1/jobs", {"companySlug": "latam"}),
]

for idx, (url, params) in enumerate(gupy_tests, 1):
    print(f"\nTeste {idx}:")
    print(f"  URL: {url}")
    print(f"  Params: {params}")
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            count = len(data.get("data", []))
            print(f"  ✓ Retornou {count} vagas")
            if count > 0:
                sample = data["data"][0]
                print(f"    Amostra: {sample.get('name', 'N/A')} @ {sample.get('companyName', 'N/A')}")
        else:
            print(f"  ❌ Status {r.status_code}")
    except Exception as e:
        print(f"  ❌ Erro: {e}")

print("\n" + "="*60)
print("✅ Diagnóstico concluído!")
print("="*60 + "\n")
