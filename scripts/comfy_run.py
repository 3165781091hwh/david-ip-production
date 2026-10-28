#!/usr/bin/env python3
"""david-ip-production · ComfyUI 提交器（Qwen-Image 2.1 Turbo，纯标准库）

把随附工作流提交到本机 ComfyUI，轮询结果并下载成图。

用法：
  python comfy_run.py --probe
  python comfy_run.py --prompt "提示词" --size 1024x1024 --out out/a.png
  python comfy_run.py --mode edit --ref 三视图.png --ref logo.png --prompt "提示词" --out out/b.png

要点：
  - 参考图按顺序进入 images.image_1、image_2…：图1 形象锚点，图2 标识/产品，图3 起其它（最多 16 张）。
  - 编辑模式下输出尺寸跟随参考图，--size 只在文生图模式（t2i）生效。
  - 服务地址取 --server，其次 config.local.md 的 COMFYUI_URL，再次 127.0.0.1:8188。
"""

import argparse
import json
import random
import sys
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = {
    "t2i": ROOT / "workflows" / "qwen21-t2i.api.json",
    "edit": ROOT / "workflows" / "qwen21-edit.api.json",
}


def log(msg):
    print(msg, flush=True)


def read_config():
    cfg = {}
    path = ROOT / "config.local.md"
    if path.is_file():
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            cfg[key.strip()] = value.strip().strip('"').strip("'")
    return cfg


def request(url, data=None, headers=None, method=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def get_json(url, timeout=15):
    return json.loads(request(url, timeout=timeout).decode("utf-8"))


def multipart(fields, files):
    boundary = "----davidip" + uuid.uuid4().hex
    body = b""
    for key, value in fields.items():
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
    for key, (filename, payload, ctype) in files.items():
        body += (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'
            f"Content-Type: {ctype}\r\n\r\n"
        ).encode() + payload + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


def upload_image(server, path):
    path = Path(path)
    ext = path.suffix.lower()
    ctype = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(ext, "image/png")
    body, boundary = multipart(
        {"overwrite": "true", "type": "input"},
        {"image": (path.name, path.read_bytes(), ctype)},
    )
    raw = request(
        f"{server}/upload/image",
        data=body,
        headers={"Content-Type": boundary},
        method="POST",
    )
    info = json.loads(raw.decode("utf-8"))
    name = info.get("name", path.name)
    subfolder = info.get("subfolder") or ""
    return f"{subfolder}/{name}" if subfolder else name


def node_id(tpl, class_type):
    for key, node in tpl.items():
        if node.get("class_type") == class_type:
            return key
    raise SystemExit(f"工作流模板里找不到节点：{class_type}")


def submit(server, tpl):
    payload = json.dumps({"prompt": tpl, "client_id": "david-ip-production"}).encode()
    raw = request(
        f"{server}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
        timeout=30,
    )
    return json.loads(raw.decode("utf-8"))


def wait(server, prompt_id, timeout=900):
    deadline = time.time() + timeout
    while time.time() < deadline:
        history = get_json(f"{server}/history/{prompt_id}")
        entry = history.get(prompt_id)
        if entry and entry.get("outputs"):
            return entry
        time.sleep(2)
    raise SystemExit(f"超时未完成：{prompt_id}")


def download(server, entry, out_path):
    images = []
    for node_out in entry.get("outputs", {}).values():
        images.extend(node_out.get("images", []))
    if not images:
        raise SystemExit("工作流执行完成，但没有图像输出")
    image = images[0]
    query = urllib.parse.urlencode(
        {"filename": image["filename"], "subfolder": image.get("subfolder", ""), "type": image.get("type", "output")}
    )
    data = request(f"{server}/view?{query}")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true", help="只探测服务，不提交")
    parser.add_argument("--server", default=None)
    parser.add_argument("--mode", choices=["t2i", "edit"], default="t2i")
    parser.add_argument("--prompt", default="")
    parser.add_argument("--negative", default="")
    parser.add_argument("--ref", action="append", default=[], help="参考图，可多次给出，按顺序传递")
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--prefix", default=None)
    parser.add_argument("--out", default="output/result.png")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--dry-run", action="store_true", help="只打印将提交的 JSON")
    args = parser.parse_args()

    cfg = read_config()
    server = (args.server or cfg.get("COMFYUI_URL") or "http://127.0.0.1:8188").rstrip("/")

    try:
        stats = get_json(f"{server}/system_stats")
    except Exception as exc:  # noqa: BLE001
        log(f"未连通 {server}：{exc}")
        log("→ 请确认 ComfyUI 已启动，或用 --server / COMFYUI_URL 给出地址")
        return 1

    device = (stats.get("devices") or [{}])[0].get("name", "unknown")
    log(f"已连通 {server} · ComfyUI {stats['system'].get('comfyui_version')} · {device}")
    if args.probe:
        return 0

    template = json.loads(TEMPLATES[args.mode].read_text(encoding="utf-8"))
    seed = args.seed if args.seed is not None else random.randint(0, 2**48)
    prefix = args.prefix or f"david_ip/{args.mode}"

    enc = node_id(template, "TextEncodeQwenImage21")
    template[enc]["inputs"]["prompt"] = args.prompt
    template[enc]["inputs"]["negative_prompt"] = args.negative
    template[node_id(template, "RandomNoise")]["inputs"]["noise_seed"] = seed
    template[node_id(template, "SaveImage")]["inputs"]["filename_prefix"] = prefix

    if args.mode == "t2i":
        width, height = (int(x) for x in args.size.lower().split("x"))
        template[node_id(template, "EmptyLatentImage")]["inputs"].update({"width": width, "height": height})
    else:
        if not args.ref:
            raise SystemExit("edit 模式至少需要一张参考图：--ref 三视图.png")
        if len(args.ref) > 16:
            raise SystemExit("参考图最多 16 张")
        template.pop("470", None)
        for index, ref in enumerate(args.ref, start=1):
            if not Path(ref).is_file():
                raise SystemExit(f"参考图不存在：{ref}")
            name = Path(ref).name if args.dry_run else upload_image(server, ref)
            load_id = str(900 + index)
            template[load_id] = {"class_type": "LoadImage", "inputs": {"image": name}}
            template[enc]["inputs"][f"images.image_{index}"] = [load_id, 0]

    if args.dry_run:
        log(json.dumps(template, ensure_ascii=False, indent=2))
        return 0

    result = submit(server, template)
    prompt_id = result["prompt_id"]
    if result.get("node_errors"):
        log("工作流校验未通过：")
        log(json.dumps(result["node_errors"], ensure_ascii=False, indent=2))
        log("→ 缺少的节点通常是自定义节点未安装，把节点名告知用户，不要擅自安装")
        return 2

    log(f"已提交 {prompt_id} · seed {seed}")
    entry = wait(server, prompt_id, args.timeout)
    if entry.get("status", {}).get("status_str") not in (None, "success"):
        log(json.dumps(entry.get("status"), ensure_ascii=False))
        return 3
    saved = download(server, entry, args.out)
    log(f"完成：{saved.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
