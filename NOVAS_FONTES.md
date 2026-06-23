# 📌 Guia de Novas Fontes para o Scraper

## Fontes Recomendadas para Adicionar

### 1. **Indeed Brasil** 🎯 (Muito promissor)
```python
url = "https://br.indeed.com/jobs?q=logistica+aerea&l=sao+paulo"
```
- Vantagens: Muitas vagas, boa cobertura
- Desafio: Pode bloquear scrapers simples
- Solução: Usar User-Agent customizado e delays

### 2. **LinkedIn** 💼 (Difícil, requer login)
```python
# Alternativa: usar linkedin-jobs-scraper library
# Ou usar a API oficial (requer credenciais)
```
- Vantagens: Vagas de qualidade, empresa verificada
- Desafio: Requer autenticação
- Solução: API oficial com token ou biblioteca de scraping

### 3. **Vagas.com Alternativa** 🔄 (Já funciona)
Adicionar mais termos de busca:
```python
ADDITIONAL_SEARCH_TERMS = [
    "ground-handling",
    "air-cargo",
    "airport-operations",
    "supply-chain",
]
```

### 4. **GitHub Jobs** (Descontinuado) ⚠️
- Status: Não recomendado (serviço foi descontinuado)

### 5. **Catho API Pública** (Alternativa)
Se conseguir encontrar o endpoint correto:
```python
# Investigar: https://api.catho.com.br/...
# Ou: https://mobile-api.catho.com.br/...
```

---

## 🔧 Implementação de Novas Fontes

### Template para nova fonte:

```python
def fetch_nova_fonte(busca: str = "logistica") -> list[dict]:
    """
    Busca vagas em [NOME DA FONTE]
    """
    results = []
    url = f"https://exemplo.com/vagas?q={busca}&city=sao-paulo"
    
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        
        # [INSERIR SELETORES ESPECÍFICOS DA FONTE]
        for card in soup.select("selector-correto"):
            title = card.select_one("...").get_text(strip=True)
            company = card.select_one("...").get_text(strip=True)
            href = card.select_one("a")["href"]
            full_url = href if href.startswith("http") else f"https://exemplo.com{href}"
            
            results.append({
                "id":          f"source_{hash(full_url)}",
                "title":       title,
                "company":     company,
                "emoji":       airline_emoji(company),
                "location":    "São Paulo, SP",
                "type":        "CLT",
                "area":        "Logística",
                "date_posted": today(),
                "url":         full_url,
                "source":      "NovaBusca",
                "is_new":      True,
            })
    except Exception as e:
        print(f"  [WARN] Nova Fonte: {e}")
    
    return results
```

---

## 🔬 Como Testar Seletores CSS

1. Abrir a página no navegador
2. Pressionar F12 (Developer Tools)
3. Inspecionar um elemento (Ctrl+Shift+C)
4. Testar no console JavaScript:

```javascript
// Para encontrar o seletor certo
document.querySelectorAll(".job-item").length
document.querySelectorAll("[data-testid='job-card']").length

// Ou use o elemento inspecionado:
element.textContent  // Pega o texto
element.href         // Pega o link
```

---

## 📊 Checklist para Adicionar Nova Fonte

- [ ] URL da busca funciona no navegador
- [ ] Status HTTP é 200
- [ ] Seletores CSS identificados e testados
- [ ] Função criada e testada
- [ ] Adicionada em `collect_all_jobs()`
- [ ] Delay apropriado adicionado (1-2 segundos)
- [ ] Tratamento de erro implementado
- [ ] User-Agent customizado se necessário
- [ ] Rotação de IPs considerada (se bloqueado)

---

## 🛡️ Evitando Bloqueios

```python
# 1. User-Agent variado
HEADERS = {
    "User-Agent": random.choice([
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15)",
        "Mozilla/5.0 (X11; Linux x86_64)",
    ]),
    "Accept-Language": "pt-BR,pt;q=0.9",
}

# 2. Delays entre requisições
time.sleep(random.uniform(1, 3))

# 3. Tratamento de status 429 (Too Many Requests)
if r.status_code == 429:
    time.sleep(60)  # Esperar 1 minuto
    r = requests.get(url, headers=HEADERS, timeout=15)
```

---

## 📚 Bibliotecas Úteis para Web Scraping

```bash
# Já instalados
pip install requests beautifulsoup4 lxml

# Para sites dinâmicos (JavaScript)
pip install selenium
pip install playwright

# Para parsing avançado
pip install scrapy
pip install parsel

# Para lidar com JavaScript
pip install pyppeteer
```

---

## 🎯 Prioridade de Implementação

1. **Emergência**: Reativar Gupy (estava funcionando antes)
2. **Alta**: Testar novamente Catho com Selenium
3. **Média**: Adicionar Indeed Brasil
4. **Baixa**: Integrar LinkedIn (complexo)

---

**Última atualização**: 23/06/2026
