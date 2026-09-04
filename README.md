# easyCV

一个 Yaml 文件定义所有内容，实时预览，在线编辑，可一键导出 PDF，不用装任何软件，可丝滑接入各种skill

克隆仓库 → 编辑 `resumes/` 下的 YAML → 启动服务 → 浏览器打开即可预览和导出。首次启动会把根目录 `resume.yaml`（如存在）自动迁移为 `resumes/主简历.yaml`。

## Preview

```
http://localhost:8010/editor    ← 编辑器（默认首页）：左侧 YAML 编辑 + 右侧实时预览 + 一键导出 PDF
http://localhost:8010/resume    ← 独立预览页（可选）：只读展示单份简历，适合分享/单独打印
```

## Quick Start

**macOS**（需要 Python 3.9+，没有先 `brew install python`）

```bash
git clone https://github.com/BLYHFL/easyCV.git
cd easyCV
bash start.sh          # 自动建环境、装依赖、启动，并打开浏览器
# 首次使用请先复制模板建一份简历：cp examples/模板.yaml resumes/主简历.yaml
```

**Linux**

```bash
git clone https://github.com/BLYHFL/easyCV.git
cd easyCV
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# 用脱敏模板建一份自己的简历（resumes/ 下每个 .yaml 就是一份简历）
cp examples/模板.yaml resumes/主简历.yaml

uvicorn app:app --reload --host 0.0.0.0 --port 8010
```

**Windows**

```bash
git clone https://github.com/BLYHFL/easyCV.git
cd easyCV
python3 -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt

# 用脱敏模板建一份自己的简历
copy examples\模板.yaml resumes\主简历.yaml

uvicorn app:app --reload --host 0.0.0.0 --port 8010
```

启动后访问 [http://localhost:8010](http://localhost:8010)。

> 简历数据属于个人隐私，`resumes/`、`images/` 已被 `.gitignore` 排除，不会被提交到仓库。

## 多数据源 × 多风格

简历内容存放在 `resumes/` 目录，**每个 `.yaml` 文件是一份独立简历**（不同岗位不同内容）。首次启动会把根目录的 `resume.yaml` 自动迁移为 `resumes/主简历.yaml`。

编辑器顶部两个下拉框：

- **数据源**：切换要编辑的简历；点「＋」输入名称即可新建一份
- **风格**：切换渲染样式，同一份数据即时换装

| 风格 | 外观 | 样式文件 |
| ---- | ---- | -------- |
| 风格 1 · 经典蓝 | 居左排版，蓝色主色调（默认） | `static/themes/classic.css` |
| 风格 2 · 现代青 | 深青色系，色块标题 + 时间轴条目 | `static/themes/modern.css` |
| 风格 3 · 学术黑 | 衬线字体、居中排版、黑白灰，不显示证件照 | `static/themes/elegant.css` |
| 风格 4 · 紧凑学术 | 学术黑的高密度一页版：小字号、统一行高、压缩间距 | `static/themes/compact.css` |

N 份数据源 × 4 种风格 = 任意组合预览/导出。数据源与风格的选择会记忆在浏览器（localStorage），也可用 URL 参数直达：`/resume?src=产品经理&theme=elegant`。

## How It Works

```
resumes/              ← 简历数据源目录，每个 .yaml 一份简历（唯一需要编辑的文件）
templates/resume.html ← Jinja2 渲染模板
static/style.css      ← 基础结构样式（同时是经典蓝默认外观）+ 编辑器 UI
static/themes/        ← 每个风格一个 CSS 文件（classic / modern / elegant / compact），按主题加载
app.py                ← FastAPI 服务
```

### 编辑与导出（都在编辑器里完成）

打开 `/editor`（即首页）：

1. 顶部下拉框选**数据源**（不同岗位的简历）和**风格**（渲染样式），右侧实时预览
2. 左侧直接改 YAML，自动保存
3. 点右上角**「导出 PDF」**，直接调起浏览器打印——打的就是右侧预览，无需跳转任何页面

`/resume` 是可选的只读预览页，用于把某份简历单独分享给别人，或在独立标签页里打印；简历页右上角的「编辑 YAML」可一键跳回编辑器。

> 建议使用 Chrome/Edge，打印时取消页眉页脚，边距选"无"，效果最佳。

## YAML Structure

```yaml
basics:            # 姓名、岗位、联系方式、education 教育经历、target_position 求职意向（可选）
summary:           # 个人总结（可选，写在这里才显示「📝 个人总结」板块）
skills_title:      # 能力板块标题（可选，默认「技术能力」）
skills:            # 能力条目：{ category, items }
internship:        # 工作经历：{ company, role, date, background, responsibility, highlights[], results }
projects:          # 项目经历：{ name, direction, role, date, background, responsibility, highlights[], results, tech_stack }
achievements:      # 科研成果：competition / publication / patent
```

字段都是可选的，模板会跳过缺失的板块。`highlights` 里用 `**文本**` 表示加粗。完整示例见 [`examples/`](./examples/)。

## API

所有简历接口都支持 `?src=<数据源id>`（`resumes/` 下的文件名，不含 `.yaml`），省略时取第一个数据源。

| Method | Path              | Description |
| ------ | ----------------- | ----------- |
| `GET`  | `/resume`         | HTML 简历预览，支持 `?src=` `?theme=` |
| `GET`  | `/editor`         | YAML 编辑器，支持 `?src=` |
| `GET`  | `/api/sources`    | 列出所有数据源 |
| `POST` | `/api/sources`    | 新建数据源 `{"name": "..."}` |
| `GET`  | `/api/resume`     | JSON 格式简历数据 |
| `PUT`  | `/api/resume`     | JSON 覆盖更新   |
| `GET`  | `/api/resume/raw` | 获取原始 YAML   |
| `PUT`  | `/api/resume/raw` | 保存原始 YAML（写入前校验） |
| `GET`  | `/docs`           | OpenAPI 文档  |

## Docker

```bash
docker build -t easy-cv .
docker run -p 8010:8010 easy-cv
```

Acknowledgements

- 原始项目：<https://github.com/lvy010/easyCV>（MIT）
- <https://github.com/hijiangtao/resume>
- <https://github.com/yamlresume/yamlresume>

## License

MIT
