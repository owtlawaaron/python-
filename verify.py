#!/usr/bin/env python3
"""
pydrill のデータ検証ツール。

HTML に埋め込まれた 3 つのデータ配列を取り出し、
「宣言されている出力」と「実際に Python を実行した出力」が
一致するかを全件照合する。

    python3 verify.py                     # pydrill-pro.html を検証
    python3 verify.py pydrill.html        # ファイル指定

問題を 1 問足したら必ず通すこと。LLM は型と符号を平気で間違える
（9 ** 0.5 は 3 ではなく 3.0、-7 // 2 は -3 ではなく -4）。
間違った出力を載せた教材は、間違いを覚えさせる。
"""
import sys, io, json, re, contextlib, pathlib

# ────────────────────────── JS リテラル → JSON ──────────────────────────
def _unescape(body):
    """JS 文字列リテラルの中身を Python の文字列に戻す。"""
    out, i = [], 0
    tbl = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f",
           "\\": "\\", "'": "'", '"': '"', "/": "/", "`": "`", "\n": ""}
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            nx = body[i + 1]
            if nx == "u":
                out.append(chr(int(body[i + 2:i + 6], 16))); i += 6; continue
            out.append(tbl.get(nx, nx)); i += 2; continue
        out.append(c); i += 1
    return "".join(out)


def js_to_json(s):
    """QUESTIONS のような JS オブジェクトリテラルを JSON 文字列に直す。

    いったん「文字列」と「それ以外」のトークン列に分解してから組み立てる。
    こうしないと引用符の対応を取り違える（"a"+"b" の連結を、
    直前のキーの閉じ引用符から数えてしまう事故が起きる）。
    """
    toks, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c in "\"'":                                   # 文字列
            q, i, buf = c, i + 1, []
            while i < n and s[i] != q:
                if s[i] == "\\":
                    buf.append(s[i:i + 2]); i += 2; continue
                buf.append(s[i]); i += 1
            i += 1
            toks.append(("s", _unescape("".join(buf))))
            continue
        if c == "/" and s[i + 1:i + 2] == "*":           # ブロックコメント
            i = s.index("*/", i) + 2; continue
        if c == "/" and s[i + 1:i + 2] == "/":           # 行コメント
            j = s.find("\n", i); i = n if j < 0 else j; continue
        m = re.match(r"([A-Za-z_$][\w$]*)\s*:", s[i:])   # 素のキー
        if m and (not toks or (toks[-1][0] == "r" and toks[-1][1].rstrip()[-1:] in "{,[")):
            toks.append(("s", m.group(1)))
            toks.append(("r", ":")); i += m.end(); continue
        toks.append(("r", c)); i += 1

    # 隣り合う r トークンをまとめる
    merged = []
    for t, v in toks:
        if t == "r" and merged and merged[-1][0] == "r":
            merged[-1] = ("r", merged[-1][1] + v)
        else:
            merged.append((t, v))

    # 文字列 + 文字列 の連結をたたむ
    out = []
    for t, v in merged:
        if (t == "s" and len(out) >= 2 and out[-1][0] == "r"
                and out[-1][1].strip() == "+" and out[-2][0] == "s"):
            out.pop()
            out[-1] = ("s", out[-1][1] + v)
            continue
        out.append((t, v))

    txt = "".join(json.dumps(v, ensure_ascii=False) if t == "s" else v for t, v in out)
    return re.sub(r",(\s*[}\]])", r"\1", txt)          # 末尾カンマ


def extract(text, name):
    """const NAME=[ ... ] / var NAME=[ ... ] を括弧の対応で切り出す。

    pyblock.html は ES5 で書く決まりなので var も受ける。
    """
    k = text.find("const %s=" % name)
    if k < 0:
        k = text.find("var %s=" % name)
    if k < 0:
        return None
    start = text.index("[", k)
    depth, i, in_s, q = 0, start, False, ""
    while i < len(text):
        c = text[i]
        if in_s:
            if c == "\\": i += 2; continue
            if c == q: in_s = False
        elif c in "\"'`":
            in_s, q = True, c
        elif c in "[{":
            depth += 1
        elif c in "]}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1
    raise ValueError("括弧が閉じていない: " + name)


