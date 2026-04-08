#!/usr/bin/env python3
"""
generate.py — Static site generator for Un-official business/resource sites.

Directory layout
----------------
  UnofficalSiteGenerator/    <- tool lives here, never moves
    generate.py
    index.html.j2

  ExampleSite-Unofficial/    <- site folders live as siblings next to the tool
    site.md                  <- the only file you edit per site
    css/                     <- optional: copied into dist/ as-is
    js/
    img/
    docs/
    dist/                    <- generated output appears here

  AnotherSite-Unofficial/    <- add as many sibling site folders as you like
    site.md
    dist/

Usage
-----
    # Build one site -- pass the site directory
    python UnofficalSiteGenerator/generate.py ../ExampleSite-Unofficial

    # Build one site -- pass site.md directly
    python UnofficalSiteGenerator/generate.py ../ExampleSite-Unofficial/site.md

Output per site (written into that site's dist/ folder)
--------------------------------------------------------
    dist/index.html
    dist/favicon.ico
    dist/android-chrome-192x192.png
    dist/android-chrome-512x512.png
    dist/apple-touch-icon.png
    dist/site.webmanifest
    dist/css/  dist/js/  dist/img/  dist/docs/   (copied if present)

Requirements (install once, anywhere)
--------------------------------------
    pip install pyyaml jinja2 pillow requests
"""

import json
import re
import shutil
import struct
import sys
from io import BytesIO
from pathlib import Path

# -- Third-party (pip install pyyaml jinja2 pillow requests) -------------------
try:
    import yaml
except ImportError:
    sys.exit("Missing dependency: pip install pyyaml")

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:
    sys.exit("Missing dependency: pip install jinja2")

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("WARNING: Pillow not found -- favicon generation skipped. pip install pillow")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("WARNING: requests not found -- GitHub info skipped. pip install requests")


# -- Tool location: template always lives next to generate.py ------------------
TOOL_DIR = Path(__file__).resolve().parent


# -- Helpers -------------------------------------------------------------------

def digits_only(phone: str) -> str:
    """Strip everything except digits from a phone number string."""
    return re.sub(r"\D", "", phone)


def github_pages_url(github_url: str) -> str:
    """
    Convert a GitHub repo URL to its probable GitHub Pages URL.
    e.g. https://github.com/user/repo -> https://user.github.io/repo/
    """
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)", github_url)
    if match:
        user, repo = match.group(1), match.group(2)
        return f"https://{user}.github.io/{repo}/"
    return github_url


def fetch_github_info(github_url: str) -> dict:
    """
    Call the GitHub REST API to get live repo metadata.
    Returns a dict with description, license, last_push, stars, open_issues.
    Falls back to empty dict if the request fails or requests isn't installed.
    """
    if not REQUESTS_AVAILABLE:
        return {}

    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)", github_url)
    if not match:
        return {}

    api_url = f"https://api.github.com/repos/{match.group(1)}/{match.group(2)}"
    try:
        resp = requests.get(api_url, timeout=8,
                            headers={"Accept": "application/vnd.github+json"})
        resp.raise_for_status()
        data = resp.json()
        return {
            "description": data.get("description", ""),
            "license":     data.get("license", {}).get("spdx_id", ""),
            "last_push":   data.get("pushed_at", "")[:10],   # YYYY-MM-DD
            "stars":       data.get("stargazers_count", 0),
            "open_issues": data.get("open_issues_count", 0),
        }
    except Exception as exc:
        print(f"WARNING: GitHub API request failed -- {exc}")
        return {}


# -- Favicon generation --------------------------------------------------------

