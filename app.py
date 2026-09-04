import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parent
RESUME_FILE = BASE_DIR / "resume.yaml"
DATA_DIR = BASE_DIR / "resumes"
DEFAULT_SOURCE = "主简历"

# 可选渲染风格：同一个数据源，不同的 CSS 外观。
# key 会作为 <body> 的 theme-{key} 类名，value 是编辑器切换按钮上的文案。
THEMES: Dict[str, str] = {
    "classic": "风格 1 · 经典蓝",
    "modern": "风格 2 · 现代青",
    "elegant": "风格 3 · 学术黑",
    "compact": "风格 4 · 紧凑学术",
}
DEFAULT_THEME = "classic"

app = FastAPI(title="easy-cv", version="0.2.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/images", StaticFiles(directory=str(BASE_DIR / "images")), name="images")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def bold_filter(text: str) -> str:
    """Convert **text** to <strong>text</strong> for inline bold markers."""
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)


templates.env.filters["bold"] = bold_filter


class ResumeDataPayload(BaseModel):
    data: Dict[str, Any]


class ResumeRawPayload(BaseModel):
    yaml_text: str


class SourcePayload(BaseModel):
    name: str


def _css_version() -> str:
    """返回静态样式的最新修改时间，作为 URL 版本号规避浏览器缓存（含主题文件）。"""
    try:
        mtimes = [(BASE_DIR / "static" / "style.css").stat().st_mtime]
        themes_dir = BASE_DIR / "static" / "themes"
        if themes_dir.is_dir():
            mtimes += [p.stat().st_mtime for p in themes_dir.glob("*.css")]
        return str(int(max(mtimes)))
    except OSError:
        return "1"


def _ensure_data_dir() -> None:
    """确保 resumes/ 目录存在；首次运行把根目录的 resume.yaml 迁移进去作为默认数据源。"""
    DATA_DIR.mkdir(exist_ok=True)
    if not any(DATA_DIR.glob("*.yaml")) and RESUME_FILE.exists():
        shutil.copy(RESUME_FILE, DATA_DIR / f"{DEFAULT_SOURCE}.yaml")


def _list_sources() -> List[str]:
    """列出所有数据源 id（文件名去掉 .yaml），默认数据源排在最前。"""
    _ensure_data_dir()
    stems = sorted(p.stem for p in DATA_DIR.glob("*.yaml"))
    if DEFAULT_SOURCE in stems:
        stems.remove(DEFAULT_SOURCE)
        stems.insert(0, DEFAULT_SOURCE)
    return stems


def _resolve_source(src: Optional[str]) -> str:
    """把查询参数解析成合法数据源 id；为空时取默认数据源，非法时 404。"""
    sources = _list_sources()
    if not sources:
        raise HTTPException(status_code=404, detail="resumes/ 目录下没有任何数据源 yaml 文件")
    if not src:
        return sources[0]
    if src not in sources:
        raise HTTPException(status_code=404, detail=f"数据源不存在: {src}")
    return src


def _source_path(src: str) -> Path:
    return DATA_DIR / f"{src}.yaml"


def _read_resume(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise HTTPException(status_code=404, detail="数据源文件不存在")
    text = path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(text) or {}
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="YAML 顶层必须是对象")
    return parsed


def _write_resume(data: Dict[str, Any], path: Path) -> None:
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/editor")


def _resolve_theme(theme: Optional[str]) -> str:
    """把查询参数解析成合法主题 id；为空或非法时取默认主题。"""
    return theme if theme in THEMES else DEFAULT_THEME


@app.get("/resume", response_class=HTMLResponse, include_in_schema=False)
def resume_page(request: Request, src: Optional[str] = None, theme: Optional[str] = None) -> HTMLResponse:
    source = _resolve_source(src)
    resolved_theme = _resolve_theme(theme)
    data = _read_resume(_source_path(source))
    return templates.TemplateResponse(
        request,
        "resume.html",
        context={
            "resume": data,
            "basics": data.get("basics", {}),
            "skills": data.get("skills", []),
            "skills_title": data.get("skills_title", "技术能力"),
            "achievements": data.get("achievements", {}),
            "projects": data.get("projects", []),
            "themes": THEMES,
            "default_theme": DEFAULT_THEME,
            "theme": resolved_theme,
            "sources": _list_sources(),
            "current_src": source,
            "css_version": _css_version(),
        },
    )


@app.get("/editor", response_class=HTMLResponse, include_in_schema=False)
def editor_page(request: Request, src: Optional[str] = None) -> HTMLResponse:
    source = _resolve_source(src)
    path = _source_path(source)
    yaml_text = path.read_text(encoding="utf-8") if path.exists() else ""
    return templates.TemplateResponse(
        request,
        "editor.html",
        context={
            "yaml_text": yaml_text,
            "themes": THEMES,
            "sources": _list_sources(),
            "current_src": source,
            "css_version": _css_version(),
        },
    )


@app.get("/api/sources")
def list_sources() -> Dict[str, List[str]]:
    return {"sources": _list_sources()}


@app.post("/api/sources")
def create_source(payload: SourcePayload) -> Dict[str, str]:
    name = payload.name.strip()
    if not re.fullmatch(r"[\w\-]{1,40}", name):
        raise HTTPException(status_code=400, detail="名称只能包含中英文、数字、下划线、中划线，长度 1-40")
    _ensure_data_dir()
    path = DATA_DIR / f"{name}.yaml"
    if path.exists():
        raise HTTPException(status_code=400, detail=f"数据源已存在: {name}")
    skeleton = {"basics": {"name": name, "position": ""}}
    path.write_text(
        yaml.safe_dump(skeleton, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return {"message": f"已创建数据源: {name}", "name": name}


@app.get("/api/resume")
def get_resume_data(src: Optional[str] = None) -> Dict[str, Any]:
    return _read_resume(_source_path(_resolve_source(src)))


@app.put("/api/resume")
def put_resume_data(payload: ResumeDataPayload, src: Optional[str] = None) -> Dict[str, str]:
    _write_resume(payload.data, _source_path(_resolve_source(src)))
    return {"message": "已更新简历数据"}


@app.get("/api/resume/raw")
def get_resume_raw(src: Optional[str] = None) -> Dict[str, str]:
    path = _source_path(_resolve_source(src))
    if not path.exists():
        raise HTTPException(status_code=404, detail="数据源文件不存在")
    return {"yaml_text": path.read_text(encoding="utf-8")}


@app.put("/api/resume/raw")
def put_resume_raw(payload: ResumeRawPayload, src: Optional[str] = None) -> Dict[str, str]:
    source = _resolve_source(src)
    try:
        parsed = yaml.safe_load(payload.yaml_text) or {}
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"YAML 解析失败: {exc}") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="YAML 顶层必须是对象")
    _source_path(source).write_text(payload.yaml_text, encoding="utf-8")
    return {"message": "YAML 已保存"}


if __name__ == "__main__":
    import sys
    import subprocess
    import platform

    host = "127.0.0.1"
    port = 8010

    if platform.system() == "Darwin":
        url = f"http://{host}:{port}"
        subprocess.Popen(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        import uvicorn
    except ImportError:
        print("uvicorn 未安装，请先运行: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)

    uvicorn.run("app:app", host=host, port=port, reload=True)
