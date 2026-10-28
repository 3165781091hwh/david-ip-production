# 安装与配置

## 1. 安装 Skill

克隆到对应 Agent 的 skills 目录，**目录名保持 `david-ip-production`**（与 `SKILL.md` 的 `name` 字段一致）。

```bash
git clone <this-repo> david-ip-production
```

| Agent | 目标路径 |
| --- | --- |
| Reasonix（Windows） | `%APPDATA%\reasonix\skills\david-ip-production` |
| Reasonix（macOS / Linux） | `~/.config/reasonix/skills/david-ip-production` |
| Claude Code | `~/.claude/skills/david-ip-production` |
| Codex | `~/.codex/skills/david-ip-production` |

Windows 快速安装（PowerShell）：

```powershell
git clone <this-repo> "$env:APPDATA\reasonix\skills\david-ip-production"
```

## 2. 验证是否被加载

新开一个会话，让 Agent 复述规则，能答出 **G-1 ~ G-5** 即加载成功：

```
列出 david-ip-production 的五条通用规则，并说明三视图为什么是唯一参考图。
```

若未被识别，依次检查：

1. 目录名与 `SKILL.md` 的 `name` 是否一致（`david-ip-production`）。
2. `SKILL.md` 是否仍在目录根部（不是嵌了一层子目录）。
3. YAML front matter 是否完整（`---` 开头、`description` 存在）。
4. 重启会话或刷新 skills 缓存。

## 3. 本地生图（可选）

仓库已随附 Qwen-Image 2.1 Turbo 工作流，不必自建：

| 文件 | 用途 |
| --- | --- |
| `workflows/qwen21-t2i.api.json` | 文生图，脚本提交用 |
| `workflows/qwen21-edit.api.json` | 参考图生图，脚本提交用，最多 16 张参考图 |
| `workflows/qwen21-t2i.workflow.json`<br>`workflows/qwen21-edit.workflow.json` | 同内容界面版，可在 ComfyUI 里直接打开核对与调参 |

前提：本机 ComfyUI 已装好 Qwen-Image 2.1 的三个权重文件与 `TextEncodeQwenImage21`、`QwenImage21Cache`、`ManualSigmas` 等节点；缺什么，脚本会把节点名报出来。

先探测服务：

```powershell
python scripts/comfy_run.py --probe
```

地址与字体登记在仓库根目录的 `config.local.md`（已被 `.gitignore` 排除，不与 `git pull` 冲突）：

```text
COMFYUI_URL=http://127.0.0.1:8188
MANUAL_PATH=D:/<your-path>/ComfyUI-Qwen-Image-2.1 部署与工作流手册.md
FONT_DIR=C:/Users/<you>/Fonts
FONT_STICKER=
FONT_POSTER=
FONT_BODY=
```

| 键 | 说明 |
| --- | --- |
| `COMFYUI_URL` | 服务地址，缺省 `http://127.0.0.1:8188` |
| `MANUAL_PATH` | 可选兜底：自己的部署与参数手册；只在要求按自己习惯运行时才读 |
| `FONT_DIR` | 本地字体目录 |
| `FONT_STICKER` / `FONT_POSTER` / `FONT_BODY` | 表情包配字 / 海报标题 / 推文正文的字体，写绝对路径（`.ttf` / `.otf` / `.ttc`，`.ttc` 可带 `#索引`） |

出图命令：

```powershell
python scripts/comfy_run.py --prompt "…" --size 1024x1024 --out output/a.png
python scripts/comfy_run.py --mode edit --ref assets/turnaround.png --prompt "…" --out output/b.png
```

`MANUAL_PATH` 指向的是自己的手册，**仓库不内置任何人的本地手册**，也不建议把手册放进仓库（通常含个人目录、硬件信息与私人素材路径）。

### 字体

配字在图外后期叠加，先定字体槽位：

```powershell
python scripts/font_probe.py                   # 扫本机 → output/fonts/sheet.png + 编号表
python scripts/font_probe.py --pick 9,10,29    # 按样张编号写入三个槽位
```

- 扫描顺序：`FONT_DIR` → 用户字体目录 → `C:\Windows\Fonts`；不含中文的字体会被剔除，同字族最多留两款（常规 + 粗体），`.ttc` 自动选到有中文的索引。
- 样张用同一句示例文案渲染，用户指着编号挑即可，不必记路径。
- 授权提醒：免费商用不等于可随仓库分发；微软雅黑等系统字体只能本机使用，不要提交进仓库（`fonts/` 已被忽略）。

## 4. 更新

```bash
cd david-ip-production
git pull
```

如果本地改过 `SKILL.md` 等受版本管理的文件，先 `git stash` 或在拉取后重新应用。本地手册路径写在 `config.local.md` 中，该文件不进入版本管理，更新时不受影响。

## 5. 目录约定

本 Skill 只规定「怎么生产」，不规定「产出放哪」。若同时管理多个 IP，建议在仓库之外建一个工作目录：

```text
<workspace>/
├─ <ip-name>/
│  ├─ assets/     # 三视图、主视觉（含配色与字体参考）
│  ├─ stickers/   # 表情包成品
│  ├─ posters/
│  ├─ wechat/     # HTML/CSS 组件与预览页
│  ├─ merch/
│  └─ video/
```

同一 IP 的所有产物集中在自己的目录里，三视图放在 `assets/` 最外层，便于每次生成时挂参考图。
