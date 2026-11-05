#!/usr/bin/env python3
"""Outil d'edition du blog Dabilio (local uniquement).

Lancement :  python3 blog-admin/admin.py
Puis ouvrir http://localhost:8800  (le navigateur s'ouvre tout seul).

Ecoute uniquement sur 127.0.0.1 : ne jamais deployer ni exposer cet outil.
"""
import base64
import json
import mimetypes
import re
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parent))
import builder  # noqa: E402

ROOT = builder.ROOT
PORT = 8800
IMG_DIR = ROOT / "public" / "blog"
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
STATIC_EXT = {".html", ".css", ".js", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico", ".xml", ".txt", ".json"}
PUBLISH_PATHS = ["blog", "blog-src", "public/blog", "sitemap.xml", "llms.txt"]


def run_git(*args, timeout=90):
    env = {"GIT_TERMINAL_PROMPT": "0", "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"}
    p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=env)
    return p.returncode, (p.stdout + p.stderr).strip()


def unpushed_count():
    """Nombre de commits locaux pas encore sur GitHub (0 si inconnu)."""
    code, out = run_git("rev-list", "--count", "origin/main..HEAD")
    return int(out) if code == 0 and out.isdigit() else 0


def push_explained():
    code, out = run_git("push", "origin", "HEAD")
    if code and ("rejected" in out or "non-fast-forward" in out or "fetch first" in out):
        raise ValueError("GitHub contient des commits que vous n'avez pas en local (quelqu'un a publié avant vous).\n"
                         "Rien n'a été écrasé. Ne forcez pas : demandez de récupérer d'abord les changements "
                         "(git pull) avant de republier.\n\n" + out)
    if code:
        raise ValueError("L'envoi vers GitHub a échoué :\n" + out)
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "DabilioBlogAdmin"

    def log_message(self, *a):
        pass

    # ---- utilitaires
    def _host_ok(self):
        return self.headers.get("Host", "") in ("localhost:%d" % PORT, "127.0.0.1:%d" % PORT)

    def _json(self, code, data):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 12 * 1024 * 1024:
            raise ValueError("Requête trop volumineuse")
        return json.loads(self.rfile.read(n) or b"{}")

    # ---- GET
    def do_GET(self):
        if not self._host_ok():
            return self._json(403, {"error": "Hôte refusé"})
        u = urlparse(self.path)
        if u.path in ("/", "/_admin", "/_admin/"):
            return self._file(Path(__file__).parent / "admin.html")
        if u.path == "/api/articles":
            return self._json(200, [{k: a[k] for k in ("slug", "title", "date", "status")} for a in builder.all_articles()])
        if u.path == "/api/article":
            slug = parse_qs(u.query).get("slug", [""])[0]
            if not builder.SLUG_RE.match(slug) or not (builder.SRC / (slug + ".md")).exists():
                return self._json(404, {"error": "Article introuvable"})
            meta, body = builder.parse_article(builder.SRC / (slug + ".md"))
            meta["body"] = body
            return self._json(200, meta)
        if u.path == "/api/git-status":
            code, out = run_git("status", "--short", "--", *PUBLISH_PATHS)
            run_git("fetch", "origin", timeout=30)
            return self._json(200, {"changes": [l for l in out.splitlines() if l.strip()], "unpushed": unpushed_count()})
        # fichiers du site, pour l'apercu (lecture seule, liste blanche d'extensions)
        rel = u.path.lstrip("/")
        if rel.endswith("/") or rel == "":
            rel += "index.html"
        target = (ROOT / rel).resolve()
        if ROOT in target.parents and target.is_file() and target.suffix in STATIC_EXT \
                and not any(p.startswith(".") for p in target.relative_to(ROOT).parts) \
                and target.parts[len(ROOT.parts)] not in ("blog-admin",):
            return self._file(target)
        self._json(404, {"error": "Introuvable"})

    def _file(self, path):
        data = path.read_bytes()
        self.send_response(200)
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text/") or ctype.endswith("json") else ""))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    # ---- POST
    def do_POST(self):
        if not self._host_ok() or self.headers.get("X-Blog-Admin") != "1":
            return self._json(403, {"error": "Requête refusée"})
        try:
            data = self._body()
            route = urlparse(self.path).path
            if route == "/api/preview":
                return self._json(200, {"html": builder.markdown_to_html(data.get("body", ""))})
            if route == "/api/save":
                return self._json(200, self._save(data))
            if route == "/api/delete":
                slug = data.get("slug", "")
                if not builder.SLUG_RE.match(slug):
                    raise ValueError("Slug invalide")
                (builder.SRC / (slug + ".md")).unlink(missing_ok=True)
                builder.build()
                return self._json(200, {"ok": True})
            if route == "/api/upload":
                return self._json(200, self._upload(data))
            if route == "/api/publish":
                return self._json(200, self._publish(data))
            self._json(404, {"error": "Route inconnue"})
        except Exception as e:  # message lisible dans l'interface
            self._json(400, {"error": str(e)})

    def _save(self, d):
        slug, old = d.get("slug", ""), d.get("old_slug", "")
        if not builder.SLUG_RE.match(slug):
            raise ValueError("Adresse (slug) invalide : lettres minuscules, chiffres et tirets seulement.")
        if slug == "index":
            raise ValueError("« index » est réservé.")
        if slug != old and (builder.SRC / (slug + ".md")).exists():
            raise ValueError("Un article utilise déjà cette adresse.")
        if not d.get("title", "").strip():
            raise ValueError("Le titre est obligatoire.")
        if d.get("status") == "published" and not d.get("description", "").strip():
            raise ValueError("La description est obligatoire pour publier (elle sert au référencement).")
        builder.SRC.mkdir(parents=True, exist_ok=True)
        meta = {k: d.get(k, "") for k in ("title", "description", "date", "image", "image_credit", "image_credit_url", "tags", "status")}
        if meta["image_credit_url"].strip() and not re.match(r"^https?://", meta["image_credit_url"].strip(), re.I):
            raise ValueError("Le lien de la source de l'image doit commencer par http:// ou https://")
        if meta["status"] not in ("draft", "published"):
            meta["status"] = "draft"
        (builder.SRC / (slug + ".md")).write_text(builder.serialize_article(meta, d.get("body", "")), encoding="utf-8")
        if old and old != slug and builder.SLUG_RE.match(old):
            (builder.SRC / (old + ".md")).unlink(missing_ok=True)
        return {"ok": True, "slug": slug, "build": builder.build()}

    def _upload(self, d):
        name = Path(d.get("name", "")).name.lower()
        stem = re.sub(r"[^a-z0-9]+", "-", Path(name).stem).strip("-") or "image"
        ext = Path(name).suffix
        if ext not in IMG_EXT:
            raise ValueError("Format non accepté (png, jpg, webp, gif).")
        raw = base64.b64decode(d.get("data", ""), validate=False)
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError("Image trop lourde (8 Mo maximum).")
        IMG_DIR.mkdir(parents=True, exist_ok=True)
        final, n = stem + ext, 1
        while (IMG_DIR / final).exists():
            n += 1
            final = "%s-%d%s" % (stem, n, ext)
        (IMG_DIR / final).write_bytes(raw)
        return {"path": "public/blog/" + final}

    def _publish(self, d):
        title = (d.get("message") or "Blog : mise à jour des articles").replace("\n", " ")[:120]
        builder.build()
        code, out = run_git("add", "-A", "--", *PUBLISH_PATHS)
        if code:
            raise ValueError("git add a échoué :\n" + out)
        code, status = run_git("status", "--short", "--", *PUBLISH_PATHS)
        out = ""
        if status.strip():
            code, out = run_git("commit", "-m", title, "--", *PUBLISH_PATHS)
            if code:
                raise ValueError("git commit a échoué :\n" + out)
        elif not unpushed_count():
            return {"ok": True, "log": "Rien à publier : tout est déjà à jour sur GitHub."}
        push = push_explained()
        return {"ok": True, "log": (out + "\n" + push).strip()}


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = "http://localhost:%d" % PORT
    print("Blog Dabilio - outil d'édition : %s  (Ctrl+C pour arrêter)" % url)
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt.")


if __name__ == "__main__":
    main()
