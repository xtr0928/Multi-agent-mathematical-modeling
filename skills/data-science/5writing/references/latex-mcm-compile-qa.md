# LaTeX 美赛论文编译与排版 QA 实战（2026-08 MCM Problem C 实测）

在 5writing 的 `templates/en/mcm-latex/` 模板上跑通 xelatex 编译 + PDF 排版 QA 的全套经验。

## 1. Windows 无 LaTeX 环境：MiKTeX 便携版安装（免管理员）

```bash
# 清华镜像下载 setup 工具（约 2.7MB）
curl -sL -o miktexsetup.zip "https://mirrors.tuna.tsinghua.edu.cn/CTAN/systems/win32/miktex/setup/windows-x64/miktexsetup-5.5.0%2B1763023-x64.zip"
unzip -o -q miktexsetup.zip -d miktexsetup
cd miktexsetup
# 两步：先下载包仓库，再安装到便携目录
./miktexsetup_standalone.exe --local-package-repository=/c/tools/miktex-repo --package-set=essential --shared=no --verbose download
./miktexsetup_standalone.exe --local-package-repository=/c/tools/miktex-repo --package-set=essential --shared=no --verbose install --portable=/c/tools/miktex
# 用 PATH 指向便携 bin（每次编译前 export）
export PATH="/c/tools/miktex/texmfs/install/miktex/bin/x64:$PATH"
```
- 注意 `--portable` 参数在 `install` 子命令；下载和安装是两个独立命令。
- essential 包集会缺一些宏包，首次编译时 MiKTeX 会自动从网络补装，**首次编译很慢（可能 >5min）**，必须 background=true + notify_on_complete。
- 中文模板用 xelatex（fontspec 需要 XeTeX）；英文模板同样 xelatex 两遍。

## 2. xelatex 编译纪律

```bash
xelatex -interaction=nonstopmode main.tex   # 跑两遍解决交叉引用
```
- 退出码 1 不一定是错误：MiKTeX 的 "So far, you have not checked for MiKTeX updates" 会以 exit 1 退出但 PDF 已生成。看 `Output written on main.pdf (N pages)` 判断成功。
- `&&` 链在 exit 1 时中断第二遍 → 两遍分开跑或用 `;`。
- 编译超时首选 background + notify_on_complete，不要前台等。

## 3. listings 代码块黑底 bug（严重，OCR 检查才发现）

- **现象**：`\lstset{backgroundcolor=\color[gray]{0.97}}` 在未加载 xcolor 的上下文中渲染成整块黑色，代码不可读，边缘漏出 `[gray]0.97` 字样。
- **修复**：
```latex
\usepackage{xcolor}
\lstset{
  frame=single, framerule=0.4pt, framesep=4pt,
  basicstyle=\ttfamily\small,
  backgroundcolor=\color{white},
  breaklines=true, breakatwhitespace=false,
  columns=fullflexible, keepspaces=true,
}
```
- 教训：**写完 PDF 必须渲染页面目检**，编译通过 ≠ 排版正确。

## 4. 孤立页 / 大面积空白（\pagebreak[100] 的坑）

- **现象**：每节前 `\pagebreak[100]`（强制分页）导致某节末尾溢出的 1 个 bullet 单独成页（一页 90% 空白）。
- **修复**：删掉章节间全部 `\pagebreak[100]`（美赛不要求每节新页），内容自然流动，24 页 → 19 页，空白页全消。
- 浮动体参数 `[htbp]` → `[H]`（float 宏包）强制就地，可消除表格/图被推走造成的空洞；同时调 `\renewcommand{\topfraction}{0.9}` 等放宽浮动阈值。
- `\pagebreak[100]` 保留在 References / Appendices 前即可。

## 5. PDF 排版 QA 工作流（OCR 页面检查）

```python
import fitz
doc = fitz.open('main.pdf')
for i in range(len(doc)):
    doc[i].get_pixmap(dpi=80).save(f'p{i+1:02d}.png')
```
- 渲染后逐页 vision_analyze 检查：表格溢出 / 代码块黑底 / 孤立页空白 / 中文标签混排 / 图偏小。
- 程序化扫描：`p.get_text()` 长度 <200 且无图 = 疑似空白页；像素均值 <60 占比 >30% = 疑似黑块。
- 检查清单：页眉 `Team #N | Page X of Y`、Summary Sheet 三栏、图编号引用闭环、关键数字齐全。
- **英文论文的图内文字必须全英文**：matplotlib 图里的中文标签（"评委 vs 粉丝"）在英文论文里是明显扣分项——生成图时用英文标签，或出图后重新生成。2026-C 实测：图 3 子图中文标签漏网，评委视角一眼可见。
- **`\TotalPages` 必须与最终实际页数一致**：模板里写死 `of 25` 而实际 19 页 → 页眉页码与实际不符，提交前 grep 核对（`grep -n "TotalPages" main.tex` 改掉）。

## 6. 数字一致性核对（评委 HARD FAIL #2）

- 论文写完必须核对正文/摘要所有关键数字与代码输出一致。
- 反演模型改约束逻辑后可行性率会变（97.7% → 93.1%），必须重跑全链路并全局替换过期数字（`sed`/脚本 replace 后重新编译验证 0 残留）。
- 快速核对脚本：提取 PDF 全文，assert 每个关键数字出现；摘要数字密度应 ≥20 个。

## 7. 无 LaTeX 时的兜底：Edge headless 打印 HTML → PDF

```bash
"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --headless --disable-gpu \
  --print-to-pdf="C:\path\out.pdf" --no-pdf-header-footer "file:///C:/path/report.html"
```
- 适合快速出中文报告；但美赛要求英文 + 标准模板时仍应上 LaTeX。
- Edge 会锁 PDF 文件（WPS/Acrobat 打开也会锁）→ 改名输出或先关预览程序。
