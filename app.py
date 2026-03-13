# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, render_template_string
import psycopg2
import os
import requests
import base64

app = Flask(__name__)

HF_TOKEN = os.environ.get("HF_TOKEN", "hf_CBTMZRRrBddpslPMOyUNGcRbyhNnSQUcABR")
HF_URL = "https://router.huggingface.co/models/google/vit-base-patch16-224"

def classify_image(image_bytes):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    response = requests.post(HF_URL, headers=headers, data=image_bytes)
    return response.json()

def get_db():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "db"),
        database=os.environ.get("DB_NAME", "imagenes"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", "postgres123")
    )

def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS clasificaciones (
                id SERIAL PRIMARY KEY,
                nombre_archivo TEXT,
                resultado TEXT,
                confianza FLOAT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error DB: {e}")

HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Clasificador de Imágenes IA</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: Segoe UI, sans-serif; background:#13111e; min-height:100vh; }
.banner { background:linear-gradient(90deg,#7c3aed,#2563eb,#0891b2,#059669); padding:18px 28px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px; }
.banner-left { display:flex; flex-direction:column; gap:2px; }
.banner-course { font-size:11px; color:rgba(255,255,255,0.7); letter-spacing:1px; text-transform:uppercase; }
.banner-title { font-size:16px; font-weight:600; color:#fff; }
.banner-names { display:flex; gap:8px; flex-wrap:wrap; }
.name-badge { background:rgba(255,255,255,0.15); border:0.5px solid rgba(255,255,255,0.25); border-radius:20px; padding:4px 12px; font-size:11px; color:#fff; }
.body { padding:28px 20px; }
.header { text-align:center; margin-bottom:28px; }
.sub { font-size:13px; color:#6b6a8a; }
.card { background:#1c1a2e; border:0.5px solid #2e2b4a; border-radius:16px; padding:24px; margin-bottom:16px; max-width:700px; margin-left:auto; margin-right:auto; }
.drop { border:1.5px dashed #3d3a5e; border-radius:12px; padding:48px 24px; text-align:center; cursor:pointer; transition:border-color 0.2s; }
.drop:hover { border-color:#7c6fc7; }
.drop-icon { width:48px; height:48px; background:#27243d; border-radius:12px; display:flex; align-items:center; justify-content:center; margin:0 auto 12px; }
.drop-icon svg { width:24px; height:24px; stroke:#7c6fc7; fill:none; stroke-width:1.5; }
.drop-title { font-size:15px; color:#c4b5fd; font-weight:500; margin-bottom:4px; }
.drop-hint { font-size:12px; color:#6b6a8a; }
#preview { max-width:100%; max-height:280px; border-radius:12px; margin-top:16px; display:none; object-fit:contain; }
.btn { width:100%; padding:13px; background:#5b4fcf; border:none; border-radius:10px; color:#fff; font-size:14px; font-weight:500; cursor:pointer; margin-top:16px; display:none; }
.btn:hover { background:#4c42b8; }
.result-card { background:#1c1a2e; border:0.5px solid #2e2b4a; border-radius:16px; padding:24px; max-width:700px; margin:0 auto 16px; display:none; }
.res-label { font-size:22px; font-weight:500; color:#e2dff8; margin-bottom:4px; text-transform:capitalize; }
.res-conf { font-size:13px; color:#6b6a8a; margin-bottom:20px; }
.bar-row { display:flex; align-items:center; gap:10px; margin-bottom:10px; }
.bar-label { font-size:12px; color:#9491b4; width:150px; text-transform:capitalize; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.bar-track { flex:1; height:6px; background:#27243d; border-radius:4px; overflow:hidden; }
.bar-fill { height:100%; border-radius:4px; }
.bar-pct { font-size:12px; color:#7c6fc7; min-width:40px; text-align:right; }
.badge { display:inline-block; background:#27243d; color:#7c6fc7; font-size:11px; padding:3px 10px; border-radius:20px; }
.hist-title { font-size:13px; color:#6b6a8a; margin-bottom:14px; letter-spacing:0.5px; text-transform:uppercase; }
.hist-row { display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:0.5px solid #2e2b4a; }
.hist-row:last-child { border-bottom:none; }
.hist-name { font-size:13px; color:#c4b5fd; text-transform:capitalize; }
.hist-meta { font-size:12px; color:#6b6a8a; }
.loading { text-align:center; color:#6b6a8a; padding:16px; display:none; }
.spinner { display:inline-block; width:28px; height:28px; border:2px solid #27243d; border-top-color:#7c6fc7; border-radius:50%; animation:spin 0.8s linear infinite; }
@keyframes spin { to { transform:rotate(360deg); } }
</style>
</head>
<body>
<div class="banner">
  <div class="banner-left">
    <span class="banner-course">Computación en la Nube — Práctica 4</span>
    <span class="banner-title">Entorno Multi-Container en AWS</span>
  </div>
  <div class="banner-names">
    <span class="name-badge">Daniel Fernando Mejia</span>
    <span class="name-badge">Ruben Dario Salcedo</span>
    <span class="name-badge">Juan Espitia</span>
  </div>
</div>
<div class="body">
  <div class="header">
    <div class="sub">Clasificador de imágenes con inteligencia artificial</div>
  </div>
  <div class="card">
    <div class="drop" onclick="document.getElementById('fileInput').click()">
      <input type="file" id="fileInput" accept="image/*" style="display:none" onchange="previewImage(event)">
      <div class="drop-icon">
        <svg viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
      </div>
      <div class="drop-title">Arrastra tu imagen aquí</div>
      <div class="drop-hint">o haz clic para seleccionar — JPG, PNG, WEBP</div>
    </div>
    <img id="preview" src="" alt="preview">
    <div class="loading" id="loading"><div class="spinner"></div><p style="margin-top:10px;font-size:13px;">Analizando imagen...</p></div>
    <button class="btn" id="btnAnalizar" onclick="clasificar()">Clasificar imagen</button>
  </div>
  <div class="result-card" id="resultCard">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
      <div>
        <div class="res-label" id="resLabel"></div>
        <div class="res-conf" id="resConf"></div>
      </div>
      <div style="margin-left:auto;"><span class="badge">Top resultado</span></div>
    </div>
    <div id="barras"></div>
  </div>
  <div class="card">
    <div class="hist-title">Historial de clasificaciones</div>
    <div id="historial"><p style="color:#6b6a8a;font-size:13px;">Sin registros aún.</p></div>
  </div>
</div>
<script>
let archivo = null;
function previewImage(e) {
  const file = e.target.files[0];
  if (!file) return;
  archivo = file;
  const reader = new FileReader();
  reader.onload = ev => {
    const p = document.getElementById("preview");
    p.src = ev.target.result;
    p.style.display = "block";
    document.getElementById("btnAnalizar").style.display = "block";
    document.getElementById("resultCard").style.display = "none";
  };
  reader.readAsDataURL(file);
}
async function clasificar() {
  if (!archivo) return;
  document.getElementById("loading").style.display = "block";
  document.getElementById("btnAnalizar").style.display = "none";
  const fd = new FormData();
  fd.append("imagen", archivo);
  const res = await fetch("/clasificar", { method:"POST", body:fd });
  const data = await res.json();
  document.getElementById("loading").style.display = "none";
  document.getElementById("btnAnalizar").style.display = "block";
  if (data.error) {
    alert("Error: " + data.error);
    return;
  }
  document.getElementById("resultCard").style.display = "block";
  document.getElementById("resLabel").textContent = data.resultado;
  document.getElementById("resConf").textContent = "Confianza: " + (data.confianza*100).toFixed(1) + "%";
  let html = "";
  data.top5.forEach((item, i) => {
    const color = i === 0 ? "#5b4fcf" : "#3d3a5e";
    html += '<div class="bar-row"><span class="bar-label">' + item.label + '</span><div class="bar-track"><div class="bar-fill" style="width:' + (item.score*100).toFixed(1) + '%;background:' + color + ';"></div></div><span class="bar-pct">' + (item.score*100).toFixed(1) + '%</span></div>';
  });
  document.getElementById("barras").innerHTML = html;
  cargarHistorial();
}
async function cargarHistorial() {
  const res = await fetch("/historial");
  const data = await res.json();
  if (!data.length) return;
  let html = "";
  data.forEach(r => {
    html += '<div class="hist-row"><span class="hist-name">' + r.resultado + '</span><span class="badge">' + (r.confianza*100).toFixed(1) + '%</span><span class="hist-meta">' + r.fecha + '</span></div>';
  });
  document.getElementById("historial").innerHTML = html;
}
cargarHistorial();
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/clasificar", methods=["POST"])
def clasificar():
    file = request.files.get("imagen")
    if not file:
        return jsonify({"error": "No se recibió imagen"}), 400
    image_bytes = file.read()
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    response = requests.post(HF_URL, headers=headers, data=image_bytes)
    if response.status_code != 200:
        return jsonify({"error": "Error al clasificar imagen"}), 500
    results = response.json()
    if isinstance(results, list) and len(results) > 0:
        top = results[0]
        resultado = top["label"]
        confianza = float(top["score"])
        top5 = [{"label": r["label"], "score": float(r["score"])} for r in results[:5]]
    else:
        return jsonify({"error": "Respuesta inesperada del modelo"}), 500
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO clasificaciones (nombre_archivo, resultado, confianza) VALUES (%s, %s, %s)",
                    (file.filename, resultado, confianza))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error DB: {e}")
    return jsonify({"resultado": resultado, "confianza": confianza, "top5": top5})

@app.route("/historial")
def historial():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT resultado, confianza, fecha FROM clasificaciones ORDER BY fecha DESC LIMIT 10")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([{"resultado": r[0], "confianza": r[1], "fecha": str(r[2])} for r in rows])
    except:
        return jsonify([])

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8000)

