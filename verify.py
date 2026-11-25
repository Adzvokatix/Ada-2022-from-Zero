#!/usr/bin/env python3
"""Run every program in a course volume and check the markdown tells the truth.

    python3 verify.py volume-2/README.md            check: report any terminal that differs
    python3 verify.py volume-2/README.md --update   rewrite terminals with what really printed
    python3 verify.py volume-2/README.md --lesson 2 only lesson 2

How it reads the markdown, top to bottom, the way a student works through it:

  * "# N" starts lesson N in a fresh, empty folder. If the markdown has
    <!-- verify: lesson-folder ~/ada-course-2/lesson-{n} -->, that is the
    folder's name, under a stand-in home folder, so "~" works in commands.
  * "$ cd somewhere" changes folder for the boxes that follow, as in a
    real terminal. Files are saved relative to the current folder.
  * A caption that is a file name ("hello.adb", "src/greet.ads", "notes.txt")
    followed by a code block saves that block as that file, replacing any
    earlier version, just as the student would.
  * A "Terminal" box whose lines start with "$ " is a session. Each "$ " line
    is run with bash in the lesson folder, inside a real terminal (pty), and
    what it prints must match the lines under it. Text inside <ins>…</ins> is
    what the user typed: it is fed to the program as one line. <ins></ins> is
    a bare Enter.
  * A "Target output" box is checked once its exercise ends, so the solution's
    files exist by then. Its commands run the same way.
  * Put <!-- verify: skip --> on the line before a box to leave it unchecked
    (install commands, version checks, random output). A reason may follow:
    <!-- verify: skip (the secret number is random) -->.

Needs only Python 3 and the commands the course uses (gnatmake, gprbuild).
Exits 1 if anything differs, so it can gate a build.
"""
import argparse, difflib, html, os, pty, re, select, subprocess, sys, tempfile, time

FILE_CAPTION = re.compile(r"^[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*\.[A-Za-z0-9]+$")
EXERCISE = re.compile(r"^(Exercise \d+\.\d+|Checkpoint)$")
INS = re.compile(r"<ins>(.*?)</ins>")


# ---------------------------------------------------------------- running

def run_session(cmd, cwd, inputs, home, timeout=30):
    """Run one command in a pty, typing each input when the program goes quiet.
    Returns everything the terminal showed, typed echo included."""
    master, slave = pty.openpty()
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": home, "TERM": "dumb", "LANG": "C.UTF-8"}
    p = subprocess.Popen(["bash", "-c", cmd], cwd=cwd, stdin=slave, stdout=slave, stderr=slave,
                         env=env, start_new_session=True)
    os.close(slave)
    out, queue, deadline = b"", list(inputs), time.time() + timeout

    def read(idle):
        """Read until the program is quiet for `idle` seconds (False) or exits (True)."""
        nonlocal out
        while True:
            r, _, _ = select.select([master], [], [], idle)
            if not r:
                return False
            try:
                data = os.read(master, 4096)
            except OSError:
                return True
            if not data:
                return True
            out += data

    while True:
        if queue:
            if read(0.4):
                break
            os.write(master, (queue.pop(0) + "\n").encode())
        else:
            if read(max(1, deadline - time.time())):
                break
            p.kill()
            out += b"\n[verify: timed out]\n"
            break
    os.close(master)
    p.wait()
    out = out.decode("utf-8", "replace").replace("\r\n", "\n")
    # "bash -c" words its own errors as "bash: line 1: …"; a terminal says "bash: …"
    return re.sub(r"^bash: line \d+: ", "bash: ", out, flags=re.M)


def mark_typed(out, inputs):
    """Wrap each typed input (as echoed by the terminal) in <ins>, escaping the rest."""
    parts, pos, owned = [], 0, False
    for inp in inputs:
        start = pos + 1 if owned else pos     # step past the previous answer's own Enter
        j = out.find(inp + "\n", start) if inp else out.find("\n", start)
        if j < 0:
            continue                          # program ended before reading it
        parts.append(html.escape(out[pos:j], quote=False))
        parts.append(f"<ins>{html.escape(inp, quote=False)}</ins>")
        pos, owned = j + len(inp), True
    parts.append(html.escape(out[pos:], quote=False))
    return "".join(parts)


# ---------------------------------------------------------------- reading the markdown

def find_box(lines, i):
    """If a code box starts at line i (``` or <pre>), return (start, end, body, is_pre)."""
    if lines[i].startswith("```"):
        j = i + 1
        while j < len(lines) and not lines[j].startswith("```"):
            j += 1
        return i, j, "\n".join(lines[i + 1:j]), False
    if lines[i].strip() == "<pre>":
        j = i + 1
        while j < len(lines) and lines[j].strip() != "</pre>":
            j += 1
        return i, j, "\n".join(lines[i + 1:j]), True
    return None


def session_steps(body, is_pre):
    """Split a terminal body into [(command, expected_output, inputs)]."""
    steps, cur = [], None
    for line in body.split("\n"):
        plain = html.unescape(re.sub(r"</?ins>", "", line)) if is_pre else line
        if plain.startswith("$ "):
            cur = [plain[2:], [], []]
            steps.append(cur)
        elif cur is not None:
            cur[1].append(line)
            if is_pre:
                cur[2].extend(html.unescape(x) for x in INS.findall(line))
    return [(c, "\n".join(o), ins) for c, o, ins in steps]


