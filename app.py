import os
from pathlib import Path
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from flask import Flask, render_template, render_template_string, request, jsonify
import requests

# Intenta cargar .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = Flask(__name__, template_folder=str(TEMPLATES_DIR), static_folder=str(STATIC_DIR))

FUNCTION_URL = (os.environ.get("FUNCTION_URL") or "").strip()
TIMEOUT_SEC = 10

def build_url_with_name(base_url: str, name: str) -> str:
    parts = list(urlparse(base_url))
    query = dict(parse_qsl(parts[4], keep_blank_values=True))
    query["name"] = name
    parts[4] = urlencode(query)
    return urlunparse(parts)

@app.before_request
def _log_req():
    app.logger.info("➡ %s %s", request.method, request.path)

@app.get("/health")
def health():
    return {"status": "ok", "fn_configured": bool(FUNCTION_URL), "templates_dir": str(TEMPLATES_DIR)}

@app.get("/")
def index():
    try:
        if not (TEMPLATES_DIR / "index.html").exists():
            # Fallback visible para evitar página en blanco
            return render_template_string("""
            <!doctype html><meta charset="utf-8">
            <h1>Plantilla no encontrada</h1>
            <p>Crea <code>templates/index.html</code> al lado de <code>app.py</code>.</p>
            <p><b>FUNCTION_URL cargada:</b> {{ ok }}</p>
            <p>Abre <a href="/health">/health</a> para diagnosticar.</p>
            """, ok=bool(FUNCTION_URL))
        return render_template("index.html", fn_configured=bool(FUNCTION_URL))
    except Exception as e:
        app.logger.exception("Error renderizando index")
        return f"<pre>Error renderizando index: {e}</pre>", 500

@app.post("/api/submit")
def submit():
    if not FUNCTION_URL:
        return jsonify(ok=False, error="No se ha configurado FUNCTION_URL"), 500

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify(ok=False, error="El campo 'name' está vacío."), 400

    try:
        url = build_url_with_name(FUNCTION_URL, name)
        resp = requests.get(url, timeout=TIMEOUT_SEC)
        resp.raise_for_status()
        return jsonify(ok=True, result=resp.text)
    except requests.Timeout:
        return jsonify(ok=False, error="Tiempo de espera agotado llamando a Azure Function."), 504
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else 502
        body = e.response.text if e.response is not None else str(e)
        return jsonify(ok=False, error=f"Error HTTP {status}: {body}"), status
    except Exception as e:
        app.logger.exception("Fallo en submit")
        return jsonify(ok=False, error=f"Error inesperado: {e}"), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.logger.info("Iniciando en http://127.0.0.1:%s", port)
    app.logger.info("Templates dir: %s", TEMPLATES_DIR)
    app.logger.info("FUNCTION_URL cargada: %s", bool(FUNCTION_URL))
    app.run(host="0.0.0.0", port=port, debug=True)
