#!/usr/bin/env python3
"""md2html: turn the "Ada 2022 from Zero" markdown export back into a styled, interactive web page.

Usage:
    python3 md2html.py Ada_2022_from_Zero.md                 # writes Ada_2022_from_Zero.html
    python3 md2html.py course.md -o site/index.html          # choose the output file
    python3 md2html.py course.md --watch                     # rebuild every time you save the .md

Standard library only: no pip, no pandoc. Plain markdown (headings, paragraphs, lists, tables, fenced
code, **bold**, *italic*, `code`, [links](url)) converts as usual. On top of that it recognises the
patterns the course export uses and rebuilds the page's features from them:

    "# 3" then "## Title" then a paragraph   lesson section with number badge, title and lead
    "### 2Make a folder"                      numbered setup step
    a short label line, then a code fence     captioned block:
        Terminal / Target output              terminal styling (prompt, errors in red)
        name.adb / name.ads                   Ada code: highlighting, line numbers, Copy button
        anything else ("Fedora")              shell command with a Copy button
    "Exercise 4.2" or "Checkpoint", then "#### Title"   exercise card with a Mark done tick
    "Hint" / "Solution" / "If it doesn't work" / "Notes" folding sections inside an exercise
    "#### Remember" and "#### Common mistakes"          summary panel
    "Your computer", "On Linux" / "On Windows" / "On Mac"  system picker that shows one panel at a time
    "Statement", "Screen afterwards", then "1`Put (...);`" lines   cursor walkthrough, recomputed
    "**3** full groups of 2: ..."                       the division dots picture
    alternating "`name`" / description lines            nested scope boxes
    a run of "[Lesson 1: Title](#1)" lines              the lesson deck with progress holes
    "## Glossary" then term / definition pairs          glossary list
    "[Lesson 8](#arrays)" style links                   pointed at the right lesson by their text

Anything it can't place is still rendered as ordinary markdown, and a summary with any warnings is
printed after each build, so you can see when an edit broke a pattern.
"""
import argparse, html, os, re, sys, time
from html.parser import HTMLParser

E = html.escape
TYPED_ON, TYPED_OFF = "\x01", "\x02"   # stand-ins for <ins>…</ins> until the text is escaped

# --------------------------------------------------------------------------- markdown blocks

def parse_blocks(text):
    lines = text.replace("\r\n", "\n").split("\n")
    blocks, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            lang = line[3:].strip()
            j = i + 1
            body = []
            while j < n and not lines[j].startswith("```"):
                body.append(lines[j])
                j += 1
            blocks.append(dict(t="code", text="\n".join(body), lang=lang, line=i + 1))
            i = j + 1
            continue
        if re.match(r"^<pre>\s*$", line):
            # raw HTML terminal: plain text, with <ins> or <u> around what the user typed
            j = i + 1
            while j < n and lines[j].strip() != "</pre>":
                j += 1
            raw = "\n".join(lines[i + 1:j])
            marked = re.sub(r"<(ins|u)>", TYPED_ON, raw)
            marked = re.sub(r"</(ins|u)>", TYPED_OFF, marked)
            stray = re.findall(r"</?[A-Za-z][^>]*>", marked)
            marked = html.unescape(marked)
            blocks.append(dict(t="code", text=marked.replace(TYPED_ON, "").replace(TYPED_OFF, ""),
                               marked=marked, lang="", line=i + 1, stray=stray,
                               unclosed=j >= n))
            i = j + 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            blocks.append(dict(t="h", level=len(m.group(1)), text=m.group(2).strip(), line=i + 1))
            i += 1
            continue
        if line.startswith("|") and i + 1 < n and re.match(r"^\|\s*:?-{3,}", lines[i + 1]):
            head = split_row(line)
            rows, j = [], i + 2
            while j < n and lines[j].startswith("|"):
                rows.append(split_row(lines[j]))
                j += 1
            blocks.append(dict(t="table", head=head, rows=rows, line=i + 1))
            i = j
            continue
        for kind, pat in (("ul", r"^[-*+]\s+(.*)$"), ("ol", r"^\d+[.)]\s+(.*)$")):
            if re.match(pat, line):
                items, j = [], i
                while j < n and re.match(pat, lines[j]):
                    items.append(re.match(pat, lines[j]).group(1))
                    j += 1
                    while j < n and lines[j].startswith("  ") and lines[j].strip():  # continuation
                        items[-1] += " " + lines[j].strip()
                        j += 1
                blocks.append(dict(t=kind, items=items, line=i + 1))
                i = j
                break
        else:
            para, j = [line], i + 1
            while j < n and lines[j].strip() and not re.match(r"^(#{1,6}\s|```|<pre>|\||[-*+]\s|\d+[.)]\s)", lines[j]):
                para.append(lines[j])
                j += 1
            blocks.append(dict(t="p", text=" ".join(s.strip() for s in para), line=i + 1))
            i = j
    return blocks


def split_row(line):
    """Split a table row on |, ignoring pipes inside `code`."""
    cells, cur, in_code = [], "", False
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    for ch in s:
        if ch == "`":
            in_code = not in_code
        if ch == "|" and not in_code:
            cells.append(cur.strip())
            cur = ""
        else:
            cur += ch
    cells.append(cur.strip())
    return cells

# --------------------------------------------------------------------------- inline markdown

class Ctx:
    def __init__(self):
        self.ids = set()
        self.warnings = []
        self.lesson_ids = set()

    def warn(self, line, msg):
        self.warnings.append(f"line {line}: {msg}")


