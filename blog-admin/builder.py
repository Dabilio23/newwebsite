"""Generateur du blog Dabilio : articles Markdown -> pages HTML statiques.

Sans dependance externe (bibliotheque standard uniquement).
Sources : blog-src/articles/*.md  |  Sortie : blog/*.html
"""
import html
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "blog-src" / "articles"
OUT = ROOT / "blog"
SITE = "https://dabil.io"
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
          "août", "septembre", "octobre", "novembre", "décembre"]
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MARK_BLOG_START, MARK_BLOG_END = "<!-- blog:start -->", "<!-- blog:end -->"


# ---------------------------------------------------------------- Markdown
def _inline(text):
    text = html.escape(text, quote=False)
    codes = []

    def keep_code(m):
        codes.append("<code>%s</code>" % m.group(1))
        return "\x00%d\x00" % (len(codes) - 1)

    text = re.sub(r"`([^`]+)`", keep_code, text)
    text = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)",
                  lambda m: '<img src="%s" alt="%s" loading="lazy">' % (_safe_url(m.group(2)), m.group(1)), text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
                  lambda m: '<a href="%s">%s</a>' % (_safe_url(m.group(2)), m.group(1)), text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?!\w)", r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], text)


def _safe_url(url):
    url = html.unescape(url).strip()
    if re.match(r"^\s*(javascript|data|vbscript):", url, re.I):
        return "#"
    return html.escape(url, quote=True)


def markdown_to_html(md):
    lines = md.replace("\r\n", "\n").split("\n")
    out, i, para = [], 0, []

    def flush():
        if para:
            out.append("<p>%s</p>" % _inline(" ".join(s.strip() for s in para)))
            para.clear()

    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            flush()
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            out.append("<pre><code>%s</code></pre>" % html.escape("\n".join(buf)))
            i += 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            flush()
            level = max(2, len(m.group(1)))  # le titre de l'article est le seul h1
            text = m.group(2).strip()
            out.append('<h%d id="%s">%s</h%d>' % (level, _anchor(text), _inline(text), level))
        elif re.match(r"^\s*([-*_])\s*\1\s*\1[\s\1]*$", line):
            flush()
            out.append("<hr>")
        elif line.startswith(">"):
            flush()
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i].lstrip("> ").rstrip())
                i += 1
            out.append("<blockquote>%s</blockquote>" % markdown_to_html("\n".join(buf)))
            continue
        elif re.match(r"^\s*([-*+])\s+", line) or re.match(r"^\s*\d+[.)]\s+", line):
            flush()
            ordered = bool(re.match(r"^\s*\d+[.)]\s+", line))
            items = []
            while i < len(lines) and re.match(r"^\s*(?:[-*+]|\d+[.)])\s+", lines[i]):
                items.append(re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", lines[i]))
                i += 1
            tag = "ol" if ordered else "ul"
            out.append("<%s>%s</%s>" % (tag, "".join("<li>%s</li>" % _inline(t) for t in items), tag))
            continue
        elif not line.strip():
            flush()
        else:
            para.append(line)
        i += 1
    flush()
    return "\n".join(out)


def _anchor(text):
    t = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.U).strip()
    return re.sub(r"[\s_]+", "-", t) or "section"


# ---------------------------------------------------------------- Articles
def parse_article(path):
    raw = path.read_text(encoding="utf-8")
    meta, body = {}, raw
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", raw, re.S)
    if m:
        for line in m.group(1).split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        body = m.group(2)
    meta["slug"] = path.stem
    meta.setdefault("title", path.stem)
    meta.setdefault("description", "")
    meta.setdefault("date", date.today().isoformat())
    meta.setdefault("image", "")
    meta.setdefault("image_credit", "")
    meta.setdefault("image_credit_url", "")
    meta.setdefault("tags", "")
    meta.setdefault("status", "draft")
    return meta, body.strip()


def serialize_article(meta, body):
    keys = ["title", "description", "date", "image", "image_credit", "image_credit_url", "tags", "status"]
    head = "\n".join("%s: %s" % (k, str(meta.get(k, "")).replace("\n", " ").strip()) for k in keys)
    return "---\n%s\n---\n\n%s\n" % (head, body.strip())


def all_articles():
    items = []
    for p in sorted(SRC.glob("*.md")):
        meta, body = parse_article(p)
        meta["body"] = body
        items.append(meta)
    return sorted(items, key=lambda a: a["date"], reverse=True)


