#!/usr/bin/env python3
"""david-ip-production · 字体定位

扫本机字体 → 过滤掉不含中文的 → 按风格归类 → 渲一张样张 → 一键写进 config.local.md 的三个语义槽位。

用法：
  python font_probe.py                                  # 出样张 + 候选表
  python font_probe.py --text "就是这个" --limit 24      # 换示例文案、限数量
  python font_probe.py --pick 3,7,12 --slots FONT_STICKER,FONT_POSTER,FONT_BODY

槽位含义：
  FONT_STICKER  表情包配字（粗、圆、笔画重）
  FONT_POSTER   海报标题与卖点
  FONT_BODY     推文正文与说明

依赖：Pillow、fontTools（缺 fontTools 时不做中文覆盖检测与风格识别，只按文件名归类）
"""

import argparse
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SLOTS = ("FONT_STICKER", "FONT_POSTER", "FONT_BODY")

# 展示顺序即下表顺序；匹配按本表逐条尝试
STYLE_RULES = (
    ("黑体", r"黑|hei|gothic|yahei|sans|pingfang|harmony|alibaba|puwei|sourcehan|等线|deng|arial|helvetica|segoe|verdana|tahoma|calibri|noto sans"),
    ("圆体", r"圆|yuan|round|maru|pop|soft"),
    ("标题/展示", r"综艺|海报|标题|display|impact|bebas|smiley|得意|deyi|zcool|站酷|logo|poster|ultra|super"),
    ("手写/楷", r"楷|kai|hand|brush|script|行书|隶|书法|行楷|毛笔|marker|comic"),
    ("宋体/明朝", r"宋|song|serif|ming|mincho|sung|times|georgia|garamond|antiqua|bodoni|bookman|palatino|仿宋"),
    ("其它", r""),
)
STYLE_ORDER = {style: i for i, (style, _) in enumerate(STYLE_RULES)}
STYLE_NOISE = r"(?:regular|bold|italic|oblique|light|medium|demibold|semi|thin|black|heavy|condensed|narrow|book|roman|mt|fb|itc)"


def read_config():
    cfg = {}
    path = ROOT / "config.local.md"
    if path.is_file():
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                cfg[key.strip()] = value.strip().strip('"').strip("'")
    return cfg


def guess_style(name, filename):
    blob = f"{name} {filename}".lower()
    for style, pattern in STYLE_RULES:
        if pattern and re.search(pattern, blob):
            return style
    return "其它"


def family_key(name):
    return re.sub(r"[\s\-_]+", "", re.sub(STYLE_NOISE, "", name.lower(), flags=re.I)) or name.lower()


def font_faces(path):
    if path.suffix.lower() != ".ttc":
        return [0]
    try:
        from fontTools.ttLib import TTCollection

        with TTCollection(str(path), lazy=True) as collection:
            return list(range(len(collection.fonts)))
    except Exception:  # noqa: BLE001
        return [0]


def face_info(path, index, cjk):
    name, missing, cjk_ok = path.stem, set(), False
    try:
        from fontTools.ttLib import TTFont

        font = TTFont(str(path), fontNumber=index, lazy=True)
        full = font["name"].getDebugName(4) or font["name"].getDebugName(1)
        name = full if full and full.strip("_ ") else path.stem
        cmap = font.getBestCmap() or {}
        missing = {ch for ch in cjk if ord(ch) not in cmap}
        cjk_ok = bool(cmap)
        font.close()
    except Exception:  # noqa: BLE001
        pass
    return name, "".join(sorted(missing)), cjk_ok


def collect(cfg, limit, text):
    cjk = [ch for ch in text if ord(ch) > 127] or ["字"]
    dirs = [d for d in (Path(cfg["FONT_DIR"]) if cfg.get("FONT_DIR") else None,) if d and d.is_dir()]
    dirs += [
        Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts",
        Path("C:/Windows/Fonts"),
    ]

    seen_names, family_hits, rows = set(), {}, []
    for directory in dirs:
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*")):
            if path.suffix.lower() not in (".ttf", ".otf", ".ttc") or path.name.lower() in seen_names:
                continue
            seen_names.add(path.name.lower())
            for index in font_faces(path):
                name, missing, cjk_ok = face_info(path, index, cjk)
                if cjk_ok and missing:
                    continue  # 中文缺字，直接剔除
                key = family_key(name)
                if family_hits.get(key, 0) >= 2:
                    continue  # 同一字族最多留常规 + 粗体两款
                family_hits[key] = family_hits.get(key, 0) + 1
                rows.append(
                    {"path": path, "index": index, "name": name, "style": guess_style(name, path.stem), "missing": missing}
                )
                break
    rows.sort(key=lambda r: (STYLE_ORDER.get(r["style"], 99), r["name"]))
    return rows[:limit]