def inline(text, ctx, line=0):
    codes = []
    def keep(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"
    s = re.sub(r"`([^`]+)`", keep, text)
    s = E(s, quote=False)
    def link(m):
        label, url = m.group(1), m.group(2)
        if url.startswith("#"):
            url = resolve_anchor(url, label, ctx, line)
        return f'<a href="{E(url)}">{label}</a>'
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])", r"<em>\1</em>", s)
    def unkeep(m):
        c = codes[int(m.group(1))]
        cls = ' class="nw"' if len(c) <= 24 else ""
        return f"<code{cls}>{E(c, quote=False)}</code>"
    return re.sub(r"\x00(\d+)\x00", unkeep, s)


def resolve_anchor(url, label, ctx, line):
    frag = url[1:]
    if frag in ctx.ids:
        return url
    plain = re.sub(r"<[^>]+>", "", label)
    m = re.match(r"^Lesson (\d+)\b", plain)
    if m and m.group(1) in ctx.lesson_ids:
        return "#" + m.group(1)
    if plain.strip().lower() in ("setup", "start here") and "0" in ctx.lesson_ids:
        return "#0"
    ctx.warn(line, f"link to {url} doesn't match any section")
    return url


def slug(text):
    s = re.sub(r"[^a-z0-9]+", "-", re.sub(r"<[^>]+>", "", text).lower()).strip("-")
    return s or "section"

# --------------------------------------------------------------------------- code blocks

ADA_KW = set("""abort abs abstract accept access aliased all and array at begin body case constant declare
delay delta digits do else elsif end entry exception exit for function generic goto if in interface is
limited loop mod new not null of or others out overriding package parallel pragma private procedure
protected raise range record rem renames requeue return reverse select separate some subtype
synchronized tagged task terminate then type until use when while with xor""".split())


def highlight_ada(src, numbered=True):
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if src.startswith("--", i):
            j = src.find("\n", i)
            j = n if j < 0 else j
            out.append(f'<i class="c">{E(src[i:j])}</i>'); i = j; continue
        if c == '"':
            m = re.compile(r'"(?:[^"\n]|"")*"?').match(src, i)
            out.append(f'<b class="s">{E(m.group())}</b>'); i = m.end(); continue
        if c == "'":
            prev = src[i - 1] if i else " "
            if (prev.isalnum() or prev in "_)]") and re.match(r"'[A-Za-z]", src[i:i + 2]):
                m = re.compile(r"'[A-Za-z_][A-Za-z0-9_]*").match(src, i)
                out.append(f'<b class="a">{E(m.group())}</b>'); i = m.end(); continue
            if i + 2 < n and src[i + 2] == "'":
                out.append(f'<b class="s">{E(src[i:i + 3])}</b>'); i += 3; continue
        if c.isdigit() and not (i and (src[i - 1].isalnum() or src[i - 1] == "_")):
            m = re.compile(r"\d[\d_]*(?:#[0-9A-Fa-f_]+#)?(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?").match(src, i)
            out.append(f'<b class="n">{E(m.group())}</b>'); i = m.end(); continue
        if c.isalpha():
            m = re.compile(r"[A-Za-z][A-Za-z0-9_]*").match(src, i)
            w = m.group()
            out.append(f'<b class="k">{w}</b>' if w.lower() in ADA_KW else E(w)); i = m.end(); continue
        if c == "@":
            out.append('<b class="k">@</b>'); i += 1; continue
        out.append(E(c)); i += 1
    if not numbered:
        return "".join(out)
    return "".join(f'<span class="ln">{l}</span>\n' for l in "".join(out).split("\n"))


def terminal_html(src):
    def T(s):  # escape, then turn the typed-input markers into <u>
        return E(s).replace(TYPED_ON, "<u>").replace(TYPED_OFF, "</u>")
    rows = []
    for l in src.split("\n"):
        if l.startswith("$ ") or l == "$":
            rows.append(f'<span class="pr">$</span> <span class="cm">{T(l[2:])}</span>')
        elif re.search(r"\berror:|^raised ", l):
            rows.append(f'<span class="err">{T(l)}</span>')
        elif re.search(r"\bwarning:", l):
            rows.append(f'<span class="wrn">{T(l)}</span>')
        else:
            rows.append(T(l))
    return "\n".join(rows)


class Ids:
    n = 0
    @classmethod
    def next(cls, p):
        cls.n += 1
        return f"{p}{cls.n}"


def is_session(code):
    """A captured terminal session has $ prompt lines; a box of commands to type doesn't."""
    return any(l.startswith("$ ") or l == "$" for l in code.split("\n"))


def code_figure(caption, code, marked=None):
    """marked: the same text with TYPED_ON/TYPED_OFF around typed input, from a <pre> block."""
    underlined = bool(marked and TYPED_ON in marked)
    if caption and caption.startswith("Target output") and "underlined" in caption and not underlined:
        # no underline markup in this box, so don't promise it
        caption = "Target output, including what the user typed"
    if (caption or "").startswith("Target output") or (caption == "Terminal" and is_session(code)):
        cls = "term goal" if caption.startswith("Target output") else "term"
        return (f'<figure class="{cls}"><figcaption><span>{E(caption)}</span></figcaption>'
                f"<pre>{terminal_html(marked if underlined else code)}</pre></figure>")
    i = Ids.next("c")
    if caption and re.search(r"\.ad[bs]$", caption):
        body, cls = highlight_ada(code), "code"
    else:
        body, cls = E(code), "code sh"
    cap = (f'<figcaption><span>{E(caption or "")}</span>'
           f'<button class="copy" type="button" data-copy="{i}">Copy</button></figcaption>')
    return f'<figure class="{cls}">{cap}<pre id="{i}"><code>{body}</code></pre></figure>'

# --------------------------------------------------------------------------- course patterns

