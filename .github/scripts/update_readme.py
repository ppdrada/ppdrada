"""Rewrite the tech stack and latest-repos blocks of README.md from the GitHub repos JSON."""
import collections, json, os, pathlib, re, sys, urllib.error, urllib.request

SKIP = {"ppdrada"}  # repos that never show up
LIMIT = 5           # cards in "latest things i built"
LANGS = 7           # project technologies after the fixed tools

FIXED = [("Windows", "assets/windows"), ("macOS", "apple"), ("Linux", "linux"), ("Git", "git"),
         ("VS Code", "assets/vscode"), ("Postman", "postman")]
# GitHub language -> simple-icons slug, or a local asset when simple-icons has none
ICONS = {
    "Python": "python", "JavaScript": "javascript", "TypeScript": "typescript", "Java": "openjdk",
    "Shell": "gnubash", "Swift": "swift", "HTML": "html5", "CSS": "css", "C": "c", "C++": "cplusplus",
    "Go": "go", "Rust": "rust", "PHP": "php", "Kotlin": "kotlin", "Dart": "dart", "Ruby": "ruby",
    "Lua": "lua", "Jupyter Notebook": "jupyter", "Dockerfile": "docker",
    "SCSS": "sass", "TSQL": "assets/sql", "PLSQL": "assets/sql", "PLpgSQL": "postgresql",
}

# dark and light colors for every image, so the readme works in both GitHub themes
DARK = {"icon": "BFBFBF", "bg": "#111111", "border": "#2A2A2A", "name": "#EDEDED", "dot": "#8C8C8C", "lang": "#A6A6A6"}
LIGHT = {"icon": "595959", "bg": "#F6F6F6", "border": "#D0D0D0", "name": "#1F1F1F", "dot": "#8C8C8C", "lang": "#595959"}

CARD = """<svg xmlns="http://www.w3.org/2000/svg" width="160" height="58" viewBox="0 0 160 58" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">
<rect x="0.5" y="0.5" width="159" height="57" rx="8" fill="{bg}" stroke="{border}"/>
<text x="14" y="25" fill="{name_color}" font-size="{size}" font-weight="600">{name}</text>
<circle cx="18" cy="40" r="4" fill="{dot}"/>
<text x="27" y="44" fill="{lang_color}" font-size="11">{lang}</text>
</svg>
"""


def themed(dark, light, attrs):
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="{dark}">'
            f'<img src="{light}" {attrs} /></picture>')


def icon(alt, src):
    if src.startswith("assets/"):
        return themed(f"{src}.svg", f"{src}-light.svg", f'height="34" alt="{alt}"')
    cdn = f"https://cdn.simpleicons.org/{src}/"
    return themed(cdn + DARK["icon"], cdn + LIGHT["icon"], f'height="34" alt="{alt}"')


def get(url):
    headers = {"Authorization": f"Bearer {os.environ['GH_TOKEN']}"} if os.environ.get("GH_TOKEN") else {}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as res:
        return json.load(res)


def skills_block(repos, owner):
    # every language of every repo (not only the main one); most repos first, then most code
    used, size = collections.Counter(), collections.Counter()
    for r in repos:
        for lang, n in get(f"https://api.github.com/repos/{owner}/{r['name']}/languages").items():
            if lang in ICONS:
                used[lang] += 1
                size[lang] += n
    langs = sorted(used, key=lambda l: (-used[l], -size[l]))[:LANGS]
    return "&nbsp;&nbsp;\n".join(icon(a, s) for a, s in FIXED + [(l, ICONS[l]) for l in langs])


def repos_block(repos, owner, assets):
    for old in assets.glob("repo-*.svg"):
        old.unlink()
    cards = []
    for r in repos[:LIMIT]:
        name, lang = r["name"], (r["language"] or "").lower()
        for suffix, c in (("", DARK), ("-light", LIGHT)):
            card = CARD.format(name=name, lang=lang, size=13 if len(name) <= 16 else 10, bg=c["bg"], border=c["border"], name_color=c["name"], dot=c["dot"], lang_color=c["lang"])
            (assets / f"repo-{name}{suffix}.svg").write_text(card, encoding="utf-8")
        img = themed(f"assets/repo-{name}.svg", f"assets/repo-{name}-light.svg", f'width="18%" alt="{name} · {lang}"')
        cards.append(f'<a href="https://github.com/{owner}/{name}">{img}</a>')
    return "&nbsp;".join(cards)


def last_commit(owner, repo):
    # pushed_at also moves when bots (dependabot) touch a repo, so sort by the real last commit instead
    url = f"https://api.github.com/repos/{owner}/{repo['name']}/commits?per_page=1&sha={repo['default_branch']}"
    try:
        commits = get(url)
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
    text = replace(text, "skills", skills_block(repos, owner))
    text = replace(text, "repos", repos_block(repos, owner, root / "assets"))
    readme.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
