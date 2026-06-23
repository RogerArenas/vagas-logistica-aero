# 🔧 Guia: Corrigindo Gupy e Catho com Selenium

## 📊 Diagnóstico Final

### ❌ Por que Gupy e Catho não funcionam

**Gupy:**
- ✓ Retorna HTTP 200
- ❌ Dados são carregados dinamicamente com JavaScript (Next.js)
- ❌ Requests simples só recebem o shell HTML vazio
- ✓ **Solução**: Usar Selenium ou Playwright

**Catho:**
- ❌ Retorna 404 em todas as URLs testadas
- ❌ Site pode estar bloqueando scrapers ou mudou a estrutura
- ❌ API pública não disponível
- ✓ **Solução**: Usar Selenium com detecção de bloqueio

---

## 🚀 Solução: Adicionar Selenium ao projeto

### Passo 1: Instalar dependências

```bash
pip install selenium
pip install webdriver-manager
```

### Passo 2: Baixar ChromeDriver (automático)

```bash
# webdriver-manager cuida disso automaticamente
```

### Passo 3: Implementar funções com Selenium

Veja `scraper_com_selenium.py` para exemplos completos.

---

## 📝 Exemplo 1: Gupy com Selenium

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def fetch_gupy_selenium(search_term: str = "logistica") -> list[dict]:
    """
    Busca vagas no Gupy usando Selenium
    (espera o JavaScript carregar os dados)
    """
    results = []
    
    # Configurar Chrome
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless")  # Modo invisível
    options.add_argument("user-agent=Mozilla/5.0")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        # Navegar para Gupy
        url = f"https://portal.gupy.io/jobs?search={search_term}&city=São Paulo"
        print(f"  Abrindo {url}...")
        driver.get(url)
        
        # Esperar os jobs carregarem (até 10 segundos)
        print("  Aguardando carregamento de vagas...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "job-card"))
        )
        
        # Extrair vagas
        job_elements = driver.find_elements(By.CLASS_NAME, "job-card")
        print(f"  ✓ {len(job_elements)} vagas encontradas")
        
        for job_el in job_elements[:20]:  # Limite de 20
            try:
                title = job_el.find_element(By.CLASS_NAME, "job-title").text
                company = job_el.find_element(By.CLASS_NAME, "company-name").text
                link = job_el.find_element(By.TAG_NAME, "a").get_attribute("href")
                
                results.append({
                    "id": f"gupy_{hash(link)}",
                    "title": title,
                    "company": company,
                    "url": link,
                    "source": "Gupy (Selenium)",
                })
            except:
                continue
                
    except Exception as e:
        print(f"  ❌ Erro: {e}")
    finally:
        driver.quit()
    
    return results
```

### Exemplo 2: Catho com Selenium

```python
def fetch_catho_selenium(search_term: str = "logistica") -> list[dict]:
    """
    Busca vagas no Catho usando Selenium
    """
    results = []
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("user-agent=Mozilla/5.0")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        # Tentar diferentes URLs
        urls = [
            f"https://www.catho.com.br/vagas/{search_term}/",
            f"https://www.catho.com.br/vagas?q={search_term}&city=sao-paulo",
        ]
        
        for url in urls:
            print(f"  Tentando {url[:40]}...")
            driver.get(url)
            
            # Verificar se está sendo bloqueado
            if "403" in driver.title or "Access Denied" in driver.page_source:
                print(f"  ⚠️  Página bloqueada por WAF")
                continue
            
            # Esperar vagas carregarem
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "job-item"))
                )
                
                job_elements = driver.find_elements(By.CLASS_NAME, "job-item")
                print(f"  ✓ {len(job_elements)} vagas encontradas")
                
                for job_el in job_elements[:20]:
                    try:
                        title = job_el.find_element(By.TAG_NAME, "h2").text
                        company_el = job_el.find_element(By.CLASS_NAME, "company")
                        link = job_el.find_element(By.TAG_NAME, "a").get_attribute("href")
                        
                        results.append({
                            "id": f"catho_{hash(link)}",
                            "title": title,
                            "company": company_el.text if company_el else "Empresa",
                            "url": link,
                            "source": "Catho (Selenium)",
                        })
                    except:
                        continue
                
                if results:
                    break
                    
            except Exception as e:
                print(f"  Timeout ou erro: {e}")
                continue
    
    finally:
        driver.quit()
    
    return results
```

---

## ⚙️ Integrando ao scraper.py

Adicione no `collect_all_jobs()`:

```python
# Ativar quando Selenium for instalado
# print("🌐 Buscando no Gupy (Selenium)…")
# gupy_jobs = fetch_gupy_selenium("logistica")
# for j in gupy_jobs:
#     if j["id"] not in seen:
#         seen.add(j["id"])
#         all_jobs.append(j)

# print("🌐 Buscando no Catho (Selenium)…")
# catho_jobs = fetch_catho_selenium("logistica")
# for j in catho_jobs:
#     if j["id"] not in seen:
#         seen.add(j["id"])
#         all_jobs.append(j)
```

---

## 📋 Checklist para implementar

- [ ] Instalar `pip install selenium webdriver-manager`
- [ ] Testar Gupy com Selenium
- [ ] Testar Catho com Selenium
- [ ] Integrar ao `scraper.py`
- [ ] Adicionar flag `--no-selenium` para usar sem
- [ ] Adicionar tratamento de timeout
- [ ] Adicionar retry logic
- [ ] Testar com GitHub Actions

---

## ⚠️ Considerações

### Prós do Selenium
✅ Funciona com JavaScript/conteúdo dinâmico  
✅ Pode aguardar elementos específicos  
✅ Mais próximo ao comportamento real do usuário  
✅ Pode lidar com bloqueios de WAF mais fácil  

### Contras do Selenium
❌ Mais lento que requests
❌ Requer mais memória
❌ Difícil de rodar em alguns ambientes (CI/CD)
❌ Pode quebrar se site mudar HTML

---

## 🛡️ Evitando bloqueios

```python
# 1. Usar User-Agent realista
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

# 2. Desabilitar detecção de Selenium
options.add_argument("--disable-blink-features=AutomationControlled")

# 3. Adicionar delays
import time
time.sleep(2)  # Entre requisições

# 4. Rodar em background (headless)
options.add_argument("--headless")

# 5. Usar proxy se necessário (premium)
# options.add_argument("--proxy-server=http://proxy:porta")
```

---

## 📊 Comparação: Status Atual vs. Com Selenium

| Fonte | Sem Selenium | Com Selenium |
|-------|-------------|-------------|
| **Vagas.com** | 124 vagas ✅ | 124 vagas ✅ |
| **Gupy** | 0 vagas ❌ | ~30-50 vagas (estimado) |
| **Catho** | 0 vagas ❌ | ~20-40 vagas (estimado) |
| **Total** | **124 vagas** | **~174-214 vagas** |

---

## 🚀 Próximos Passos

1. **Curto prazo**: Manter Vagas.com funcionando (124 vagas)
2. **Médio prazo**: Adicionar Selenium para Gupy e Catho
3. **Longo prazo**: Considerar LinkedIn API oficial

---

## 📚 Referências

- [Selenium Documentation](https://selenium-python.readthedocs.io/)
- [webdriver-manager](https://github.com/SergeyPirogov/webdriver-manager)
- [Playwright (Alternativa mais rápida)](https://playwright.dev/python/)

---

**Recomendação**: Use a solução atual (Vagas.com com 124 vagas) em produção, e implemente Selenium em desenvolvimento para futuras melhorias.