LABEL_RX = re.compile(r"^(?!.*[.:?!]$)(?!.*[.:?!]\s).{1,60}$|^Target output\b.{0,60}$")
EX_RX = re.compile(r"^(Exercise (\d+)\.(\d+)|Checkpoint)$")
OS_LABELS = {"On Linux": "linux", "On Windows": "windows", "On Mac": "mac"}
SOL_LABELS = ("Solution", "If it doesn't work", "Notes")
TRACE_RX = re.compile(r"^(\d+)`(.+)`$")
DIVIDE_RX = re.compile(r"^\*\*(\d+)\*\* full groups of (\d+): `[^`]+`\*\*(\d+)\*\* left over: `[^`]+`$")
CODE_ONLY_RX = re.compile(r"^`([^`]+)`$")
DECK_RX = re.compile(r"^\[([^\]]+)\]\(#([^)]+)\)$")


def simulate(stmts):
    screens, screen = [], ""
    for st in stmts:
        m = re.match(r'^(Put_Line|Put|New_Line)\s*(?:\("(.*)"\)|\((\d+)\))?;$', st)
        if not m:
            return None
        op, text, count = m.group(1), m.group(2) or "", int(m.group(3) or 1)
        screen += {"Put": text, "Put_Line": text + "\n", "New_Line": "\n" * count}[op]
        screens.append(screen)
    return screens


def is_label(b):
    return b and b["t"] == "p" and LABEL_RX.match(b["text"]) and "](" not in b["text"]


class Out:
    def __init__(self):
        self.parts, self.stack = [], []

    def add(self, s):
        self.parts.append(s)

    def open(self, kind, html_open):
        self.parts.append(html_open)
        self.stack.append(kind)

    def close_to(self, *kinds):
        """Close containers until none of `kinds` is open."""
        while any(k in self.stack for k in kinds):
            self.close_top()

    def close_top(self):
        kind = self.stack.pop()
        self.parts.append({"section": "</div></section>", "details": "</details>", "ex": "</article>",
                           "osp": "</div>", "exs": "</div>", "gloss": "</dl></div></section>",
                           "header": "</div></header>", "footer": "</div></footer>"}.get(kind, "</div>"))

    def close_all(self):
        while self.stack:
            self.close_top()


