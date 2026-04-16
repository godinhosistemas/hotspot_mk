# 🚀 Hotspot Auth — Deploy no Coolify

Sistema de autenticação Hotspot MikroTik via número de celular.
Roda como container Docker no seu VPS Hostinger via Coolify.

---

## 📁 Estrutura do projeto

```
hotspot-auth/
├── Dockerfile              ← Build da imagem Python/Flask
├── docker-compose.yml      ← Stack para o Coolify
├── app.py                  ← Servidor Flask
├── requirements.txt        ← Dependências Python
├── .env.example            ← Modelo de variáveis de ambiente
├── .gitignore
└── templates/
    ├── login.html          ← Página de login (celular)
    ├── sucesso.html        ← Página pós-autenticação
    └── acessos.html        ← Painel de acessos registrados
```

---

## ☁️ Deploy no Coolify — Passo a Passo

### 1. Suba o projeto para um repositório Git

```bash
git init
git add .
git commit -m "hotspot-auth inicial"
git remote add origin https://github.com/SEU_USUARIO/hotspot-auth.git
git push -u origin main
```

> Pode usar GitHub, GitLab ou Gitea (inclusive self-hosted no próprio Coolify).

---

### 2. No painel do Coolify

1. Acesse seu Coolify → **New Resource**
2. Escolha **Docker Compose**
3. Selecione o servidor (seu VPS Hostinger)
4. Aponte para o repositório Git ou cole o `docker-compose.yml` diretamente

---

### 3. Configure as variáveis de ambiente

Na aba **Environment Variables** do Coolify, adicione:

| Variável           | Valor                          |
|--------------------|--------------------------------|
| `MIKROTIK_HOST`    | IP público do seu MikroTik     |
| `MIKROTIK_USER`    | `admin`                        |
| `MIKROTIK_PASSWORD`| senha do admin                 |
| `MIKROTIK_PORT`    | `8728`                         |
| `HOTSPOT_PROFILE`  | `perfil-padrao`                |
| `DEFAULT_REDIRECT` | `http://www.google.com`        |

---

### 4. Configure o domínio (opcional mas recomendado)

No Coolify, aba **Domains**:
- Adicione um domínio ou subdomínio (ex: `hotspot.seudominio.com.br`)
- O Coolify configura o Traefik + SSL (Let's Encrypt) automaticamente

Ou use direto pela porta: `http://IP_DO_VPS:5000`

---

### 5. Clique em Deploy ✅

O Coolify vai:
1. Clonar o repositório
2. Fazer o build da imagem Docker
3. Subir o container com Gunicorn
4. Monitorar via healthcheck `/healthz`

---

## ⚙️ Configuração no MikroTik

Após o deploy, execute no terminal do MikroTik:

### Habilitar API RouterOS
```
/ip service set api disabled=no port=8728
/ip service set api address=0.0.0.0/0
```

### Redirecionar a página de login do Hotspot para o Flask
```
/ip hotspot profile set hsprof-hotspot \
    login-page=http://IP_DO_VPS:5000/login
```

### Liberar o VPS no Walled Garden (antes da autenticação)
```
/ip hotspot walled-garden ip add \
    dst-address=IP_DO_VPS \
    action=accept \
    comment="Servidor Flask Hotspot Auth"
```

---

## 🔒 Segurança da API MikroTik

Para que o VPS consiga se comunicar com a API do MikroTik,
o roteador precisa estar acessível pelo IP público do VPS.

### Opção A — Porta 8728 aberta (mais simples)
```
/ip firewall filter add \
    chain=input \
    protocol=tcp \
    dst-port=8728 \
    src-address=IP_DO_VPS \
    action=accept \
    place-before=0 \
    comment="Liberar API para VPS Hotspot Auth"
```

### Opção B — VPN (mais seguro)
Configure uma VPN WireGuard entre o VPS e o MikroTik,
e use o IP interno da VPN como `MIKROTIK_HOST`.

---

## 📊 Acessando os logs

| URL                              | Descrição                     |
|----------------------------------|-------------------------------|
| `http://SEU_VPS:5000/acessos`    | Painel visual de acessos      |
| `http://SEU_VPS:5000/api/acessos`| JSON com últimos 50 acessos   |
| `http://SEU_VPS:5000/healthz`    | Status do container           |

### Ver o arquivo de log direto no servidor
```bash
# Via Docker
docker exec hotspot-auth cat /data/acessos.txt

# Via volume
docker run --rm -v hotspot_logs:/data alpine cat /data/acessos.txt
```

---

## 🔄 Fluxo completo de autenticação

```
[Cliente conecta no Wi-Fi]
         ↓
[Tenta abrir qualquer site]
         ↓
[MikroTik redireciona para:]
http://SEU_VPS:5000/login?ip=X.X.X.X&mac=XX:XX&dst=http://site.com
         ↓
[Cliente digita número de celular]
         ↓
[Flask valida → grava em /data/acessos.txt]
         ↓
[Flask cria usuário no MikroTik via API]
         ↓
[Redireciona para /login do MikroTik com user+pass]
         ↓
[MikroTik autentica → libera internet por 8h]
         ↓
[Cliente acessa o site normalmente] ✅
```

---

## 📝 Formato do acessos.txt

```
16/04/2026 14:32:01 | LOGIN    | Celular: 44999998888 | IP: 192.168.10.50
16/04/2026 15:10:44 | LOGIN    | Celular: 44988887777 | IP: 192.168.10.51
```
