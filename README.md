# ✈️ Radar de Vagas — Logística Aérea · São Paulo

> Aplicação estática que busca e centraliza vagas de **logística em companhias aéreas de São Paulo**. Atualiza automaticamente via **GitHub Actions** e envia alertas por **e-mail** e **WhatsApp**.

---

## 📸 O que você vai ter

- **Tela de consulta** estilo painel de embarque (departure board)
- **Busca em tempo real** na API pública da Gupy + Catho + Vagas.com
- **Filtros** por empresa, tipo de contrato e área
- **Botão de WhatsApp** para compartilhar vagas com 1 clique
- **Alerta automático** por e-mail e WhatsApp quando surgem vagas novas
- **Atualização diária** automática via GitHub Actions (de segunda a sexta)
- **Zero custo** — tudo roda no plano gratuito do GitHub

---

## 🚀 Passo a passo para subir no GitHub Pages

### 1. Criar o repositório

1. Acesse [github.com/new](https://github.com/new)
2. Nome sugerido: `vagas-logistica-aero`
3. Marque como **Public** (obrigatório para GitHub Pages gratuito)
4. Clique em **Create repository**

### 2. Fazer upload dos arquivos

```bash
# Clone o repositório vazio
git clone https://github.com/SEU_USUARIO/vagas-logistica-aero.git
cd vagas-logistica-aero

# Copie todos os arquivos deste projeto para a pasta
# (index.html, scraper.py, jobs.json, requirements.txt, .github/)

# Envie para o GitHub
git add .
git commit -m "🚀 inicial: Radar de Vagas"
git push origin main
```

### 3. Ativar o GitHub Pages

1. No repositório, vá em **Settings → Pages**
2. Em *Source*, selecione **Deploy from a branch**
3. Escolha a branch **main** e pasta **/ (root)**
4. Clique em **Save**

Após ~2 minutos, a URL estará disponível:
```
https://SEU_USUARIO.github.io/vagas-logistica-aero/
```

> 💡 **Atualize o link** dentro do `scraper.py` e do `update_jobs.yml` trocando `SEU_USUARIO` pelo seu usuário do GitHub.

---

## 🔔 Configurar alertas automáticos

Os alertas são enviados pelo GitHub Actions quando novas vagas aparecem.

### Alertas por E-mail (Gmail)

**1. Criar senha de app no Google**

> A sua senha normal não funciona. É necessário uma senha específica para apps.

1. Acesse: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Clique em **Selecionar app → Outro** → Digite "Radar de Vagas"
3. Clique em **Gerar** → Copie a senha de 16 caracteres

**2. Adicionar os Secrets no GitHub**

1. No repositório, vá em **Settings → Secrets and variables → Actions**
2. Clique em **New repository secret** e adicione:

| Nome do Secret | Valor |
|----------------|-------|
| `SMTP_USER`    | seu e-mail do Gmail (ex: `voce@gmail.com`) |
| `SMTP_PASS`    | a senha de app de 16 caracteres |
| `ALERT_EMAIL`  | e-mail que vai receber os alertas (pode ser o mesmo) |

---

### Alertas por WhatsApp (gratuito via CallMeBot)

**1. Ativar o CallMeBot no seu WhatsApp**

1. Salve o número **+34 644 59 78 18** na agenda
2. Envie a mensagem: `I allow callmebot to send me messages`
3. Você receberá uma resposta com a sua `apikey` (ex: `123456`)

> ⚠️ Pode demorar alguns minutos para a chave chegar.

**2. Adicionar os Secrets**

| Nome do Secret | Valor |
|----------------|-------|
| `ALERT_WPP`      | seu número com código do país, sem espaços (ex: `5511999999999`) |
| `CALLMEBOT_KEY`  | a chave que o bot enviou (ex: `123456`) |

---

## ⚙️ Como funciona a atualização automática

```
┌─────────────────────────────────────────────────────┐
│              GitHub Actions (gratuito)               │
│                                                     │
│  Segunda a Sexta, 07:00 e 12:00 (horário Brasília)  │
│                      ↓                              │
│           python scraper.py --notify                │
│                      ↓                              │
│   Gupy API + Catho + Vagas.com → jobs.json          │
│                      ↓                              │
│    Se tiver vagas novas → E-mail + WhatsApp         │
│                      ↓                              │
│       git commit + push → GitHub Pages atualiza     │
└─────────────────────────────────────────────────────┘
```

### Rodar o scraper manualmente

Na aba **Actions** do repositório, selecione o workflow
**"✈️ Atualizar Vagas de Logística"** e clique em **Run workflow**.

---

## 🏢 Empresas monitoradas

| Empresa | Categoria |
|---------|-----------|
| 🔵 LATAM Airlines | Companhia aérea |
| 🟠 GOL Linhas Aéreas | Companhia aérea |
| 🔷 Azul Linhas Aéreas | Companhia aérea |
| 🟢 Voepass Linhas Aéreas | Companhia aérea regional |
| ⚪ Swissport Brasil | Handling / Solo |
| 🟤 Ogden Serviços | Handling / Solo |
| 🏛️ Infraero | Aeroportos |
| 🏢 GRU Airport | Aeroporto de Guarulhos |
| 🟡 DHL Express | Carga / Logística |
| 🟣 FedEx Brasil | Carga / Logística |
| 🟫 UPS Brasil | Carga / Logística |

Para **adicionar mais empresas**, edite a lista `COMPANY_SLUGS` no `scraper.py`.

---

## 🗂️ Estrutura do projeto

```
vagas-logistica-aero/
├── index.html               ← Interface web (GitHub Pages)
├── jobs.json                ← Dados das vagas (atualizado automaticamente)
├── scraper.py               ← Script de coleta de vagas
├── requirements.txt         ← Dependências Python
├── README.md                ← Este arquivo
└── .github/
    └── workflows/
        └── update_jobs.yml  ← Workflow de automação
```

---

## 🛠️ Rodar localmente (opcional)

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar o scraper (sem alertas)
python scraper.py

# Rodar com alertas (requer variáveis de ambiente configuradas)
SMTP_USER=voce@gmail.com SMTP_PASS=senha ALERT_EMAIL=dest@email.com \
python scraper.py --notify

# Testar sem salvar
python scraper.py --dry-run

# Visualizar o site localmente
python -m http.server 8080
# Abrir: http://localhost:8080
```

---

## ❓ Dúvidas frequentes

**O site não abre as vagas em tempo real?**

Sim! O `index.html` busca vagas diretamente na API pública da Gupy via JavaScript. O `jobs.json` serve como cache e é atualizado 2x por dia pelo Actions.

**Posso adicionar outras fontes de vagas?**

Sim. Edite as funções `fetch_catho()` e `fetch_vagas_com()` no `scraper.py` ou adicione novas funções seguindo o mesmo padrão.

**Como compartilhar a vaga com minha namorada?**

Cada cartão de vaga tem um botão do WhatsApp 📱 que abre o app com a mensagem já formatada. Ou clique em "Compartilhar" no topo para enviar as 5 melhores vagas de uma vez.

**O repositório precisa ser público?**

Sim, para usar o GitHub Pages gratuitamente o repositório precisa ser público.

---

## 📄 Licença

MIT — use, modifique e compartilhe à vontade.

---

*Feito com 💛 para facilitar a busca de vagas em logística aérea em São Paulo.*
