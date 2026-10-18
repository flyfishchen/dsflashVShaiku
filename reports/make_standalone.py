#!/usr/bin/env python3
"""把 Artifact 版报告（不含 <html>/<head>/<body> 外层）包装成可直接用浏览器打开的独立 HTML。

用法：python3 reports/make_standalone.py <artifact 版 html> [输出路径，默认 reports/eval_report.html]
"""

import sys
from pathlib import Path

RESET = """<style>
:root { color-scheme: light; padding-top: env(safe-area-inset-top, 0px); padding-bottom: env(safe-area-inset-bottom, 0px); }
body { margin: 0; }
img { max-width: 100%; }
[hidden] { display: none !important; }
</style>
"""

src = Path(sys.argv[1]).read_text(encoding="utf-8")
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent / "eval_report.html"
if src.lstrip().lower().startswith("<!doctype"):
    raise SystemExit("输入已经是完整 HTML")
i = src.index("</style>") + len("</style>")
head, body = src[:i], src[i:]
out.write_text('<!doctype html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
               '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
               + RESET + head.strip() + "\n</head>\n<body>\n" + body.strip() + "\n</body>\n</html>\n", encoding="utf-8")
print(f"已生成 {out}")
