# Flask 大图片上传防爆模式

## 问题

用户上传 JPG/PNG，文件可达 100MB，像素可达 10000×8000。
Flask 默认无上限，PIL 默认限制 89M 像素，直接 `Image.open().convert()` 爆内存。

## 四件套

```python
from PIL import Image
from flask import Flask

app = Flask(__name__)

# 1. 上传大小上限
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB

# 2. PIL 像素安全上限（Flask config 不管用，必须设 PIL 自己的）
Image.MAX_IMAGE_PIXELS = 100_000_000  # 1亿像素 ≈ 11500×8700

# 3. 413 友好报错
@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': '文件过大，最大支持 200MB'}), 413

# 4. 上传时自动缩放到安全尺寸
def save_upload(file, max_dim=4096):
    file.save(filepath)
    img = Image.open(filepath)  # 惰性加载，不立即解码
    w, h = img.size
    if max(w, h) > max_dim:
        ratio = max_dim / max(w, h)
        img = img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
        img.save(filepath, quality=90)  # 覆盖原文件
    img = img.convert('RGBA')  # 统一格式
    ...
```

## 关键点

- `Image.open()` 是惰性的，不会立即加载像素 → 先检查 size 再决定是否缩放
- `MAX_IMAGE_PIXELS` 是 PIL 模块级常量，不是 Flask config
- `MAX_CONTENT_LENGTH` 单位是字节
- 缩放后覆盖原文件节省磁盘
- `convert('RGBA')` 放最后，避免缩放前就消耗内存

## 格式白名单

```python
ALLOWED = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff'}
ext = os.path.splitext(file.filename)[1].lower()
if ext not in ALLOWED:
    return jsonify({'error': f'不支持 {ext}'}), 400
```
