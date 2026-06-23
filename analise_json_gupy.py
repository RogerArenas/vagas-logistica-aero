"""
Análise profunda do JSON do Gupy para extrair a estrutura correta
"""

import requests
from bs4 import BeautifulSoup
import json
import pprint

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

print("\n" + "="*80)
print("🔍 Análise Profunda do JSON do Gupy")
print("="*80 + "\n")

url = "https://portal.gupy.io/jobs"
params = {
    "search": "logistica",
    "city": "São Paulo"
}

try:
    r = requests.get(url, params=params, headers=HEADERS, timeout=15)
    print(f"Status: {r.status_code}\n")
    
    soup = BeautifulSoup(r.text, "html.parser")
    scripts = soup.find_all("script", type="application/json")
    
    print(f"Scripts JSON encontrados: {len(scripts)}\n")
    
    for idx, script in enumerate(scripts):
        try:
            data = json.loads(script.string)
            print(f"\n{'='*80}")
            print(f"Script {idx} - Estrutura completa:")
            print(f"{'='*80}")
            
            # Mostrar keys principais
            print(f"\nKeys principais: {list(data.keys())}")
            
            # Explorar cada nível
            if "props" in data:
                print(f"\ndata['props'] keys: {list(data['props'].keys())}")
                
                if "pageProps" in data["props"]:
                    print(f"data['props']['pageProps'] keys: {list(data['props']['pageProps'].keys())}")
                    pageProps = data["props"]["pageProps"]
                    
                    # Procurar por jobs em diferentes nomes
                    for key in pageProps:
                        value = pageProps[key]
                        if isinstance(value, list):
                            print(f"  Lista '{key}': {len(value)} elementos")
                            if len(value) > 0 and isinstance(value[0], dict):
                                print(f"    Primeiro elemento keys: {list(value[0].keys())[:10]}")
                        elif isinstance(value, dict):
                            print(f"  Dict '{key}': {list(value.keys())[:5]}...")
            
            # Procurar por arrays que pareçam ter vagas
            def find_job_arrays(obj, path=""):
                if isinstance(obj, list):
                    if len(obj) > 0 and isinstance(obj[0], dict):
                        keys = list(obj[0].keys())
                        # Procurar por chaves que sugerem vaga
                        if any(k in keys for k in ["name", "title", "jobTitle", "position", "job"]):
                            print(f"\n  Possível array de vagas em '{path}':")
                            print(f"    Tamanho: {len(obj)}")
                            print(f"    Keys: {keys[:15]}")
                            return True
                elif isinstance(obj, dict):
                    for k, v in obj.items():
                        if find_job_arrays(v, f"{path}.{k}" if path else k):
                            return True
                return False
            
            print(f"\nProcurando por possíveis arrays de vagas:")
            find_job_arrays(data)
            
        except json.JSONDecodeError as e:
            print(f"Script {idx}: JSON inválido — {e}")
    
    # Também procurar por atributos data
    print(f"\n\n{'='*80}")
    print("Procurando por atributos data-* com informações de vagas")
    print(f"{'='*80}\n")
    
    elements = soup.find_all(True, {"data-*": True})
    print(f"Elementos com data-*: {len(elements)}")
    
    # Procurar especificamente por job listings
    print("\nProcurando por padrões HTML de jobs:")
    
    # Procurar por divs que pareçam ser job cards
    job_patterns = [
        ("div", {"data-testid": lambda x: x and "job" in x.lower() if x else False}),
        ("article", {}),
        ("div", {"class": lambda x: x and "job" in x.lower() if x else False}),
    ]
    
    for tag, attrs in job_patterns:
        elements = soup.find_all(tag, attrs)
        if elements:
            print(f"  {tag} {attrs}: {len(elements)} elementos")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
