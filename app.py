"""
=============================================================
SERVIDOR DE AUTENTICAÇÃO HOTSPOT - FLASK
=============================================================
Todas as configurações são lidas via variáveis de ambiente
(.env ou docker-compose environment).
=============================================================
"""

from flask import Flask, request, render_template, redirect, jsonify
import routeros_api
import re
import os
from datetime import datetime

app = Flask(__name__)

# -------------------------------------------------------------
# CONFIGURAÇÕES VIA VARIÁVEIS DE AMBIENTE
# -------------------------------------------------------------
MIKROTIK_HOST     = os.environ.get("MIKROTIK_HOST",     "192.168.10.1")
MIKROTIK_USER     = os.environ.get("MIKROTIK_USER",     "admin")
MIKROTIK_PASSWORD = os.environ.get("MIKROTIK_PASSWORD", "")
MIKROTIK_PORT     = int(os.environ.get("MIKROTIK_PORT", "8728"))
HOTSPOT_PROFILE   = os.environ.get("HOTSPOT_PROFILE",   "perfil-padrao")
DEFAULT_REDIRECT  = os.environ.get("DEFAULT_REDIRECT",  "http://www.google.com")
LOG_FILE          = os.environ.get("LOG_FILE",          "/data/acessos.txt")
# -------------------------------------------------------------


def formatar_celular(numero: str):
    """Remove tudo que não for dígito e valida formato brasileiro (11 dígitos)."""
    apenas_digitos = re.sub(r'\D', '', numero)
    if len(apenas_digitos) == 11 and apenas_digitos[:2].isdigit():
        return apenas_digitos
    return None


def registrar_acesso(celular: str, ip_cliente: str, acao: str = "LOGIN"):
    """Salva o acesso no arquivo de log TXT persistente."""
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    linha = f"{agora} | {acao:<8} | Celular: {celular} | IP: {ip_cliente}\n"
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(linha)
    print(f"[LOG] {linha.strip()}", flush=True)


def autenticar_via_mikrotik(celular: str, ip_cliente: str, mac_cliente: str = "") -> dict:
    """
    Cria o usuário no Hotspot MikroTik (se não existir) e tenta autenticá-lo via API.
    """
    try:
        connection = routeros_api.RouterOsApiPool(
            MIKROTIK_HOST,
            username=MIKROTIK_USER,
            password=MIKROTIK_PASSWORD,
            port=MIKROTIK_PORT,
            plaintext_login=True
        )
        api = connection.get_api()
        hotspot_users = api.get_resource('/ip/hotspot/user')

        # Cria usuário se não existir
        usuarios = hotspot_users.get(name=celular)
        if not usuarios:
            hotspot_users.add(
                name=celular,
                password=celular,
                profile=HOTSPOT_PROFILE,
                comment=f"Auto - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )

        # Tenta login via API binária do Hotspot
        login_resource = api.get_binary_resource('/ip/hotspot/')
        login_resource.call('login', {
            'ip':       ip_cliente.encode(),
            'mac':      mac_cliente.encode() if mac_cliente else b'',
            'user':     celular.encode(),
            'password': celular.encode(),
        })

        connection.disconnect()
        return {"sucesso": True}

    except Exception as e:
        print(f"[ERRO] API MikroTik: {e}", flush=True)
        return {"sucesso": False, "mensagem": str(e)}


# =============================================================
# ROTAS
# =============================================================

@app.route("/", methods=["GET"])
@app.route("/login", methods=["GET"])
def pagina_login():
    dst  = request.args.get("dst", DEFAULT_REDIRECT)
    ip   = request.args.get("ip",  request.remote_addr)
    mac  = request.args.get("mac", "")
    erro = request.args.get("erro", "")
    return render_template("login.html", dst=dst, ip=ip, mac=mac, erro=erro)


@app.route("/autenticar", methods=["POST"])
def autenticar():
    celular_raw = request.form.get("celular", "").strip()
    dst         = request.form.get("dst", DEFAULT_REDIRECT)
    ip_cliente  = request.form.get("ip",  request.remote_addr)
    mac_cliente = request.form.get("mac", "")

    celular = formatar_celular(celular_raw)

    if not celular:
        return redirect(
            f"/login?dst={dst}&ip={ip_cliente}&mac={mac_cliente}"
            f"&erro=Número+inválido.+Informe+DDD+%2B+9+dígitos."
        )

    registrar_acesso(celular, ip_cliente)

    resultado = autenticar_via_mikrotik(celular, ip_cliente, mac_cliente)

    if resultado["sucesso"]:
        # Login direto via redirect para o endpoint do MikroTik
        return redirect(
            f"http://{MIKROTIK_HOST}/login"
            f"?dst={dst}&username={celular}&password={celular}"
        )
    else:
        # Fallback: página de sucesso com auto-submit form para o MikroTik
        return render_template(
            "sucesso.html",
            celular=celular,
            dst=dst,
            mikrotik_host=MIKROTIK_HOST
        )


@app.route("/acessos", methods=["GET"])
def ver_acessos():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            linhas = f.readlines()
        registros = [l.strip() for l in reversed(linhas[-100:])]
        total = len(linhas)
    except FileNotFoundError:
        registros = []
        total = 0
    return render_template("acessos.html", registros=registros, total=total)


@app.route("/api/acessos", methods=["GET"])
def api_acessos():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            linhas = f.readlines()
        return jsonify({"total": len(linhas), "registros": [l.strip() for l in linhas[-50:]]})
    except FileNotFoundError:
        return jsonify({"total": 0, "registros": []})


@app.route("/healthz", methods=["GET"])
def health():
    """Endpoint de healthcheck para o Docker/Coolify."""
    return jsonify({"status": "ok", "mikrotik": MIKROTIK_HOST}), 200


if __name__ == "__main__":
    print("=" * 55, flush=True)
    print("  HOTSPOT AUTH  |  Flask + RouterOS API", flush=True)
    print(f"  MikroTik : {MIKROTIK_HOST}:{MIKROTIK_PORT}", flush=True)
    print(f"  Log      : {LOG_FILE}", flush=True)
    print("=" * 55, flush=True)
    app.run(host="0.0.0.0", port=5000, debug=False)