def label_font(size):
    for candidate in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"):
        try:
            return ImageFont.truetype(candidate, size, index=0)
        except Exception:  # noqa: BLE001
            continue
    return ImageFont.load_default()


def render_sheet(rows, out_path, text, size):
    cols, cell_w, cell_h, pad = 3, 640, 250, 16
    canvas = Image.new("RGB", (cols * cell_w + pad, ((len(rows) + cols - 1) // cols) * cell_h + pad), "white")
    draw = ImageDraw.Draw(canvas)
    small = label_font(18)

    for i, row in enumerate(rows):
        x = pad + (i % cols) * cell_w
        y = pad + (i // cols) * cell_h
        draw.rectangle([x, y, x + cell_w - pad, y + cell_h - pad], outline=(228, 228, 228))
        try:
            font = ImageFont.truetype(str(row["path"]), size, index=row["index"])
            draw.text((x + 18, y + 18), text, font=font, fill=(20, 20, 20))
        except Exception as exc:  # noqa: BLE001
            draw.text((x + 18, y + 70), f"无法渲染：{exc}", font=small, fill=(200, 60, 60))
        draw.text((x + 18, y + cell_h - 80), f"[{i + 1:02d}] {row['style']}", font=small, fill=(60, 90, 200))
        draw.text((x + 18, y + cell_h - 56), row["name"][:34], font=small, fill=(120, 120, 120))
        draw.text((x + 18, y + cell_h - 34), row["path"].name[:40], font=small, fill=(170, 170, 170))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)
    return out_path


def write_config(picks, slots):
    path = ROOT / "config.local.md"
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines() if path.is_file() else []
    mapping = dict(zip(slots, picks))
    for slot, row in mapping.items():
        value = row["path"].as_posix() + (f"#{row['index']}" if row["index"] else "")
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{slot}="):
                lines[i] = f"{slot}={value}"
                break
        else:
            lines.append(f"{slot}={value}")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return mapping


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default="就是这个·真不错 ABC123")
    parser.add_argument("--limit", type=int, default=48)
    parser.add_argument("--size", type=int, default=44, help="样张字号")
    parser.add_argument("--out", default="output/fonts/sheet.png")
    parser.add_argument("--pick", default="", help="样张编号，逗号分隔，如 3,7,12")
    parser.add_argument("--slots", default=",".join(SLOTS))
    parser.add_argument("--list-only", action="store_true")
    args = parser.parse_args()

    rows = collect(read_config(), args.limit, args.text)
    if not rows:
        print("没有找到含中文的字体：请在 config.local.md 填 FONT_DIR，或安装中文字体")
        return 1

    for i, row in enumerate(rows, start=1):
        print(f"[{i:02d}] {row['style']:<6} {row['name']}  ({row['path'].name}{'#' + str(row['index']) if row['index'] else ''})")

    if not args.list_only:
        sheet = render_sheet(rows, ROOT / args.out, args.text, args.size)
        print(f"样张：{sheet.resolve()}")
        print("→ 让用户从样张挑序号，再执行 --pick")

    if args.pick:
        picks = [int(x) for x in re.split(r"[,，\s]+", args.pick.strip()) if x]
        slots = [s.strip() for s in args.slots.split(",") if s.strip()]
        if len(picks) != len(slots):
            raise SystemExit(f"--pick 给了 {len(picks)} 个，--slots 有 {len(slots)} 个，数量要一致")
        for slot in slots:
            if slot not in SLOTS:
                raise SystemExit(f"未知槽位：{slot}（可用：{', '.join(SLOTS)}）")
        if any(not 1 <= p <= len(rows) for p in picks):
            raise SystemExit(f"编号超出范围：1–{len(rows)}")
        for slot, row in write_config([rows[p - 1] for p in picks], slots).items():
            print(f"{slot} = {row['name']}（{row['path'].as_posix()}）")
        print("已写入 config.local.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
