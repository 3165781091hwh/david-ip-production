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

## 3. 本地生图手册登记（可选）

`SKILL.md` 的「本地生图：条件读取外部手册」一节留了占位符：

```text
<your-local-generation-manual>
```

只有当你在对话中明确说「我需要本地生图」时，Agent 才会去读这份手册。要启用它：

1. 准备你自己的 ComfyUI + Qwen-Image 2.1 部署与工作流手册（Markdown）。
2. 把占位符替换为真实路径，建议使用正斜杠的绝对路径：

```text
D:/<your-path>/ComfyUI-Qwen-Image-2.1 部署与工作流手册.md
```

3. 手册无法读取时，Agent 会主动向你要新路径——把新路径写回 `SKILL.md` 即可。

**仓库不内置任何人的本地手册**，也不建议把手册放进仓库（通常含个人目录、硬件信息与私人素材路径）。

## 4. 更新

```bash
cd david-ip-production
git pull
```

如果本地改过 `SKILL.md`（例如已填好手册路径），先 `git stash` 或在拉取后重填该处。

## 5. 目录约定

本 Skill 只规定「怎么生产」，不规定「产出放哪」。若同时管理多个 IP，建议在仓库之外建一个工作目录：

```text
<workspace>/
├─ <ip-name>/
│  ├─ assets/     # 三视图、主视觉、配色板
│  ├─ stickers/   # 表情包成品
│  ├─ posters/
│  ├─ wechat/     # HTML/CSS 组件与预览页
│  ├─ merch/
│  └─ video/
```

同一 IP 的所有产物集中在自己的目录里，三视图放在 `assets/` 最外层，便于每次生成时挂参考图。
