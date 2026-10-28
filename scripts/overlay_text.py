#!/usr/bin/env python3
"""david-ip-production · 后期叠字 / 叠标识

在已生成的图上叠加中文配字或 logo，图内不生成文字，改字只重跑本脚本。
依赖：Pillow（pip install pillow）

表情包示例：
  python overlay_text.py --base in/01.png --text "就是这个" --font C:/fonts/SmileySans-Oblique.ttf ^
      --size 0.09 --color "#2F80ED" --stroke 0.006 --stroke-color "#FFFFFF" --anchor right-center --out out/01.png

多列竖排：--text "先这样|再那样" 用 | 分列，自右向左排列。
叠 logo：--logo brand.png --logo-anchor bottom-right --logo-size 0.16
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ANCHORS = {
    "left-top": (0.0, 0.0),
    "mid-top": (0.5, 0.0),
    "right-top": (1.0, 0.0),
    "left-center": (0.0, 0.5),
    "center": (0.5, 0.5),
    "right-center": (1.0, 0.5),
    "left-bottom": (0.0, 1.0),
    "mid-bottom": (0.5, 1.0),
    "right-bottom": (1.0, 1.0),
}


def load_font(path, size, index):
    return ImageFont.truetype(str(path), size, index=index)


def char_boxes(font, chars):
    return [font.getbbox(c) for c in chars]


def wrap_vertical(chars, font, max_height, line_gap):
    columns, current, used = [], [], 0
    for char in chars:
        box = font.getbbox(char)
        height = box[3] - box[1]
        step = height + line_gap
        if current and used + step > max_height:
            columns.append(current)
            current, used = [], 0
        current.append(char)
        used += step
    if current:
        columns.append(current)
    return columns


def draw_vertical(draw, text, font, anchor, margin_x, margin_y, line_gap, col_gap, fill, stroke_width, stroke_fill):
    columns = [list(line) for line in text.split("|") if line] or [list(text)]
    width, height = draw._image.size  # noqa: SLF001
    columns = [c for line in columns for c in wrap_vertical(line, font, height - 2 * margin_y, line_gap)]

    col_widths = [max(font.getbbox(c)[2] - font.getbbox(c)[0] for c in col) for col in columns]
    col_heights = [
        sum(font.getbbox(c)[3] - font.getbbox(c)[1] for c in col) + line_gap * (len(col) - 1) for col in columns
    ]
    block_w = sum(col_widths) + col_gap * (len(columns) - 1)
    block_h = max(col_heights)

    ax, ay = ANCHORS[anchor]
    left = margin_x + (width - 2 * margin_x - block_w) * ax
    top = margin_y + (height - 2 * margin_y - block_h) * ay

    for i, col in enumerate(columns):
        x = left + sum(col_widths[:i]) + col_gap * i + (col_widths[i] - max(
            font.getbbox(c)[2] - font.getbbox(c)[0] for c in col)) / 2
        y = top + (block_h - col_heights[i]) * ay
        for char in col:
            box = font.getbbox(char)
            draw.text(
                (x - box[0], y - box[1]),
                char,
                font=font,
                fill=fill,
                stroke_width=stroke_width,
                stroke_fill=stroke_fill,
            )
            y += (box[3] - box[1]) + line_gap


def draw_horizontal(draw, text, font, anchor, margin_x, margin_y, line_gap, fill, stroke_width, stroke_fill):
    width, height = draw._image.size  # noqa: SLF001
    lines = text.replace("|", "\n").split("\n")
    boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    sizes = [(b[2] - b[0], b[3] - b[1]) for b in boxes]
    block_w = max(w for w, _ in sizes)
    block_h = sum(h for _, h in sizes) + line_gap * (len(lines) - 1)

    ax, ay = ANCHORS[anchor]
    left = margin_x + (width - 2 * margin_x - block_w) * ax
    top = margin_y + (height - 2 * margin_y - block_h) * ay

    for line, box, (w, h) in zip(lines, boxes, sizes):
        x = left + (block_w - w) * ax - box[0]
        draw.text(
            (x, top - box[1]),
            line,
            font=font,
            fill=fill,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
        )
        top += h + line_gap


def paste_logo(canvas, logo_path, anchor, size_ratio, margin_ratio):
    logo = Image.open(logo_path).convert("RGBA")
    width, height = canvas.size
    target_w = int(width * size_ratio)
    target_h = max(1, int(logo.height * target_w / logo.width))
    logo = logo.resize((target_w, target_h), Image.LANCZOS)
    margin_x, margin_y = int(width * margin_ratio), int(height * margin_ratio)
    ax, ay = ANCHORS[anchor]
    left = margin_x + (width - 2 * margin_x - target_w) * ax
    top = margin_y + (height - 2 * margin_y - target_h) * ay
    canvas.alpha_composite(logo, (int(left), int(top)))
    return canvas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--text", default="")
    parser.add_argument("--font", default=None, help="字体文件绝对路径（.ttf/.otf/.ttc）")
    parser.add_argument("--font-index", type=int, default=0, help="ttc 字体集合内的序号")
    parser.add_argument("--direction", choices=["vertical", "horizontal"], default="vertical")
    parser.add_argument("--anchor", choices=list(ANCHORS), default="right-center")
    parser.add_argument("--size", type=float, default=0.09, help="字号 = 画布高度 × 该比例")
    parser.add_argument("--color", default="#2F80ED")
    parser.add_argument("--stroke", type=float, default=0.006, help="描边宽度 = 画布高度 × 该比例，0 为不描边")
    parser.add_argument("--stroke-color", default="#FFFFFF")
    parser.add_argument("--margin", type=float, default=0.06, help="边距 = 画布宽/高 × 该比例")
    parser.add_argument("--line-gap", type=float, default=0.02)
    parser.add_argument("--col-gap", type=float, default=0.04)
    parser.add_argument("--logo", default=None)
    parser.add_argument("--logo-anchor", choices=list(ANCHORS), default="right-bottom")
    parser.add_argument("--logo-size", type=float, default=0.16, help="logo 宽度 = 画布宽度 × 该比例")
    args = parser.parse_args()

    if args.text and not args.font:
        raise SystemExit("叠加文字需要 --font：给出字体文件路径")

    canvas = Image.open(args.base).convert("RGBA")
    width, height = canvas.size

    if args.text:
        font = load_font(args.font, max(8, int(height * args.size)), args.font_index)
        draw = ImageDraw.Draw(canvas)
        margin_x, margin_y = int(width * args.margin), int(height * args.margin)
        line_gap = int(height * args.line_gap)
        stroke_width = int(height * args.stroke)
        if args.direction == "vertical":
            draw_vertical(
                draw, args.text, font, args.anchor, margin_x, margin_y, line_gap,
                int(width * args.col_gap), args.color, stroke_width, args.stroke_color,
            )
        else:
            draw_horizontal(
                draw, args.text, font, args.anchor, margin_x, margin_y, line_gap,
                args.color, stroke_width, args.stroke_color,
            )

    if args.logo:
        canvas = paste_logo(canvas, args.logo, args.logo_anchor, args.logo_size, args.margin)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    print(f"已保存：{out.resolve()}")


if __name__ == "__main__":
    main()
