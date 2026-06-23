"""
Análise detalhada da estrutura HTML do Vagas.com
"""

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
}

print("\n" + "="*70)
print("📊 ANÁLISE DETALHADA: Vagas.com - Estrutura HTML")
print("="*70 + "\n")

url = "https://www.vagas.com.br/vagas-de-logistica-aerea-em-sao-paulo-sp"

try:
    r = requests.get(url, headers=HEADERS, timeout=15)
    print(f"Status HTTP: {r.status_code}\n")
    
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Procurar por tags li.vaga
        vagas = soup.select("li.vaga")
        print(f"✓ Encontradas {len(vagas)} vagas com seletor 'li.vaga'\n")
        
        if len(vagas) > 0:
            vaga = vagas[0]
            print("Estrutura do primeiro elemento 'li.vaga':")
            print("-" * 70)
            print(vaga.prettify()[:1000])
            print("\n...\n")
            
            # Procurar por links dentro da vaga
            print("Links dentro da vaga:")
            links = vaga.find_all("a", href=True)
            for i, link in enumerate(links[:5], 1):
                href = link.get("href", "")
                text = link.get_text(strip=True)[:50]
                print(f"  {i}. href: {href}")
                print(f"     text: {text}")
            
            # Procurar por títulos
            print("\nProcurando por títulos:")
            title_selectors = [
                ("h2", "h2 tag"),
                ("h3", "h3 tag"),
                (".cargo", ".cargo class"),
                ("[data-testid='job-title']", "data-testid job-title"),
                ("a.titulo", "a.titulo"),
            ]
            
            for selector, desc in title_selectors:
                elem = vaga.select_one(selector)
                if elem:
                    print(f"  ✓ {desc}: {elem.get_text(strip=True)[:60]}")
            
            # Procurar por empresa
            print("\nProcurando por empresa:")
            company_selectors = [
                (".empresa", ".empresa class"),
                (".company", ".company class"),
                (".emprVaga", ".emprVaga class"),
                ("strong", "strong tag"),
            ]
            
            for selector, desc in company_selectors:
                elem = vaga.select_one(selector)
                if elem:
                    print(f"  ✓ {desc}: {elem.get_text(strip=True)[:60]}")
                    
except Exception as e:
    print(f"❌ Erro: {e}")

# Também testar Gupy
print("\n\n" + "="*70)
print("🔍 Testando endpoints alternativos do Gupy")
print("="*70 + "\n")

endpoints = [
    "https://api.gupy.io/api/v1/jobs",
    "https://gupy.io/api/v1/jobs",
    "https://portal.gupy.io/api/v1/jobs",
]

for endpoint in endpoints:
    try:
        r = requests.get(endpoint, params={"jobName": "logistica"}, timeout=10)
        print(f"URL: {endpoint}")
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"✓ Retornou dados!")
        print()
    except Exception as e:
        print(f"URL: {endpoint}")
        print(f"❌ Erro: {type(e).__name__}")
        print()

print("="*70)
