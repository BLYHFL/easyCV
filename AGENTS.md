# easyCV

YAML-driven resume builder — edit `resume.yaml`, get real-time HTML preview + PDF export. Zero JS framework, pure FastAPI + Jinja2.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8010
```

Open `http://localhost:8010`.

## Architecture

```
app.py              ← FastAPI app — all routes, YAML read/write, yaml.parse
resumes/            ← data sources: one .yaml per resume version (主简历.yaml migrated from resume.yaml on first run)
resume.yaml         ← legacy root file, copied into resumes/ on first run, no longer read directly
templates/
  resume.html       ← resume preview (Jinja2, A4-printable)
  editor.html       ← split-pane YAML editor + live preview
static/style.css    ← base structure styles (classic = default look), editor UI, print rules
static/themes/      ← one CSS file per theme (classic / modern / elegant / compact), loaded per ?theme=
images/             ← profile photos (e.g. 证件照.png)
examples/           ← example YAML resumes
Dockerfile          ← `python:3.12-slim`, port 8010
```

## Routes (all in `app.py`)

All resume routes accept `?src=<数据源id>` (a `.yaml` filename stem inside `resumes/`); omitted → first source (主简历 first).

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | redirect → `/editor`（编辑器即首页） |
| GET | `/resume` | 独立只读预览页（分享/单独打印用；支持 `?src=` `?theme=`） |
| GET | `/editor` | YAML editor with live preview（主工作台） |
| GET | `/api/sources` | list data source ids |
| POST | `/api/sources` | create a source (`{"name": ...}`, sanitized `[\w\-]{1,40}`) |
| GET | `/api/resume` | JSON resume data |
| PUT | `/api/resume` | overwrite with JSON body (`ResumeDataPayload`) |
| GET | `/api/resume/raw` | raw YAML text |
| PUT | `/api/resume/raw` | save YAML (validates before write) |
| GET | `/docs` | OpenAPI docs |

## Conventions

- **YAML-first**: every resume lives as a `.yaml` file under `resumes/`; read/written on every API call. No database.
- **Data sources**: `_list_sources()` scans `resumes/*.yaml`; ids are filename stems (主简历 first). Editor has a source `<select>` + `＋` button (POST `/api/sources`); switching navigates with an explicit `?src=` URL param. Data source is never remembered via localStorage — no hidden state.
- **Preview src invariant (bug class to never reintroduce)**: every preview reference inside the editor MUST carry an explicit `?src=` — including the server-rendered iframe initial `src="/resume?src={{ current_src | urlencode }}"`. A bare `/resume` inside the editor silently falls back to the first source and desyncs editor vs preview. Omitting the param is only acceptable when a human directly visits `/resume` (documented default: first source).
- **Editor auto-save**: 500 ms debounce on input, 200 ms on paste, immediate on blur/Ctrl+S. On page load the buffer is treated as already saved (`lastSavedText = textarea content`); there is NO initial auto-save PUT and no load-time preview refresh — the iframe's explicit initial src already shows the right data. Status text (就绪/保存中…/已保存/错误) is read-only, styled with a ● dot.
- **Emphasis markup in data**: use `**text**` for bold. Backticks are not markup anymore (the `code` filter was removed) and render literally — do not reintroduce them.
- **Render themes**: one CSS file per theme at `static/themes/{id}.css`; ids + dropdown labels live in `THEMES` (`app.py`). `style.css` holds base structure, the default (classic) palette and editor UI only — no theme overrides. Resolution: server validates `?theme=` and renders `<link href="/static/themes/{id}.css">`; a head script falls back to `localStorage["easyCV.theme"]` / `DEFAULT_THEME` and swaps the href pre-paint; a body script adds `body.theme-{id}` (theme selectors are scoped by that class). Editor's 风格 select writes localStorage and reloads the iframe with `&theme=`. New theme = add id to `THEMES` + create `static/themes/{id}.css`. Note: `elegant` hides the profile photo (`.header-right { display:none }`).
- **Editor-centric flow**: the editor is the single workspace. Its toolbar has 数据源/风格 selects + a 导出 PDF button that calls `previewFrame.contentWindow.print()` (fallback: opens `/resume?src=…` in a new tab). There is no 打开预览 link. `/resume` is a standalone read-only page for sharing/printing; its print-bar is hidden by JS when embedded in the editor's iframe (`window.self !== window.top`) — this also prevents editor-in-editor nesting.
- **Bold filter**: `**text**` in highlights → `<strong>text</strong>` (Jinja2 custom `bold` filter, used with `| bold | safe`).
- **PDF export**: Browser `window.print()`. Elements with `class="no-print"` hidden via `@media print`. Recommended: Chrome/Edge, margins "none", no headers/footers.
- **Error messages**: Chinese (`HTTPException`). 400 for bad YAML, 404 for missing file.
- **Code style**: Single-file layout (no package). `snake_case` functions, Chinese docstrings.
- **`resume.yaml` top-level sections**: `basics` (含可选 `education[]`、`target_position`), `skills` + 可选 `skills_title`（板块标题，默认「技术能力」）, 可选顶层 `summary`（「📝 个人总结」板块，注意是顶层字段不是嵌套在 resume: 下）, `internship`, `projects`, `achievements` (plus any custom sections — schema is freeform dict; 模板对每个板块都有 `{% if %}` 守卫，缺失即不渲染).
- **YAML write**: `yaml.safe_dump(…, sort_keys=False, allow_unicode=True)` — preserves key order, writes UTF-8.

## No tests, no linter, no type checker

The repo has zero test/lint/format infrastructure. Do not look for `pytest`, `ruff`, `mypy`, etc.
