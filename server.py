#!/usr/bin/env python3
"""ResQ AI backend: static hosting + report API + responder dashboard. Python 3 standard library only."""
import base64, json, os, re, sqlite3, urllib.request
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(HERE, "public")
DB = os.path.join(HERE, "resq.db")
MAX_BODY = 12 * 1024 * 1024
PROMPT = ('You are helping a bystander at an accident scene. Look at the photo and answer ONLY with JSON: '
 '{"summary":"one or two plain sentences about what is visible","hazards":["up to 4 short items"],'
 '"protocol":"one of scene,cpr,bleed,spine,burn,bone,choke,seiz,none","note":"one short caution"}. '
 'Describe only what you can see. Do not diagnose and never say anyone is fine or safe. If unclear, say so and use "scene".')

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    with db() as c:
        c.execute("""create table if not exists reports(
            id integer primary key autoincrement, created text, lat real, lon real, acc real,
            note text, status text default 'new', photo blob, mime text)""")

def ai_check(data_url):
    fail = lambda m: {"summary": m, "hazards": [], "protocol": "scene", "note": "Call 112 for anything serious."}
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return fail("AI photo check is not configured on the server. Set ANTHROPIC_API_KEY and restart.")
    m = re.match(r"data:(image/[\w+.-]+);base64,(.+)", data_url or "", re.S)
    if not m:
        return fail("No valid photo received.")
    body = {"model": os.environ.get("RESQ_MODEL", "claude-sonnet-5-5"), "max_tokens": 400, "messages": [{"role": "user", "content": [
        {"type": "image", "source": {"type": "base64", "media_type": m.group(1), "data": m.group(2)}},
        {"type": "text", "text": PROMPT}]}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", json.dumps(body).encode(),
        {"content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"})
    try:
        out = json.load(urllib.request.urlopen(req, timeout=40))
        text = re.sub(r"```(?:json)?", "", out["content"][0]["text"]).strip()
        return json.loads(text)
    except Exception:
        return fail("The photo check failed. Choose the situation manually and call 112 if it is serious.")

class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=PUBLIC, **k)

    def send_json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            raise ValueError("too large")
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/api/health":
            return self.send_json({"ok": True})
        if p == "/api/reports":
            with db() as c:
                rows = c.execute("select id,created,lat,lon,acc,note,status,photo is not null as has_photo from reports order by id desc limit 200").fetchall()
            return self.send_json([dict(r) for r in rows])
        m = re.fullmatch(r"/api/photos/(\d+)", p)
        if m:
            with db() as c:
                r = c.execute("select photo,mime from reports where id=?", (m.group(1),)).fetchone()
            if not r or not r["photo"]:
                return self.send_json({"error": "not found"}, 404)
            self.send_response(200)
            self.send_header("Content-Type", r["mime"] or "image/jpeg")
            self.send_header("Content-Length", str(len(r["photo"])))
            self.end_headers()
            return self.wfile.write(r["photo"])
        return super().do_GET()

    def do_POST(self):
        p = self.path.split("?")[0]
        try:
            d = self.body()
        except Exception:
            return self.send_json({"error": "bad request"}, 400)
        if p == "/api/reports":
            photo, mime = None, None
            m = re.match(r"data:(image/[\w+.-]+);base64,(.+)", d.get("photo") or "", re.S)
            if m:
                mime, photo = m.group(1), base64.b64decode(m.group(2))
            num = lambda v: v if isinstance(v, (int, float)) else None
            with db() as c:
                cur = c.execute("insert into reports(created,lat,lon,acc,note,photo,mime) values(?,?,?,?,?,?,?)",
                    (datetime.now(timezone.utc).isoformat(timespec="seconds"), num(d.get("lat")), num(d.get("lon")),
                     num(d.get("acc")), str(d.get("note") or "")[:500], photo, mime))
            return self.send_json({"id": cur.lastrowid})
        m = re.fullmatch(r"/api/reports/(\d+)/handled", p)
        if m:
            with db() as c:
                c.execute("update reports set status='handled' where id=?", (m.group(1),))
            return self.send_json({"ok": True})
        if p == "/api/check":
            return self.send_json(ai_check(d.get("photo")))
        self.send_json({"error": "not found"}, 404)

if __name__ == "__main__":
    init()
    port = int(os.environ.get("PORT", "8000"))
    print(f"ResQ AI running: app http://localhost:{port}  dashboard http://localhost:{port}/dashboard.html")
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