def french_date(iso):
    try:
        y, m, d = (int(x) for x in iso.split("-"))
        return "%d %s %d" % (d, MONTHS[m - 1], y)
    except Exception:
        return iso


def reading_minutes(body):
    return max(1, round(len(re.findall(r"\w+", body)) / 200))


# ---------------------------------------------------------------- Gabarits
def _site_parts():
    """Nav et footer repris de modules/services.html : le blog suit toujours le site."""
    src = (ROOT / "modules" / "services.html").read_text(encoding="utf-8")
    nav = re.search(r"<!-- =+ NAV =+ -->.*?</nav>", src, re.S).group(0)
    footer = re.search(r"<footer.*?</footer>", src, re.S).group(0)
    nav = nav.replace('href="services.html"', 'href="../modules/services.html"')
    footer = footer.replace('href="services.html"', 'href="../modules/services.html"') \
                   .replace('href="annuaire.html"', 'href="../modules/annuaire.html"')
    return nav, footer


STYLE = """
        body { font-family: 'Inter', sans-serif; }
        .article-body { font-size: 1.125rem; line-height: 1.8; color: #3f3f46; }
        .article-body > * + * { margin-top: 1.25rem; }
        .article-body h2 { font-size: 1.75rem; line-height: 1.25; font-weight: 500; letter-spacing: -0.02em; color: #18181b; margin-top: 2.75rem; }
        .article-body h3 { font-size: 1.35rem; line-height: 1.3; font-weight: 500; color: #18181b; margin-top: 2rem; }
        .article-body h4 { font-size: 1.1rem; font-weight: 600; color: #18181b; margin-top: 1.5rem; }
        .article-body a { color: #4059ad; text-decoration: underline; text-underline-offset: 3px; }
        .article-body ul { list-style: disc; padding-left: 1.5rem; }
        .article-body ol { list-style: decimal; padding-left: 1.5rem; }
        .article-body li + li { margin-top: 0.4rem; }
        .article-body blockquote { border-left: 3px solid #10b981; padding: 0.25rem 0 0.25rem 1.25rem; color: #52525b; font-style: italic; }
        .article-body img { border-radius: 1rem; width: 100%; height: auto; border: 1px solid #e4e4e7; }
        .article-body code { background: #f4f4f5; padding: 0.1rem 0.4rem; border-radius: 0.4rem; font-size: 0.95em; }
        .article-body pre { background: #1b1b1e; color: #e4e4e7; padding: 1.25rem; border-radius: 1rem; overflow-x: auto; }
        .article-body pre code { background: transparent; padding: 0; }
        .article-body hr { border: 0; border-top: 1px solid #e4e4e7; margin: 2.5rem 0; }
"""


def _page(title, description, canonical, og_image, body_html, jsonld, og_type="website"):
    nav, footer = _site_parts()
    t, d = html.escape(title, quote=True), html.escape(description, quote=True)
    return """<!doctype html>
<html lang="fr">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{t}</title>
    <meta name="description" content="{d}">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="{canonical}">
    <meta property="og:type" content="{og_type}">
    <meta property="og:site_name" content="Dabilio">
    <meta property="og:url" content="{canonical}">
    <meta property="og:title" content="{t}">
    <meta property="og:description" content="{d}">
    <meta property="og:image" content="{og_image}">
    <meta property="og:locale" content="fr_FR">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{t}">
    <meta name="twitter:description" content="{d}">
    <meta name="twitter:image" content="{og_image}">
    <script type="application/ld+json">
{jsonld}
    </script>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://code.iconify.design/iconify-icon/1.0.7/iconify-icon.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&amp;display=swap" rel="stylesheet">
    <style>{style}</style>
</head>

<body
    class="bg-[#FAFAFA] text-zinc-900 antialiased selection:bg-emerald-200 selection:text-emerald-950 overflow-x-hidden scroll-smooth">

    {nav}

    <main>
{body}
    </main>

    {footer}

    <script>
        document.addEventListener('DOMContentLoaded', function () {{
            var menuToggle = document.getElementById('menu-toggle');
            var mobileMenu = document.getElementById('mobile-menu');
            if (menuToggle && mobileMenu) {{
                menuToggle.addEventListener('click', function () {{
                    mobileMenu.classList.toggle('hidden');
                }});
            }}
        }});
    </script>

  <!-- Start of HubSpot Embed Code -->
  <script type="text/javascript" id="hs-script-loader" async defer src="//js-eu1.hs-scripts.com/148611543.js"></script>
  <!-- End of HubSpot Embed Code -->
</body>

</html>
""".format(t=t, d=d, canonical=canonical, og_image=og_image, og_type=og_type,
           jsonld=jsonld, style=STYLE, nav=nav, footer=footer, body=body_html)