def render(blocks, ctx):
    # first pass: lessons, exercises per lesson, heading ids
    lesson_ex, cur = {}, None
    for k, b in enumerate(blocks):
        if b["t"] == "h" and b["level"] == 1 and b["text"].isdigit():
            cur = b["text"]
            lesson_ex[cur] = []
            ctx.lesson_ids.add(cur)
            ctx.ids.add(cur)
        elif b["t"] == "p" and EX_RX.match(b["text"]) and cur is not None:
            nxt = blocks[k + 1] if k + 1 < len(blocks) else None
            if nxt and nxt["t"] == "h" and nxt["level"] == 4:
                lesson_ex[cur].append(ex_id(b["text"], cur))
        elif b["t"] == "h" and b["text"].lower() == "glossary":
            ctx.ids.add("glossary")
    total_ex = sum(len(v) for v in lesson_ex.values())
    any_typed = any(TYPED_ON in b.get("marked", "") for b in blocks)
    for k, b in enumerate(blocks):
        if b["t"] == "p" and "underlined" in b["text"] and not any_typed:
            ctx.warn(b["line"], "says typed input is underlined, but the markdown has no underline markup")
        if b["t"] == "p" and b["text"].startswith("Target output") and "underlined" in b["text"]:
            nb = blocks[k + 1] if k + 1 < len(blocks) else None
            if not (nb and TYPED_ON in nb.get("marked", "")):
                ctx.warn(b["line"], "caption promises underlined input, but the box below has no <ins> markup")
        if b.get("stray"):
            ctx.warn(b["line"], f"<pre> block has tags other than <ins>/<u>: {b['stray'][:3]}")
        if b.get("unclosed"):
            ctx.warn(b["line"], "<pre> block is never closed with </pre>")

    o, i, n = Out(), 0, len(blocks)
    title = None
    nav = []
    short = {}
    stats = dict(code=0, plain=0, terminal=0, target=0, typed=0, shell=0, exercises=0, os_panels=0, tables=0)

    def nxt(k=1):
        return blocks[i + k] if i + k < n else None

    while i < n:
        b = blocks[i]
        t = b["t"]

        # ---------------- headings
        if t == "h":
            text, lvl = b["text"], b["level"]
            if lvl == 1 and title is None and not text.isdigit():
                title = text
                o.add(f'<header class="band top"><div class="wrap"><h1>{inline(text, ctx, b["line"])}</h1>')
                o.stack.append("header")
                i += 1
                continue
            if lvl == 1 and text.isdigit():
                o.close_all()
                num = text
                h2 = nxt()
                ttl = h2["text"] if h2 and h2["t"] == "h" and h2["level"] == 2 else f"Lesson {num}"
                i += 2 if h2 and h2["t"] == "h" and h2["level"] == 2 else 1
                lead = ""
                if i < n and blocks[i]["t"] == "p" and not is_label(blocks[i]):
                    lead = f'<p class="lead">{inline(blocks[i]["text"], ctx, blocks[i]["line"])}</p>'
                    i += 1
                nav.append((num, ttl))
                o.open("section", f'<section class="lesson band" id="{num}"><div class="lw">'
                                  f'<header class="lh"><span class="badge" aria-hidden="true">{num}</span>'
                                  f'<div><h2>{inline(ttl, ctx)}</h2>{lead}</div></header>')
                continue
            if lvl == 2 and text.lower() == "glossary":
                o.close_all()
                i += 1
                lead = ""
                if i < n and blocks[i]["t"] == "p" and not is_label(blocks[i]):
                    lead = f'<p class="lead">{inline(blocks[i]["text"], ctx, blocks[i]["line"])}</p>'
                    i += 1
                nav.append(("glossary", "Glossary"))
                o.open("gloss", '<section class="band gloss" id="glossary"><div class="lw"><header class="lh">'
                                '<span class="badge" aria-hidden="true">A–Z</span><div><h2>Glossary</h2>'
                                f'{lead}</div></header><dl class="glist">')
                while i + 1 < n and blocks[i]["t"] == "p" and blocks[i + 1]["t"] == "p" \
                        and re.search(r"\[[^\]]+\]\(#[^)]+\)\s*$", blocks[i + 1]["text"]):
                    term, d = blocks[i], blocks[i + 1]
                    o.add(f'<div class="gi"><dt>{inline(term["text"], ctx, term["line"])}</dt>'
                          f'<dd>{inline(d["text"], ctx, d["line"])}</dd></div>')
                    i += 2
                o.close_all()
                o.open("footer", '<footer class="band foot"><div class="wrap">')
                continue
            if lvl == 4 and text in ("Remember", "Common mistakes"):
                o.close_to("osp", "details")
                parts = []
                while i < n and blocks[i]["t"] == "h" and blocks[i]["level"] == 4 \
                        and blocks[i]["text"] in ("Remember", "Common mistakes"):
                    parts.append(f'<h4>{E(blocks[i]["text"])}</h4>')
                    i += 1
                    if i < n and blocks[i]["t"] in ("ul", "ol"):
                        parts.append(list_html(blocks[i], ctx))
                        i += 1
                o.add(f'<aside class="keep">{"".join(parts)}</aside>')
                continue
            if lvl == 3 and text == "Exercises":
                o.close_to("osp", "details", "ex", "exs")
                o.open("exs", '<div class="exs"><h3 class="exh">Exercises</h3>')
                i += 1
                continue
            # any other heading ends a system panel
            o.close_to("osp")
            if lvl == 3:
                m = re.match(r"^(\d+)(\D.*)$", text)
                if m and "section" in o.stack:
                    o.add(f'<h3 class="step" id="step-{m.group(1)}"><span class="sn">{m.group(1)}</span>'
                          f'{inline(m.group(2), ctx, b["line"])}</h3>')
                    i += 1
                    continue
            hid = slug(text)
            o.add(f'<h{lvl} id="{hid}">{inline(text, ctx, b["line"])}</h{lvl}>' if lvl <= 3
                  else f"<h{lvl}>{inline(text, ctx, b['line'])}</h{lvl}>")
            i += 1
            continue

        # ---------------- code
        if t == "code":
            o.add(code_figure(None, b["text"]))
            stats["plain"] += 1
            i += 1
            continue

        if t == "table":
            o.add(table_html(b, ctx))
            stats["tables"] += 1
            i += 1
            continue

        if t in ("ul", "ol"):
            o.add(list_html(b, ctx))
            i += 1
            continue

        # ---------------- paragraphs and the course's special lines
        text = b["text"]
        nb = nxt()

        if "header" in o.stack and DECK_RX.match(text):
            cards = []
            while i < n and blocks[i]["t"] == "p" and DECK_RX.match(blocks[i]["text"]):
                label, target = DECK_RX.match(blocks[i]["text"]).groups()
                top, _, rest = label.partition(": ")
                holes = "".join(f'<i data-h="{h}"></i>' for h in lesson_ex.get(target, []))
                cards.append(f'<a class="card" href="#{E(target)}" data-card="{E(target)}">'
                             f'<span class="cn">{E(top if rest else "")}</span>'
                             f'<span class="ct">{E(rest or top)}</span><span class="holes">{holes}</span></a>')
                i += 1
            o.add(f'<nav class="deck" aria-label="Lessons">{"".join(cards)}</nav>')
            for b2 in blocks[:i]:
                dm = b2["t"] == "p" and DECK_RX.match(b2["text"])
                if dm:
                    lab, tgt = dm.groups()
                    short[tgt] = lab.partition(": ")[2] or lab
            o.close_to("header")
            o.add("{{NAV}}")
            continue

        if re.fullmatch(r"\*\*\d+ of \d+ done\*\*", text):
            o.add(f'<p class="prog" aria-live="polite"><strong id="count">0 of {total_ex} done</strong>'
                  f'<span class="meter" aria-hidden="true"><i id="bar"></i></span>'
                  f'<button class="reset" id="reset" type="button">Reset progress</button></p>')
            i += 1
            continue

        if text == "A–Z" and nb and nb["t"] == "h" and nb["text"].lower() == "glossary":
            i += 1
            continue

        if text == "Your computer":
            btns = "".join(f'<button type="button" data-os="{k}" aria-pressed="false">{v}</button>'
                           for k, v in (("linux", "Linux"), ("windows", "Windows"), ("mac", "Mac")))
            o.add(f'<div class="ospick" role="group" aria-label="Your computer"><span>Your computer</span>{btns}</div>')
            i += 1
            continue

        if text in OS_LABELS:
            o.close_to("osp")
            o.open("osp", f'<div class="osp" data-for="{OS_LABELS[text]}"><span class="osl">{E(text)}</span>')
            stats["os_panels"] += 1
            i += 1
            continue

        m = EX_RX.match(text)
        if m and nb and nb["t"] == "h" and nb["level"] == 4:
            o.close_to("osp", "details", "ex")
            lesson = current_lesson(o, blocks, i)
            xid = ex_id(text, lesson)
            o.open("ex", f'<article class="ex" id="ex-{xid}"><header><div><span class="exn">{E(text)}</span>'
                         f'<h4>{inline(nb["text"], ctx, nb["line"])}</h4></div>'
                         f'<button class="done" type="button" data-ex="{xid}" aria-pressed="false">'
                         f'<span class="box"></span><span class="dl">Mark done</span></button></header>')
            stats["exercises"] += 1
            i += 2
            continue

        if text == "Hint" and "ex" in o.stack:
            o.close_to("details")
            o.open("details", '<details class="hint"><summary>Hint</summary>')
            i += 1
            continue

        if text in SOL_LABELS and "ex" in o.stack:
            o.close_to("details")
            o.open("details", f'<details class="sol"><summary>{E(text)}</summary>')
            i += 1
            continue

        if text == "Statement" and nb and nb["t"] == "p" and nb["text"] == "Screen afterwards":
            j, stmts, shown = i + 2, [], []
            while j + 1 < n and blocks[j]["t"] == "p" and TRACE_RX.match(blocks[j]["text"]):
                stmts.append(TRACE_RX.match(blocks[j]["text"]).group(2))
                shown.append(blocks[j + 1]["text"] if blocks[j + 1]["t"] == "p" else "")
                j += 2
            screens = simulate(stmts)
            if screens is None:
                ctx.warn(b["line"], "couldn't recompute the cursor walkthrough; using the exported text")
                screens = shown
            rows = "".join(f'<div class="st"><span class="tk">{k + 1}</span><code class="hl">{highlight_ada(st, numbered=False)}</code></div>'
                           f'<div class="sc">{E(sc)}<span class="cur"></span></div>'
                           for k, (st, sc) in enumerate(zip(stmts, screens)))
            o.add('<div class="trace"><div class="th">Statement</div><div class="th">Screen afterwards</div>'
                  f"{rows}</div>")
            i = j
            continue

        m = DIVIDE_RX.match(text)
        if m:
            q, d, r = int(m.group(1)), int(m.group(2)), int(m.group(3))
            groups = "".join('<span class="grp">' + "<i></i>" * d + "</span>" for _ in range(q))
            rest = '<span class="rest">' + "<i></i>" * r + "</span>" if r else ""
            o.add(f'<figure class="divv"><div class="dots">{groups}{rest}</div>'
                  f'<figcaption>{inline(text.replace("`**", "` · **"), ctx, b["line"])}</figcaption></figure>')
            i += 1
            continue

        if CODE_ONLY_RX.match(text):
            pairs, j = [], i
            while j + 1 < n and blocks[j]["t"] == "p" and CODE_ONLY_RX.match(blocks[j]["text"]) \
                    and blocks[j + 1]["t"] == "p" and not CODE_ONLY_RX.match(blocks[j + 1]["text"]):
                pairs.append((blocks[j], blocks[j + 1]))
                j += 2
            if len(pairs) >= 2:
                inner = ""
                for name, desc in reversed(pairs):
                    inner = (f'<div class="scope"><div class="sh">{inline(name["text"], ctx)}</div>'
                             f'<p>{inline(desc["text"], ctx, desc["line"])}</p>{inner}</div>')
                o.add(f'<figure class="scopes">{inner}</figure>')
                i = j
                continue
            if nb and nb["t"] == "ol":
                o.add(f'<p class="bigcode">{inline(text, ctx, b["line"])}</p>')
                i += 1
                continue

        if is_label(b) and nb and nb["t"] == "code":
            cap = text
            o.add(code_figure(cap, nb["text"], nb.get("marked")))
            kind = ("target" if cap.startswith("Target output")
                    else "terminal" if cap == "Terminal" and is_session(nb["text"])
                    else "code" if re.search(r"\.ad[bs]$", cap) else "shell")
            stats[kind] += 1
            if TYPED_ON in nb.get("marked", "") and kind in ("target", "terminal"):
                stats["typed"] += 1
            i += 2
            continue

        o.add(f'<p>{inline(text, ctx, b["line"])}</p>')
        i += 1

    o.close_all()
    body = "".join(o.parts)
    nav_html = ('<div class="navband"><nav class="nav" id="nav" aria-label="Jump to lesson">'
                + "".join(f'<a href="#{E(k)}">{E(k + " " + short.get(k, v) if k.isdigit() else short.get(k, v))}</a>'
                          for k, v in nav)
                + "</nav></div>")
    body = body.replace("{{NAV}}", nav_html, 1)
    stats.update(lessons=len(lesson_ex), exercises_expected=total_ex)
    return title or "Course", body, stats