def hex_to_rgb(hex_color: str) -> tuple:
    """Convert '#RRGGBB' to (R, G, B)."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def make_favicon_image(letter: str, fg: str, bg: str, size: int) -> "Image.Image":
    """
    Draw a square favicon image with a coloured background and a centred letter.
    Uses anchor='mm' to reliably centre the glyph at all sizes.
    """
    img  = Image.new("RGB", (size, size), hex_to_rgb(bg))
    draw = ImageDraw.Draw(img)

    font = None
    font_size = max(10, int(size * 0.65))
    candidate_dirs = [
        "/usr/share/fonts/truetype/dejavu",
        "/usr/share/fonts/truetype/liberation",
        "/System/Library/Fonts",
        "/Library/Fonts",
        "C:/Windows/Fonts",
    ]
    candidate_names = [
        "DejaVuSerif-Bold.ttf",
        "LiberationSerif-Bold.ttf",
        "Georgia Bold.ttf",
        "georgia.ttf",
        "Times New Roman Bold.ttf",
        "timesbd.ttf",
    ]
    for d in candidate_dirs:
        for n in candidate_names:
            path = Path(d) / n
            if path.exists():
                try:
                    font = ImageFont.truetype(str(path), font_size)
                    break
                except Exception:
                    pass
        if font:
            break

    if font is None:
        print("    WARNING: No TrueType font found -- favicon letter may not render correctly.")
        font = ImageFont.load_default()

    mid = size / 2
    draw.text((mid, mid), letter, fill=hex_to_rgb(fg), font=font, anchor="mm")

    return img


def image_to_ico(images: list) -> bytes:
    """Pack a list of PIL Images into a valid multi-size .ico file."""
    png_bufs = []
    for img in images:
        buf = BytesIO()
        img.save(buf, format="PNG")
        png_bufs.append(buf.getvalue())

    num = len(images)
    header = struct.pack("<HHH", 0, 1, num)

    offset = 6 + num * 16
    directory = b""
    for i, img in enumerate(images):
        w, h = img.size
        data = png_bufs[i]
        directory += struct.pack(
            "<BBBBHHII",
            w if w < 256 else 0,
            h if h < 256 else 0,
            0, 0, 1, 32,
            len(data),
            offset,
        )
        offset += len(data)

    return header + directory + b"".join(png_bufs)


def generate_favicons(favicon_cfg: dict, dist_dir: Path) -> None:
    """Generate favicon.ico, android PNGs, apple-touch-icon, and site.webmanifest."""
    if not PIL_AVAILABLE:
        print("  [favicon] Skipped -- Pillow not installed.")
        return

    letter = favicon_cfg.get("letter", "?")
    fg     = favicon_cfg.get("color",      "#ffffff")
    bg     = favicon_cfg.get("background", "#333333")

    print(f"  [favicon] Generating '{letter}' -- fg={fg}  bg={bg}")

    sizes = {
        "android-chrome-192x192.png": 192,
        "android-chrome-512x512.png": 512,
        "apple-touch-icon.png":       180,
    }

    for filename, size in sizes.items():
        img = make_favicon_image(letter, fg, bg, size)
        img.save(dist_dir / filename, format="PNG")
        print(f"    wrote {filename}")

    ico_images = [make_favicon_image(letter, fg, bg, s) for s in (16, 32, 48)]
    (dist_dir / "favicon.ico").write_bytes(image_to_ico(ico_images))
    print("    wrote favicon.ico")

    manifest = {
        "name": "",
        "short_name": "",
        "icons": [
            {"src": "android-chrome-192x192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "android-chrome-512x512.png", "sizes": "512x512", "type": "image/png"},
        ],
        "theme_color": bg,
        "background_color": bg,
        "display": "standalone",
    }
    (dist_dir / "site.webmanifest").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print("    wrote site.webmanifest")


# -- Config loading ------------------------------------------------------------

def load_config(config_path: Path) -> dict:
    """
    Load site.md -- expects a YAML document.
    Strips pure comment lines (starting with #) before parsing.
    """
    raw = config_path.read_text(encoding="utf-8")
    yaml_lines = []
    for line in raw.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#") and ":" not in stripped:
            continue
        yaml_lines.append(line)
    return yaml.safe_load("\n".join(yaml_lines)) or {}


def build_template_context(cfg: dict, github_info: dict) -> dict:
    """Assemble the Jinja2 template context from config + GitHub data."""
    phone_raw  = cfg.get("phone", "")
    github_url = cfg.get("github", "")

    return {
        "name":               cfg.get("name", ""),
        "github":             github_url,
        "github_pages_url":   github_pages_url(github_url) if github_url else "",
        "operator":             cfg.get("operator", ""),
        "operator_url":         cfg.get("operator_url", ""),
        "operator_support_url": cfg.get("operator_support_url", ""),
        "location":     cfg.get("location", ""),
        "email":        cfg.get("email", ""),
        "phone":        phone_raw,
        "phone_digits": digits_only(phone_raw),
        "hours":    cfg.get("hours",    []),
        "links":    cfg.get("links",    []),
        "menu":     cfg.get("menu",     []),
        "services": cfg.get("services", []),
        "photos":   cfg.get("photos",   []),
        "gh":       github_info,
    }


def copy_assets(src_dir: Path, dist_dir: Path) -> None:
    """Copy css/, js/, img/, docs/ folders into dist/ if they exist."""
    for folder in ("css", "js", "img", "docs"):
        src = src_dir / folder
        if src.exists():
            dst = dist_dir / folder
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"  [assets] Copied {folder}/")


# -- Build ---------------------------------------------------------------------

def find_config(arg: Path) -> Path:
    """
    Accept a path to a site directory or to site.md directly.
    Returns the resolved Path to site.md.
    """
    arg = arg.resolve()
    if arg.is_dir():
        candidate = arg / "site.md"
        if not candidate.exists():
            sys.exit(f"ERROR: No site.md found in: {arg}")
        return candidate
    if arg.is_file():
        return arg
    sys.exit(f"ERROR: Path not found: {arg}")


def build_site(config_file: Path) -> None:
    """Build one site from its site.md config file."""
    src_dir  = config_file.parent
    dist_dir = src_dir / "dist"
    dist_dir.mkdir(exist_ok=True)

    print(f"\n=== Building: {src_dir.name} ===")
    print(f"  Config   : {config_file}")
    print(f"  Output   : {dist_dir}")
    print(f"  Template : {TOOL_DIR / 'index.html.j2'}\n")

    cfg = load_config(config_file)
    print(f"  [config] Loaded -- site name: {cfg.get('name', '(unnamed)')}")

    github_info = {}
    if cfg.get("github"):
        print(f"  [github] Fetching repo info ...")
        github_info = fetch_github_info(cfg["github"])
        if github_info:
            print(f"    description : {github_info.get('description', '')}")
            print(f"    license     : {github_info.get('license', '')}")
            print(f"    last push   : {github_info.get('last_push', '')}")
        else:
            print("    (no data returned -- continuing without)")

    template_path = TOOL_DIR / "index.html.j2"
    if not template_path.exists():
        sys.exit(f"ERROR: Template not found: {template_path}\n"
                 f"       Make sure index.html.j2 is in the same folder as generate.py")

    env      = Environment(loader=FileSystemLoader(str(TOOL_DIR)),
                           autoescape=select_autoescape(["html"]))
    html     = env.get_template("index.html.j2").render(
                   **build_template_context(cfg, github_info))

    (dist_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"  [html]   Wrote {dist_dir / 'index.html'}")

    favicon_cfg = cfg.get("favicon", {})
    if favicon_cfg:
        generate_favicons(favicon_cfg, dist_dir)
    else:
        print("  [favicon] No favicon config in site.md -- skipping.")

    copy_assets(src_dir, dist_dir)

    print(f"\n  Done -- {src_dir.name}/dist/index.html\n")

def _write_readme(config_file: Path, name: str | None = None) -> None:
    """
    Write a tiny markdown README.md next to site.md.

    * If ``name`` is supplied (e.g. the value from the config), it becomes the page title.
    * Otherwise we fall back to the folder’s base name as the identifier.
    The file will be created in the same directory that contains ``site.md``.
    """
    readme_path = config_file.parent / "README.md"

    # If a human‑readable name is not given, use the folder name (or empty string).
    if name:
        title = name
    else:
        title = str(config_file.parent.name) or ""

    content = f"""# {title} (Un-official)

This is a custom unofficial site generated by the [Un‑official Static Website Generator](https://github.com/djbrieck/Un-official-static-website-generator).

## Build

Check out the generator repo and place this site’s folder as a sibling to it then run the following command from the this site’s folder:

```bash
python3 ../Un-official-static-website-generator/generate.py .
``` 
This will read the `site.md` config file, generate `dist/index.html` and favicons, and copy any `css/`, `js/`, `img/`, or `docs/` folders into `dist/`.

## Edit the `site.md` file to customize the content of the generated site then re-run the generator to update the output.

## Deploy the contents of the `dist/` folder to your hosting provider or [IPFS](https://ipfs.tech/).
"""

    readme_path.write_text(content, encoding="utf-8")
    print(f"  [readme] Wrote {readme_path}")


# -- Main ----------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python generate.py <site-directory | site.md>")
    build_site(find_config(Path(sys.argv[1])))
    _write_readme(find_config(Path(sys.argv[1])))


if __name__ == "__main__":
    main()