def _img_rel(image):
    return ("../" + image.lstrip("/")) if image else ""


def _img_abs(image):
    return "%s/%s" % (SITE, image.lstrip("/")) if image else "%s/public/logo.png" % SITE


def _tags(a):
    return [t.strip() for t in a["tags"].split(",") if t.strip()]


def render_article(a):
    url = "%s/blog/%s.html" % (SITE, a["slug"])
    cover = ""
    if a["image"]:
        cover = '<img src="%s" alt="%s" class="w-full rounded-3xl border border-zinc-200 shadow-sm mb-12">' % (
            html.escape(_img_rel(a["image"]), quote=True), html.escape(a["title"], quote=True))
    credit = ""
    if a["image"] and (a["image_credit"] or a["image_credit_url"]):
        label = html.escape(a["image_credit"] or a["image_credit_url"])
        url_ok = re.match(r"^https?://", a["image_credit_url"] or "", re.I)
        link = '<a href="%s" target="_blank" rel="noopener noreferrer" class="underline underline-offset-2 hover:text-zinc-700">%s</a>' % (
            html.escape(a["image_credit_url"], quote=True), label) if url_ok else label
        cover = cover.replace("mb-12", "mb-3")
        credit = '<p class="text-xs text-zinc-400 mb-12">Source de l\'image : %s</p>' % link
    tags = "".join('<span class="text-xs text-[#4059ad] bg-[#4059ad]/10 border border-[#4059ad]/20 px-3 py-1 rounded-full">%s</span>'
                   % html.escape(t) for t in _tags(a))
    body = """        <article class="pt-36 pb-24">
            <div class="max-w-3xl mx-auto px-6">
                <a href="index.html" class="inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-900 transition-colors mb-8">
                    <iconify-icon icon="solar:arrow-left-linear" width="16" height="16"></iconify-icon>
                    Tous les articles
                </a>
                <div class="flex flex-wrap gap-2 mb-5">{tags}</div>
                <h1 class="text-4xl md:text-5xl font-medium tracking-tight text-zinc-900 leading-[1.1] mb-6">{title}</h1>
                <p class="text-sm text-zinc-500 mb-10">{d} - {mins} min de lecture</p>
                {cover}{credit}
                <div class="article-body">
{content}
                </div>
                <div class="mt-16 rounded-3xl bg-[#170b30] text-white p-8 md:p-10 text-center">
                    <h2 class="text-2xl font-medium tracking-tight mb-3">Parlons des enjeux de votre établissement</h2>
                    <p class="text-white/70 mb-6">Découvrez comment Dabilio répond aux enjeux du terrain.</p>
                    <a href="../index.html#contact" class="inline-flex items-center gap-2 bg-[#f9f7f3] text-black font-medium px-8 py-4 rounded-full hover:bg-[#f2cc8f] transition-all">
                        Demander une démo
                        <iconify-icon icon="solar:arrow-right-linear" width="18" height="18"></iconify-icon>
                    </a>
                </div>
            </div>
        </article>""".format(tags=tags, title=html.escape(a["title"]), d=french_date(a["date"]),
                             mins=reading_minutes(a["body"]), cover=cover, credit=credit,
                             content=markdown_to_html(a["body"]))
    ld = json.dumps({
        "@context": "https://schema.org", "@type": "Article",
        "headline": a["title"], "description": a["description"],
        "datePublished": a["date"], "dateModified": a["date"],
        "image": _img_abs(a["image"]), "inLanguage": "fr",
        "mainEntityOfPage": url,
        "author": {"@type": "Organization", "name": "Dabilio"},
        "publisher": {"@type": "Organization", "name": "Dabilio",
                      "logo": {"@type": "ImageObject", "url": SITE + "/public/logo.png"}},
    }, ensure_ascii=False, indent=2)
    return _page("%s | Dabilio" % a["title"], a["description"], url, _img_abs(a["image"]), body, ld, "article")