def ex_id(label, lesson):
    m = re.match(r"^Exercise (\d+)\.(\d+)$", label)
    return f"{m.group(1)}-{m.group(2)}" if m else f"{lesson}-check"


def current_lesson(o, blocks, i):
    for k in range(i, -1, -1):
        b = blocks[k]
        if b["t"] == "h" and b["level"] == 1 and b["text"].isdigit():
            return b["text"]
    return "0"


def list_html(b, ctx):
    tag = b["t"]
    return f"<{tag}>" + "".join(f"<li>{inline(x, ctx, b['line'])}</li>" for x in b["items"]) + f"</{tag}>"


def table_html(b, ctx):
    head = b["head"]
    th = "".join(f"<th>{inline(h, ctx, b['line'])}</th>" for h in head)
    rows = []
    for r in b["rows"]:
        cells = []
        for k, c in enumerate(r):
            label = re.sub(r"<[^>]+>|`", "", head[k]) if k < len(head) else ""
            cells.append(f'<td data-l="{E(label)}"><span>{inline(c, ctx, b["line"])}</span></td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return f'<div class="scroll"><table class="stack"><thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'

# --------------------------------------------------------------------------- page

CSS = r"""
:root{color-scheme:light dark;--bg:light-dark(#ffffff,#1a1a19);--ink:light-dark(#111110,#ecece6);--mut:light-dark(#57574f,#a8a8a0);--plane:light-dark(#d8d8d4,#2f2f2c);--soft:light-dark(#f1f1ee,#232321);--rule:light-dark(#cfcfca,#3b3b38);--y:#ffe600;--hole:light-dark(#111110,#ecece6);--kw:light-dark(#111110,#ffffff);--str:light-dark(#7a5300,#e2c46c);--com:light-dark(#74746d,#8e8e87);--att:light-dark(#1c5d8a,#8cc2e8)}
:root[data-theme=light]{color-scheme:light}:root[data-theme=dark]{color-scheme:dark}
*{box-sizing:border-box;min-width:0}
html{scroll-padding-top:72px;-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:400 16.5px/1.6 "Hanken Grotesk",system-ui,sans-serif;overflow-x:clip}
a{color:var(--ink);text-decoration-thickness:1px;text-underline-offset:3px}
code,pre{font-family:"JetBrains Mono",ui-monospace,Menlo,Consolas,monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0}
code{font-size:.88em;overflow-wrap:anywhere}code.nw{white-space:nowrap}
.band{padding-block:clamp(28px,4vw,56px);padding-inline:max(5vw,16px)}
.wrap,.lw{max-width:1100px;margin-inline:auto}
h1{font-weight:700;font-size:clamp(34px,5vw,50px);line-height:1.05;letter-spacing:-.02em;margin:0 0 12px}
.top p{max-width:66ch;color:var(--mut)}
.prog{display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px}
.prog strong{font-size:20px;color:var(--ink)}
.meter{display:inline-block;width:200px;height:10px;background:var(--plane)}.meter i{display:block;height:100%;width:0;background:var(--ink);transition:width .3s}
.reset{font:inherit;font-size:14px;background:none;border:0;color:var(--mut);text-decoration:underline;cursor:pointer;min-height:44px}
.deck{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin-top:20px}
.card{display:grid;grid-template-rows:auto 1fr auto;gap:4px;min-height:108px;padding:12px 14px 12px 18px;background:var(--plane);color:var(--ink);text-decoration:none;clip-path:polygon(14px 0,100% 0,100% 100%,0 100%,0 14px)}
.card:hover{filter:brightness(.97)}.card.next{background:var(--y);color:#111110}
.cn{font-size:13px;opacity:.75}.ct{font-size:16px;font-weight:700;line-height:1.2}
.holes{display:flex;flex-wrap:wrap;gap:5px}.holes i{width:8px;height:15px;border-radius:2px;background:color-mix(in srgb,currentColor 16%,transparent)}
.holes i.p{background:var(--hole)}.card.next .holes i.p{background:#111110}
.navband{position:sticky;top:0;z-index:5;background:var(--bg);border-block:1px solid var(--rule)}
.nav{display:flex;gap:2px;overflow-x:auto;max-width:1100px;margin-inline:auto;padding-inline:max(5vw,16px)}
.nav a{flex:none;padding:12px 10px;font-size:14px;font-weight:500;text-decoration:none;white-space:nowrap;border-bottom:3px solid transparent}.nav a.on{border-bottom-color:var(--ink)}
.lesson{border-bottom:1px solid var(--rule)}
.lh{display:grid;grid-template-columns:auto minmax(0,1fr);gap:20px;align-items:start;margin-bottom:24px}
.badge{display:grid;place-items:center;min-width:58px;height:74px;padding:0 8px;background:var(--plane);font-size:26px;font-weight:700;clip-path:polygon(12px 0,100% 0,100% 100%,0 100%,0 12px)}
h2{font-size:clamp(30px,4vw,42px);line-height:1.05;letter-spacing:-.02em;margin:4px 0 8px}
.lead{margin:0;font-size:18px;color:var(--mut);max-width:62ch}
h3{font-size:21px;margin:32px 0 8px;line-height:1.2}h4{margin:18px 0 6px;font-size:18px}
.lw>p,.lw>ul,.lw>ol,.osp>p,.osp>ul,details>p{max-width:70ch}
.step{display:flex;align-items:center;gap:14px;margin-top:40px}
.sn{display:grid;place-items:center;flex:none;width:34px;height:42px;background:var(--plane);font-size:18px;clip-path:polygon(8px 0,100% 0,100% 100%,0 100%,0 8px)}
figure{margin:16px 0}
figcaption{display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:13px;padding-left:14px;min-height:38px}
.code{background:var(--soft);border:1px solid var(--rule)}
.code figcaption{border-bottom:1px solid var(--rule);font-family:"JetBrains Mono",monospace;color:var(--mut)}
.copy{font:500 13px "Hanken Grotesk",sans-serif;color:var(--ink);background:none;border:0;border-left:1px solid var(--rule);min-height:38px;min-width:64px;cursor:pointer}.copy:hover{background:var(--plane)}
pre{margin:0;padding:14px 16px;overflow-x:auto;font-size:14px;line-height:1.55;tab-size:8}
.code pre{counter-reset:ln}.ln{counter-increment:ln}
.ln::before{content:counter(ln);display:inline-block;width:2.2em;margin-right:12px;text-align:right;color:var(--com);opacity:.7;user-select:none}
pre b,.hl b{font-weight:400}pre b.k,.hl b.k{font-weight:700;color:var(--kw)}pre b.s,pre b.n,.hl b.s,.hl b.n{color:var(--str)}pre b.a,.hl b.a{color:var(--att)}pre i.c,.hl i.c{color:var(--com);font-style:normal}
.term{background:#121211;color:#e9e9e3;border:1px solid #121211}
.term figcaption{color:#9c9c95;border-bottom:1px solid #2c2c29}.goal figcaption span{color:#ffe600}
.term u{color:#fff;font-weight:700;text-decoration:underline 2px #ffe600;text-underline-offset:4px}
.term .pr{color:#8d8d86}.term .cm{color:#fff;font-weight:700}.term .err{color:#ff8a7a}.term .wrn{color:#f2c46b}
.scroll{overflow-x:auto;margin:16px 0}
table{border-collapse:collapse;width:100%;font-size:15px}
th,td{text-align:left;vertical-align:top;padding:9px 12px 9px 0;border-bottom:1px solid var(--rule)}th{border-bottom:2px solid var(--ink)}
td code{overflow-wrap:normal}
.keep{background:var(--soft);border:1px solid var(--rule);padding:6px 22px 14px;margin:28px 0;max-width:760px;font-size:15.5px}
.keep ul{padding-left:18px;margin:0}
.exs{margin-top:36px}.exh{font-size:24px}
.ex{border-top:2px solid var(--ink);padding:18px 0 22px}
.ex>header{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}.ex>header h4{margin:2px 0 0}
.exn{font-size:14px;color:var(--mut)}
.done{display:inline-flex;align-items:center;gap:10px;flex:none;font:500 15px "Hanken Grotesk",sans-serif;color:var(--ink);background:var(--bg);border:1.5px solid var(--ink);min-height:44px;padding:0 14px;cursor:pointer}
.done .box{width:10px;height:18px;border:1.5px solid currentColor}
.done[aria-pressed=true]{background:var(--ink);color:var(--bg)}.done[aria-pressed=true] .box{background:var(--y);border-color:var(--y)}
details{border:1px solid var(--rule);margin-top:10px}
summary{cursor:pointer;min-height:44px;display:flex;align-items:center;padding:0 14px;font-weight:700;list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"";border-left:7px solid currentColor;border-block:5px solid transparent;margin-right:10px;transition:transform .15s}
details[open]>summary::before{transform:rotate(90deg)}
details>*:not(summary){margin-left:14px;margin-right:14px}details>:last-child{margin-bottom:14px}
details.sol[open]{background:var(--soft)}
.ospick{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:22px 0 4px}.ospick span{font-weight:700;margin-right:6px}
.ospick button{font:500 16px "Hanken Grotesk",sans-serif;min-height:44px;padding:0 18px;border:1.5px solid var(--ink);background:var(--bg);color:var(--ink);cursor:pointer}
.ospick button[aria-pressed=true]{background:var(--ink);color:var(--bg)}
.osp{margin:14px 0;padding:2px 0 2px 16px;border-left:1px solid var(--rule)}.osl{display:block;font-size:14px;color:var(--mut);margin-top:8px}
:root[data-os] .osp{display:none}
:root[data-os=linux] .osp[data-for=linux],:root[data-os=windows] .osp[data-for=windows],:root[data-os=mac] .osp[data-for=mac]{display:block}
.trace{display:grid;grid-template-columns:minmax(0,15em) minmax(0,1fr);border:1px solid var(--rule);margin:18px 0;max-width:640px}
.trace .th{font-size:14px;font-weight:700;padding:8px 14px;background:var(--plane)}
.trace .st{display:flex;gap:12px;padding:10px 14px;border-top:1px solid var(--rule);background:var(--soft)}
.trace .st code{white-space:nowrap}.tk{flex:none;width:1.4em;color:var(--mut);font-size:14px}
.trace .sc{background:#121211;color:#e9e9e3;padding:10px 14px;border-top:1px solid #2c2c29;font:14px/1.5 "JetBrains Mono",monospace;white-space:pre;overflow-x:auto}
.cur{display:inline-block;width:.62em;height:1.2em;background:#ffe600;vertical-align:-.25em}
.divv{padding:18px;border:1px solid var(--rule);background:var(--soft);max-width:560px}
.dots{display:flex;flex-wrap:wrap;gap:14px}.grp{display:inline-flex;gap:6px;padding:8px 10px;border:1.5px solid var(--ink)}
.rest{display:inline-flex;gap:6px;padding:8px 10px;border:1.5px dashed var(--mut)}
.dots i{width:18px;height:18px;border-radius:50%;background:var(--ink)}.rest i{background:#ffe600;outline:1.5px solid #111110}
.divv figcaption{padding:14px 0 0;display:block;font-size:15px}
.scopes{max-width:620px}.scope{border:1.5px solid var(--ink);padding:10px 14px 14px}
.scope .scope{margin-top:10px;background:var(--soft)}.scope .scope .scope{background:var(--plane)}.scope p{margin:4px 0 0;font-size:15px}
.bigcode code{font-size:clamp(18px,3vw,26px)}
.gloss{background:var(--soft)}.glist{columns:2 340px;column-gap:48px;margin:0}
.gi{break-inside:avoid;padding:10px 0;border-top:1px solid var(--rule)}.gi dt{font-weight:700}.gi dd{margin:2px 0 0;font-size:15.5px}
.foot{color:var(--mut);font-size:15px}.foot p{max-width:72ch}
:focus-visible{outline:3px solid var(--ink);outline-offset:2px}
@media(max-width:600px){body{font-size:16px}pre{font-size:13px;padding:12px}.lh{grid-template-columns:minmax(0,1fr)}.badge{display:none}
.ex>header{flex-direction:column}.trace{grid-template-columns:minmax(0,1fr)}.trace .th:nth-child(2){display:none}
.deck{grid-template-columns:repeat(2,minmax(0,1fr))}.card{min-height:72px}
table{font-size:14px}.stack thead{display:none}.stack tr{display:grid;padding-block:8px;border-bottom:1px solid var(--rule)}
.stack td{display:grid;grid-template-columns:6.5em minmax(0,1fr);gap:10px;border:0;padding:3px 0}.stack td::before{content:attr(data-l);color:var(--mut);font-size:13px}}
@media(prefers-reduced-motion:reduce){*{transition:none!important}}
"""

JS = r"""
{
  const KEY = "ada2022-md-done", OSKEY = "ada2022-md-os";
  let done = new Set();
  try { done = new Set(JSON.parse(localStorage.getItem(KEY) || "[]")); } catch (e) {}
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify([...done])); } catch (e) {} };
  const buttons = [...document.querySelectorAll(".done")];
  const render = () => {
    for (const b of buttons) {
      const on = done.has(b.dataset.ex);
      b.setAttribute("aria-pressed", on);
      b.querySelector(".dl").textContent = on ? "Done" : "Mark done";
    }
    for (const h of document.querySelectorAll(".holes i")) h.classList.toggle("p", done.has(h.dataset.h));
    let marked = false;
    for (const c of document.querySelectorAll(".card")) {
      const holes = [...c.querySelectorAll(".holes i")];
      const open = holes.length && !holes.every(h => done.has(h.dataset.h));
      c.classList.toggle("next", !!open && !marked);
      if (open && !marked) marked = true;
    }
    const n = buttons.filter(b => done.has(b.dataset.ex)).length;
    const count = document.getElementById("count"), bar = document.getElementById("bar");
    if (count) count.textContent = n + " of " + buttons.length + " done";
    if (bar) bar.style.width = (buttons.length ? 100 * n / buttons.length : 0) + "%";
  };
  for (const b of buttons) b.addEventListener("click", () => {
    done.has(b.dataset.ex) ? done.delete(b.dataset.ex) : done.add(b.dataset.ex); save(); render();
  });
  const reset = document.getElementById("reset");
  if (reset) {
    let armed = false;
    reset.addEventListener("click", () => {
      if (!armed) { armed = true; reset.textContent = "Click again to clear all ticks";
        setTimeout(() => { armed = false; reset.textContent = "Reset progress"; }, 4000); return; }
      armed = false; done.clear(); save(); render(); reset.textContent = "Reset progress";
    });
  }
  for (const c of document.querySelectorAll(".copy")) c.addEventListener("click", async () => {
    const pre = document.getElementById(c.dataset.copy);
    try { await navigator.clipboard.writeText(pre.innerText.replace(/\n$/, "")); c.textContent = "Copied"; }
    catch (e) { const r = document.createRange(); r.selectNodeContents(pre);
      const s = getSelection(); s.removeAllRanges(); s.addRange(r); c.textContent = "Selected"; }
    setTimeout(() => { c.textContent = "Copy"; }, 1600);
  });
  const setOS = os => {
    document.documentElement.dataset.os = os;
    for (const b of document.querySelectorAll(".ospick button")) b.setAttribute("aria-pressed", b.dataset.os === os);
    try { localStorage.setItem(OSKEY, os); } catch (e) {}
  };
  if (document.querySelector(".ospick")) {
    let os = null;
    try { os = localStorage.getItem(OSKEY); } catch (e) {}
    if (!os) {
      const ua = navigator.userAgent || "", pf = (navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || ua;
      os = /win/i.test(pf) ? "windows" : (/mac/i.test(pf) && !/iphone|ipad/i.test(ua)) ? "mac" : "linux";
    }
    for (const b of document.querySelectorAll(".ospick button")) b.addEventListener("click", () => setOS(b.dataset.os));
    setOS(os);
  }
  const nav = document.getElementById("nav");
  if (nav && "IntersectionObserver" in window) {
    const links = new Map([...nav.querySelectorAll("a")].map(a => [a.getAttribute("href").slice(1), a]));
    const spy = new IntersectionObserver(es => { for (const e of es) if (e.isIntersecting) {
      for (const a of links.values()) a.classList.remove("on");
      const a = links.get(e.target.id);
      if (a) { a.classList.add("on"); nav.scrollLeft = a.offsetLeft - nav.clientWidth / 2 + a.offsetWidth / 2; }
    } }, { rootMargin: "-45% 0px -50% 0px" });
    for (const s of document.querySelectorAll("section[id]")) spy.observe(s);
  }
  render();
}
"""

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>
{body}
<script>{js}</script>
</body>
</html>
"""

# --------------------------------------------------------------------------- checks and CLI

class Balance(HTMLParser):
    VOID = {"meta", "link", "br", "img", "input", "hr", "col", "source", "wbr"}

    def __init__(self):
        super().__init__()
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors.append(f"</{tag}> doesn't close <{self.stack[-1] if self.stack else 'nothing'}>")
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass


def build(src, dst, quiet=False):
    text = open(src, encoding="utf-8").read()
    ctx = Ctx()
    Ids.n = 0
    title, body, stats = render(parse_blocks(text), ctx)
    page = PAGE.format(title=E(title), css=CSS, js=JS, body=body)
    chk = Balance()
    chk.feed(page)
    problems = ctx.warnings + [f"HTML: {e}" for e in chk.errors[:5]]
    if chk.stack:
        problems.append(f"HTML: unclosed tags at end: {chk.stack[-5:]}")
    if stats["exercises"] != stats["exercises_expected"]:
        problems.append(f"found {stats['exercises']} exercise cards but counted {stats['exercises_expected']}")
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(page)
    if not quiet:
        print(f"{src} -> {dst}  ({len(page):,} bytes)")
        print(f"  {stats['lessons']} lessons, {stats['exercises']} exercises, {stats['code']} Ada files, "
              f"{stats['plain']} unlabelled code blocks, "
              f"{stats['terminal']} terminals, {stats['target']} target outputs, "
              f"{stats['typed']} boxes with typed input underlined, {stats['shell']} shell boxes, "
              f"{stats['tables']} tables, {stats['os_panels']} system panels")
        print("  warnings:" if problems else "  no warnings")
        for p in problems:
            print("   -", p)
    return not problems


def main():
    ap = argparse.ArgumentParser(description="Convert the Ada 2022 from Zero markdown export to HTML.")
    ap.add_argument("input", help="the .md file")
    ap.add_argument("-o", "--output", help="the .html file to write (default: next to the input)")
    ap.add_argument("--watch", action="store_true", help="rebuild whenever the .md file is saved")
    a = ap.parse_args()
    dst = a.output or os.path.splitext(a.input)[0] + ".html"
    ok = build(a.input, dst)
    if not a.watch:
        sys.exit(0 if ok else 1)
    print("watching for changes (Ctrl+C to stop)")
    last = os.path.getmtime(a.input)
    try:
        while True:
            time.sleep(0.5)
            m = os.path.getmtime(a.input)
            if m != last:
                last = m
                print(time.strftime("%H:%M:%S"), end=" ")
                try:
                    build(a.input, dst)
                except Exception as e:  # keep watching after a bad save
                    print("build failed:", e)
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