def render_box(steps_out, any_typed):
    """Lines for a box holding the real session."""
    body = []
    for cmd, marked in steps_out:
        body.append("$ " + (html.escape(cmd, quote=False) if any_typed else cmd))
        if marked:
            body.append(marked if any_typed else html.unescape(marked))
    if any_typed:
        return ["<pre>", *"\n".join(body).split("\n"), "</pre>"]
    return ["```", *"\n".join(body).split("\n"), "```"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("markdown")
    ap.add_argument("--update", action="store_true", help="rewrite each box with the real output")
    ap.add_argument("--lesson", type=int, help="only check this lesson")
    a = ap.parse_args()

    lines = open(a.markdown, encoding="utf-8").read().split("\n")
    root = tempfile.mkdtemp(prefix="verify-")
    home = os.path.join(root, "home")
    work = os.path.join(root, "front")
    os.makedirs(work)
    os.makedirs(home)
    folder_rule = None
    for l in lines:
        m = re.match(r"^<!-- verify: lesson-folder (\S+) -->$", l.strip())
        if m:
            folder_rule = m.group(1)

    def expand(path, cwd):
        if path == "~" or path.startswith("~/"):
            path = home + path[1:]
        return os.path.normpath(os.path.join(cwd, path))
    lesson = None
    pending = []          # target-output boxes waiting for their exercise to end
    edits = {}            # (start, end) -> new lines
    checked = differ = files = 0
    report = []

    def active():
        return a.lesson is None or lesson == a.lesson

    def check(start, end, body, is_pre, caption):
        nonlocal checked, differ, work
        steps = session_steps(body, is_pre)
        got, any_typed = [], False
        for cmd, _, inputs in steps:
            m = re.match(r"^cd(?:\s+(\S+))?\s*$", cmd)
            if m:
                target = expand(m.group(1) or "~", work)
                if os.path.isdir(target):
                    work, out = target, ""
                else:   # let bash word the error
                    out = run_session(cmd, work, [], home).rstrip("\n")
            else:
                out = run_session(cmd, work, inputs, home).rstrip("\n")
            marked = mark_typed(out, inputs) if inputs else html.escape(out, quote=False)
            any_typed |= bool(inputs)
            got.append((cmd, marked))
        new = render_box(got, any_typed)
        old = lines[start:end + 1]
        checked += 1
        if new != old:
            differ += 1
            where = f"line {start + 1} (lesson {lesson}, {caption})"
            diff = difflib.unified_diff(old, new, "markdown", "real run", lineterm="", n=1)
            report.append(where + "\n" + "\n".join(list(diff)[2:]))
            edits[(start, end)] = new

    def flush():
        while pending:
            check(*pending.pop(0))

    prev_text = None      # last non-blank line before the current one
    skip_next = False
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^# (\d+)\s*$", line)
        if m:
            flush()
            lesson = int(m.group(1))
            work = (expand(folder_rule.replace("{n}", str(lesson)), home) if folder_rule
                    else os.path.join(root, f"lesson-{lesson}"))
            os.makedirs(work, exist_ok=True)
        elif EXERCISE.match(line.strip()) or re.match(r"^#{1,3} ", line):
            flush()
        if re.match(r"^<!-- verify: skip\b.*-->$", line.strip()):
            skip_next = True
            i += 1
            continue
        box = find_box(lines, i)
        if box:
            start, end, body, is_pre = box
            caption = prev_text or ""
            if skip_next or not active():
                pass
            elif FILE_CAPTION.match(caption) and not is_pre:
                path = os.path.join(work, caption)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                if os.path.exists(path):
                    # GNAT counts a source as unchanged if its time stamp is within 2 seconds
                    # of the one it compiled. A student takes longer than that to edit a
                    # file; the checker must too.
                    wait = os.stat(path).st_mtime + 3.1 - time.time()
                    if wait > 0:
                        time.sleep(wait)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(body + "\n")
                files += 1
            elif caption == "Terminal" and re.search(r"^\$ ", html.unescape(re.sub(r"</?ins>", "", body)), re.M):
                check(start, end, body, is_pre, caption)
            elif caption.startswith("Target output"):
                pending.append((start, end, body, is_pre, caption))
            skip_next = False
            prev_text = None
            i = end + 1
            continue
        if line.strip():
            prev_text = line.strip()
        i += 1
    flush()

    print(f"{a.markdown}: {files} files saved, {checked} terminal boxes run, {differ} differ")
    print(f"  lesson folders kept in {home if folder_rule else root}")
    for r in report:
        print("\n" + r)
    if a.update and edits:
        out, k = [], 0
        for (s, e), new in sorted(edits.items()):
            out += lines[k:s] + new
            k = e + 1
        out += lines[k:]
        open(a.markdown, "w", encoding="utf-8").write("\n".join(out))
        print(f"\nupdated {len(edits)} boxes in {a.markdown}")
        return 0
    return 1 if differ else 0


if __name__ == "__main__":
    sys.exit(main())