def render_index(articles):
    cards = []
    for a in articles:
        img = ""
        if a["image"]:
            img = '<img src="%s" alt="" loading="lazy" class="w-full h-48 object-cover">' % html.escape(_img_rel(a["image"]), quote=True)
        cards.append("""                <a href="{slug}.html" class="group bg-white border border-zinc-200 rounded-2xl overflow-hidden hover:border-zinc-400 hover:shadow-md transition-all flex flex-col">
                    {img}
                    <div class="p-6 flex flex-col flex-1">
                        <p class="text-xs text-zinc-400 mb-3">{d} - {mins} min de lecture</p>
                        <h2 class="text-xl font-medium tracking-tight text-zinc-900 mb-2">{title}</h2>
                        <p class="text-sm text-zinc-500 leading-relaxed mb-5">{desc}</p>
                        <span class="inline-flex items-center gap-1 text-xs text-zinc-400 mt-auto group-hover:text-zinc-700 transition-colors">
                            Lire l'article <iconify-icon icon="solar:arrow-right-linear" width="12" height="12"></iconify-icon>
                        </span>
                    </div>
                </a>""".format(slug=a["slug"], img=img, d=french_date(a["date"]), mins=reading_minutes(a["body"]),
                               title=html.escape(a["title"]), desc=html.escape(a["description"])))
    grid = "\n".join(cards) if cards else '<p class="text-zinc-500">Les premiers articles arrivent bientôt.</p>'
    body = """        <section class="pt-36 pb-24">
            <div class="max-w-7xl mx-auto px-6">
                <div class="max-w-3xl mx-auto text-center mb-14">
                    <h1 class="text-4xl md:text-5xl font-medium tracking-tight text-zinc-900 leading-[1.1] mb-6">
                        Le blog <span class="text-emerald-500">Dabilio</span>
                    </h1>
                    <p class="text-lg text-zinc-500 leading-relaxed">
                        Les enjeux de l'éducation à Madagascar, vus du terrain : pilotage, vie scolaire, enseignants et familles.
                    </p>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
{grid}
                </div>
            </div>
        </section>""".format(grid=grid)
    ld = json.dumps({"@context": "https://schema.org", "@type": "Blog", "name": "Blog Dabilio",
                     "url": SITE + "/blog/", "inLanguage": "fr",
                     "publisher": {"@type": "Organization", "name": "Dabilio"}}, ensure_ascii=False, indent=2)
    return _page("Blog Dabilio | Enjeux de l'éducation à Madagascar",
                 "Articles sur les enjeux de l'éducation à Madagascar : pilotage, vie scolaire, enseignants et familles.",
                 SITE + "/blog/", SITE + "/public/logo.png", body, ld)


# ---------------------------------------------------------------- Build
def _replace_block(path, block, wrap):
    """Remplace (ou ajoute) le bloc balise entre les marqueurs du blog."""
    text = path.read_text(encoding="utf-8")
    pat = re.compile(r"\n?[ \t]*%s.*?%s\n?" % (re.escape(MARK_BLOG_START), re.escape(MARK_BLOG_END)), re.S)
    text = pat.sub("\n", text).rstrip("\n") + "\n"
    if block:
        text = wrap(text, "%s\n%s\n%s" % (MARK_BLOG_START, block, MARK_BLOG_END))
    path.write_text(text, encoding="utf-8")


def build():
    published = [a for a in all_articles() if a["status"] == "published"]
    OUT.mkdir(exist_ok=True)
    keep = {"index.html"} | {a["slug"] + ".html" for a in published}
    for f in OUT.glob("*.html"):
        if f.name not in keep:
            f.unlink()
    for a in published:
        (OUT / (a["slug"] + ".html")).write_text(render_article(a), encoding="utf-8")
    (OUT / "index.html").write_text(render_index(published), encoding="utf-8")

    urls = ['  <url>\n    <loc>%s/blog/</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.7</priority>\n  </url>' % SITE]
    for a in published:
        urls.append('  <url>\n    <loc>%s/blog/%s.html</loc>\n    <lastmod>%s</lastmod>\n    <priority>0.6</priority>\n  </url>'
                    % (SITE, a["slug"], a["date"]))
    _replace_block(ROOT / "sitemap.xml", "\n".join(urls) if published else "",
                   lambda t, b: t.replace("</urlset>", b + "\n</urlset>"))
    llms = "## Blog\n\n- [Blog Dabilio](%s/blog/): Articles sur les enjeux de l'éducation à Madagascar.\n%s" % (
        SITE, "".join("- [%s](%s/blog/%s.html): %s\n" % (a["title"], SITE, a["slug"], a["description"]) for a in published))
    _replace_block(ROOT / "llms.txt", llms.rstrip() if published else "",
                   lambda t, b: t.rstrip() + "\n\n" + b + "\n")
    return {"published": len(published), "total": len(all_articles())}


if __name__ == "__main__":
    print(build())
