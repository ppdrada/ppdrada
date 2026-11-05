"""Rewrite the tech stack and latest-repos blocks of README.md from the GitHub repos JSON."""
import collections, json, os, pathlib, re, sys, urllib.error, urllib.request

SKIP = {"ppdrada"}  # repos that never show up
LIMIT = 5           # cards in "latest things i built"
LANGS = 6           # languages after the fixed tools

FIXED = [("Windows", "assets/windows.svg"), ("macOS", "apple"), ("Linux", "linux"), ("Git", "git")]
# GitHub language -> simple-icons slug, or a local asset when simple-icons has none
ICONS = {
    "Python": "python", "JavaScript": "javascript", "TypeScript": "typescript", "Java": "openjdk",
    "Shell": "gnubash", "Swift": "swift", "HTML": "html5", "CSS": "css", "C": "c", "C++": "cplusplus",
    "Go": "go", "Rust": "rust", "PHP": "php", "Kotlin": "kotlin", "Dart": "dart", "Ruby": "ruby",
    "Lua": "lua", "Jupyter Notebook": "jupyter", "Dockerfile": "docker",
    "TSQL": "assets/sql.svg", "PLSQL": "assets/sql.svg", "PLpgSQL": "postgresql",
}

CARD = """<svg xmlns="http://www.w3.org/2000/svg" width="160" height="58" viewBox="0 0 160 58" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">
<rect x="0.5" y="0.5" width="159" height="57" rx="8" fill="#111111" stroke="#2A2A2A"/>
<text x="14" y="25" fill="#EDEDED" font-size="13" font-weight="600">{name}</text>
<circle cx="18" cy="40" r="4" fill="#8C8C8C"/>
<text x="27" y="44" fill="#A6A6A6" font-size="11">{lang}</text>
</svg>
"""


def icon(alt, src):
    url = src if src.startswith("assets/") else f"https://cdn.simpleicons.org/{src}/BFBFBF"
    return f'<img src="{url}" height="34" alt="{alt}" />'


def skills_block(repos):
    counts = collections.Counter(r["language"] for r in repos if r["language"] in ICONS)
    langs = [l for l, _ in counts.most_common(LANGS)]
    return "&nbsp;&nbsp;\n".join(icon(a, s) for a, s in FIXED + [(l, ICONS[l]) for l in langs])


def repos_block(repos, owner, assets):
    for old in assets.glob("repo-*.svg"):
        old.unlink()
    cards = []
    for r in repos[:LIMIT]:
        name, lang = r["name"], (r["language"] or "").lower()
        (assets / f"repo-{name}.svg").write_text(CARD.format(name=name, lang=lang), encoding="utf-8")
        cards.append(f'<a href="https://github.com/{owner}/{name}"><img src="assets/repo-{name}.svg" width="18%" alt="{name} · {lang}" /></a>')
    return "&nbsp;".join(cards)


def last_commit(owner, repo):
    # pushed_at also moves when bots (dependabot) touch a repo, so sort by the real last commit instead
    url = f"https://api.github.com/repos/{owner}/{repo['name']}/commits?per_page=1&sha={repo['default_branch']}"
    headers = {"Authorization": f"Bearer {os.environ['GH_TOKEN']}"} if os.environ.get("GH_TOKEN") else {}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as res:
            commits = json.load(res)
    except urllib.error.HTTPError as e:
        if e.code == 409:  # empty repo
            return ""
        raise
    return commits[0]["commit"]["committer"]["date"] if commits else ""


def replace(text, marker, body):
    pat = re.compile(rf"(<!-- {marker}:start -->\n).*?(\n<!-- {marker}:end -->)", re.S)
    assert pat.search(text), f"marker {marker} missing from README"
    return pat.sub(lambda m: m.group(1) + body + m.group(2), text)


def main(json_path, owner, root="."):
    root = pathlib.Path(root)
    repos = [r for r in json.loads(pathlib.Path(json_path).read_text(encoding="utf-8"))
             if not r["fork"] and r["name"] not in SKIP]
    repos.sort(key=lambda r: last_commit(owner, r), reverse=True)
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    text = replace(text, "skills", skills_block(repos))
    text = replace(text, "repos", repos_block(repos, owner, root / "assets"))
    readme.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