# ────────────────────────── 実行 ──────────────────────────
def run(code, stdin=""):
    """コードを実行して (出力, 例外テキスト or None) を返す。"""
    buf, real = io.StringIO(), sys.stdin
    try:
        sys.stdin = io.StringIO(stdin + "\n" if stdin else "")
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            exec(compile(code, "code.py", "exec"), {"__name__": "__main__"})
        return buf.getvalue().rstrip("\n"), None
    except BaseException as e:
        return buf.getvalue().rstrip("\n"), "%s: %s" % (type(e).__name__, e)
    finally:
        sys.stdin = real


def norm(s):
    """行末の空白と前後の空行を無視して比べる（採点側と同じ規則）。"""
    return "\n".join(l.rstrip() for l in str(s).replace("\r", "").split("\n")).strip("\n")


KW = {"if", "in", "for", "while", "return", "else", "and", "or", "not", "is", "import", "elif"}

def is_name(t):
    return (re.fullmatch(r"[A-Za-z_][\w.]*", t) and t not in KW) or re.search(r"[)\]'\"]$", t)

def join_code(ts):
    """トークン列 → 表示用のコード。アプリ側の joinCode と同じ規則。"""
    s = ""
    for i, t in enumerate(ts):
        if i:
            p = ts[i - 1]
            tight = (t in (")", "]", ",", ":")
                     or (t in ("(", "[") and is_name(p))
                     or p in ("(", "["))
            if not tight:
                s += " "
        s += t
    return s


# ────────────────────────── 検証 ──────────────────────────
SLOT = "▁"
fails, checks = [], 0

def fail(where, expected, got, extra=""):
    fails.append("%s\n    期待 = %r\n    実際 = %r%s" % (where, expected, got, extra))


def check_questions(qs):
    """組み立て型と出力予測型。"""
    global checks
    seen = set()
    for q in qs:
        qid, t = q["id"], q.get("type", "build")
        if qid in seen:
            fails.append("id 重複: " + qid)
        seen.add(qid)

        if t == "predict":
            checks += 1
            if q["choices"][q["ans"]] != q["out"]:
                fail("predict %s / 正解の選択肢が out と違う" % qid, q["out"], q["choices"][q["ans"]])
            got, err = run("\n".join(q["code"]))
            if err or norm(got) != norm(q["out"]):
                fail("predict %s / 実行結果" % qid, q["out"], err or got)
            continue

        # まぎれチップが正解トークンと衝突していないか
        dup = set(q.get("extra", [])) & set(q["tokens"])
        if dup:
            fails.append("build %s / extra が tokens と衝突: %s" % (qid, sorted(dup)))

        built = join_code(q["tokens"])
        ctx = q.get("ctx")
        if isinstance(ctx, list):
            if sum(SLOT in l for l in ctx) != 1:
                fails.append("build %s / ctx の ▁ がちょうど1個でない" % qid)
                continue
            checks += 1
            prog = "\n".join(l.replace(SLOT, built) for l in ctx)
            got, err = run(prog)
            exp = q.get("out") or ""
            if err or norm(got) != norm(exp):
                fail("build %s / 組み立てたプログラムの出力" % qid, exp, err or got,
                     "\n    コード =\n" + "\n".join("      " + l for l in prog.split("\n")))
        else:
            # 前提が文字列だけ / なし → 構文が通ることだけ確認
            checks += 1
            src = ((ctx + "\n") if isinstance(ctx, str) and ctx else "") + built
            if built.rstrip().endswith(":"):
                src += "\n    pass"
            try:
                compile(src, "code.py", "exec")
            except SyntaxError as e:
                fail("build %s / 構文が通らない" % qid, "構文OK", "%s: %s" % (type(e).__name__, e),
                     "\n    コード = " + src.replace("\n", " ; "))


def check_dict(d):
    global checks
    ids = [it["id"] for cat in d for it in cat["items"]]
    if len(ids) != len(set(ids)):
        fails.append("辞書の id が重複している")
    for cat in d:
        for it in cat["items"]:
            for v in it["v"]:
                checks += 1
                got, err = run(v["c"], v.get("i", ""))
                if err or norm(got) != norm(v["o"]):
                    fail("dict %s / %s" % (it["id"], v["l"]), v["o"], err or got)


