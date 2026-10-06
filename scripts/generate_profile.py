"""Render the profile as self-contained SVGs; optionally fetch public GitHub stats."""
import argparse
from html import escape
import json
import os
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
THEMES = {
    "dark": {"bg": "#161b22", "text": "#c9d1d9", "key": "#ffa657", "value": "#a5d6ff", "dots": "#616e7f"},
    "light": {"bg": "#f6f8fa", "text": "#24292f", "key": "#953800", "value": "#0550ae", "dots": "#8c959f"},
}


def fetch_stats(username):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "github-profile-readme"}
    if token := os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + token

    def get(path):
        with urlopen(Request("https://api.github.com" + path, headers=headers), timeout=30) as response:
            return json.load(response)

    owner = quote(username, safe="")
    user = get("/users/" + owner)
    stars = 0
    page = 1
    while True:
        repos = get(f"/users/{owner}/repos?type=owner&per_page=100&page={page}")
        stars += sum(repo["stargazers_count"] for repo in repos)
        if len(repos) < 100:
            break
        page += 1
    return {"repos": user["public_repos"], "stars": stars, "followers": user["followers"]}


def rows(profile, stats):
    result = [(0, [("text", profile["title"])]), (1, [("dots", "-" * 69)])]
    for row, key, value in profile["fields"]:
        dots = "." * max(2, 65 - len(key) - len(value) - 5)
        result.append((row, [("dots", ". "), ("key", key), ("text", ": "), ("dots", dots + " "), ("value", value)]))
    for row, heading in profile["sections"]:
        result.append((row, [("text", "- " + heading + " "), ("dots", "-" * (65-len(heading)-3))]))
    result.append((23, [
        ("dots", ". "), ("key", "Repos"), ("text", ": "), ("value", str(stats.get("repos", "--"))),
        ("dots", "  |  "), ("key", "Stars"), ("text", ": "), ("value", str(stats.get("stars", "--"))),
        ("dots", "  |  "), ("key", "Followers"), ("text", ": "), ("value", str(stats.get("followers", "--"))),
    ]))
    result.append((24, [("dots", ". " + profile["footer"])]))
    return result


def render(profile, stats, theme):
    colors = THEMES[theme]
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="985" height="530" viewBox="0 0 985 530" role="img" aria-labelledby="title desc">',
        '<title id="title">Kayo Bitencourt — GitHub Profile</title>',
        '<desc id="desc">Character portrait, Arch Linux, development stack, projects and contact information.</desc>',
        f'<rect width="985" height="530" rx="15" fill="{colors["bg"]}"/>',
        '<g font-family="DejaVu Sans Mono,Consolas,monospace" xml:space="preserve">',
    ]
    portrait = profile.get("portrait_light", profile["portrait"]) if theme == "light" else profile["portrait"]
    size = profile.get("portrait_font_size", 12)
    spacing = profile.get("portrait_line_height", 20)
    start_y = profile.get("portrait_start_y", 30)
    for row, text in enumerate(portrait):
        lines.append(f'<text x="15" y="{start_y+row*spacing}" font-size="{size}" fill="{colors["text"]}">{escape(text)}</text>')
    for row, spans in rows(profile, stats):
        line = f'<text x="370" y="{30+row*20}" font-size="14">'
        line += ''.join(f'<tspan fill="{colors[style]}">{escape(text)}</tspan>' for style, text in spans)
        lines.append(line + '</text>')
    lines.extend(['</g>', '</svg>'])
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', default=os.getenv('GITHUB_REPOSITORY_OWNER', ''))
    args = parser.parse_args()
    profile = json.loads((ROOT/'profile.json').read_text())
    stats_file = ROOT/'assets/stats.json'
    stats = json.loads(stats_file.read_text()) if stats_file.exists() else {}
    if args.username:
        # Fetch all pages before writing so a failed API request preserves current files.
        stats = fetch_stats(args.username)
        stats_file.write_text(json.dumps(stats, indent=2)+'\n')
    (ROOT/'assets/portrait.txt').write_text('\n'.join(profile['portrait'])+'\n')
    for theme in THEMES:
        (ROOT/f'assets/{theme}_mode.svg').write_text(render(profile, stats, theme))
    print('Generated dark and light profile SVGs.')


if __name__ == '__main__':
    main()
