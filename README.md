# UnofficalSiteGenerator

A simple Python tool that generates Un-official static websites from a single
`site.md` config file per site. Drop in a config, run one command, get a
complete deployable website with a custom favicon.

Built to support community-made Un-official sites for local businesses,
community resources, and other organizations.

---

## Requirements

Python 3.8+ and four packages:

```bash
pip install pyyaml jinja2 pillow requests
```

---

## Directory Layout

Sites live as **siblings** of the tool folder — not inside it.

```
UnofficalSiteGenerator/      <- tool lives here, never moves
  generate.py
  index.html.j2
  README.md

MyBusiness-Unofficial/       <- site folder, sibling to the tool
  site.md                    <- the only file you edit per site
  css/                       <- optional — copied into dist/ as-is
  js/
  img/
  docs/
  dist/                      <- generated output appears here

AnotherBusiness-Unofficial/  <- add as many as you need
  site.md
  dist/
```

---

## Usage

```bash
# Pass the site directory
python UnofficalSiteGenerator/generate.py ../MyBusiness-Unofficial

# Or pass site.md directly
python UnofficalSiteGenerator/generate.py ../MyBusiness-Unofficial/site.md
```

Output lands in `dist/` inside each site's own folder.

---

## Adding a New Site

1. Create a new sibling folder and copy the blank starter into it:

   ```bash
   mkdir ../MyBusiness-Unofficial
   cp site.md ../MyBusiness-Unofficial/site.md
   ```

2. Edit `site.md` — fill in the fields, remove any sections you don't need.

3. Optionally add assets alongside `site.md`:

   ```
   MyBusiness-Unofficial/
     site.md
     css/style.css
     img/storefront.jpg
     docs/menu.pdf
   ```

4. Run the generator:

   ```bash
   python UnofficalSiteGenerator/generate.py ../MyBusiness-Unofficial
   ```

5. Open `dist/index.html` in a browser to preview, then copy `dist/` contents
   to your web host or push to GitHub Pages.

---

## site.md Reference

```yaml
# -- Identity -----------------------------------------------------------------
name: "Business Name"
github: "https://github.com/user/repo"

# -- Operator -----------------------------------------------------------------
operator: "Your Name / Org"
operator_url: "https://yoursite.com"
operator_support_url: "https://yoursite.com/support"   # optional

# -- Favicon ------------------------------------------------------------------
favicon:
  letter: "B"            # single character
  font: "Georgia"        # Google Font name (reference only)
  color: "#ffffff"       # text color
  background: "#333333"  # square background color

# -- Contact ------------------------------------------------------------------
location: "123 Main St, City, ST 00000"
email: "hello@example.com"
phone: "(555) 555-5555"

# -- Hours --------------------------------------------------------------------
hours:
  - "Monday - Friday: 9AM to 5PM"
  - "Saturday - Sunday: Closed"

# -- Links (social, review sites, etc.) ---------------------------------------
links:
  - label: "Facebook: Business Name"
    url: "https://facebook.com/..."

# -- Menu (optional) ----------------------------------------------------------
menu:
  - label: "Menu - PDF"
    url: "docs/menu.pdf"

# -- Services (optional) ------------------------------------------------------
services:
  - "Drive-through"
  - "Online ordering"

# -- Photos (optional) --------------------------------------------------------
photos:
  - label: "Storefront"
    url: "img/storefront.jpg"
```

All sections marked **optional** (`menu`, `services`, `photos`,
`operator_support_url`) can be removed entirely — they simply won't appear
in the output.

---

## What Gets Generated

| File | Description |
|---|---|
| `dist/index.html` | The complete website page |
| `dist/favicon.ico` | Multi-size favicon (16, 32, 48px) |
| `dist/android-chrome-192x192.png` | Android home screen icon |
| `dist/android-chrome-512x512.png` | Android splash icon |
| `dist/apple-touch-icon.png` | iOS home screen icon (180px) |
| `dist/site.webmanifest` | PWA manifest |
| `dist/css/` `dist/js/` `dist/img/` `dist/docs/` | Copied from source if present |

---

## GitHub Info

If `github:` is set in `site.md` and the machine has internet access,
`generate.py` calls the GitHub REST API and pulls the repo description,
license, and last push date. If offline or the repo is private, it silently
skips this step and continues.

---

## Deploying

The contents of `dist/` are a self-contained static site. Deploy by:

- **GitHub Pages** — push `dist/` contents to the `gh-pages` branch or
  configure Pages to serve from `dist/`
- **Any web host** — copy `dist/` contents to your public HTML folder
- **IPFS** — pin the `dist/` folder

---

## License

MIT — see [LICENSE.txt](LICENSE.txt)