def check_errors(es):
    """エラー辞書。宣言したエラーが本当にそのエラーで出るか、直した形が本当に直るか。

    メッセージは「含まれるか」で見る。Python のバージョンが上がると
    「Did you mean:」のような補足が末尾に足されることがあるため。
    型は完全一致で見る（ここが違ったら別のエラーを教えていることになる）。
    """
    global checks
    seen = set()
    for e in es:
        eid = e["id"]
        if eid in seen:
            fails.append("エラー辞書の id 重複: " + eid)
        seen.add(eid)

        checks += 1
        out, err = run(e["bad"], e.get("bi", ""))
        if not err:
            fail("error %s / 壊れた形が例外を出さない" % eid,
                 e["err"] + ": " + e["msg"], out or "(出力なし)")
        else:
            got_type = err.split(":", 1)[0]
            if got_type != e["err"]:
                fail("error %s / 例外の型" % eid, e["err"], got_type,
                     "\n    実際の全文 = " + err)
            elif e["msg"] not in err:
                fail("error %s / 例外の文言" % eid, e["msg"], err)

        checks += 1
        out, err = run(e["fix"], e.get("fi", ""))
        if err or norm(out) != norm(e["fo"]):
            fail("error %s / 直した形の出力" % eid, e["fo"], err or out)


def check_write(ws):
    global checks
    for w in ws:
        checks += 1
        got, err = run(w["m"], w.get("in", ""))
        if err or norm(got) != norm(w["o"]):
            fail("write %s / 模範解答の出力" % w["id"], w["o"], err or got)
        st = w.get("st", "")
        if st and not w["m"].startswith(st.rstrip("\n")):
            fails.append("write %s / スターターが模範解答の先頭と一致しない" % w["id"])


def check_tasks(ts):
    """お題。模範解答が本当にその出力になるか。

    お題は「この出力になるように組め」なので、期待する出力が
    実際に到達可能でなければ、解けない問題を出していることになる。
    """
    global checks
    seen = set()
    for t in ts:
        if t["id"] in seen:
            fails.append("お題の id 重複: " + t["id"])
        seen.add(t["id"])
        checks += 1
        got, err = run(t["m"], t.get("i", ""))
        if err or norm(got) != norm(t["o"]):
            fail("task %s / 模範解答の出力" % t["id"], t["o"], err or got)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "pydrill-pro.html"
    path = pathlib.Path(target)
    if not path.exists():
        print("ファイルが見つかりません: %s" % target); return 2
    text = path.read_text(encoding="utf-8")

    print("検証対象: %s" % path.name)

    raw = extract(text, "QUESTIONS")
    if raw:
        raw = re.sub(r"\bSLOT\b", "'" + SLOT + "'", raw)   # 定数を実体に
        qs = json.loads(js_to_json(raw))
        print("  QUESTIONS %d 問" % len(qs)); check_questions(qs)

    raw = extract(text, "DICT")
    if raw:
        d = json.loads(raw)
        n = sum(len(it["v"]) for cat in d for it in cat["items"])
        print("  DICT %d 見出し / %d パターン"
              % (sum(len(c["items"]) for c in d), n)); check_dict(d)

    raw = extract(text, "ATOMS")
    if raw:
        a = json.loads(raw)
        n = sum(len(it["v"]) for cat in a for it in cat["items"])
        print("  ATOMS %d 原子 / %d 例"
              % (sum(len(c["items"]) for c in a), n))
        check_dict(a)          # 形が DICT と同じなので同じ検査をそのまま通す

    raw = extract(text, "ERRORS")
    if raw:
        es = json.loads(raw)
        print("  ERRORS %d 件" % len(es)); check_errors(es)

    raw = extract(text, "WRITE")
    if raw:
        ws = json.loads(raw)
        print("  WRITE %d 問" % len(ws)); check_write(ws)

    raw = extract(text, "BDICT")
    if raw:
        d = json.loads(raw)
        n = sum(len(it["v"]) for cat in d for it in cat["items"])
        print("  BDICT %d ブロック / %d 例"
              % (sum(len(c["items"]) for c in d), n))
        check_dict(d)          # 形が DICT と同じなので同じ検査をそのまま通す

    raw = extract(text, "TASKS")
    if raw:
        ts = json.loads(raw)
        print("  TASKS %d 題" % len(ts)); check_tasks(ts)

    print("\n%d 件を実行照合" % checks)
    if fails:
        print("--- 不一致 %d 件 ---" % len(fails))
        for f in fails:
            print("\n" + f)
        return 1
    print("すべて一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
