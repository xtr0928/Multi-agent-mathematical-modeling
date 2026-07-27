# Flask 大图上传最佳实践

> 适用：Flask 后端处理用户上传图片，尤其是 >10MB 或 >4096px 的场景。

## 配置三步

```python
from PIL import Image
from flask import Flask

app = Flask(__name__)

# 1) 上传大小上限（默认无限制）
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB

# 2) PIL 像素安全上限（默认 ~89M 像素）
Image.MAX_IMAGE_PIXELS = 100_000_000  # ~11500×8700

# 3) 413 自定义错误
@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': '文件过大，最大支持 200MB'}), 413
```

## save_upload 自动缩放

```python
def save_upload(file, max_dim=4096):
    """保存上传，>max_dim 自动等比缩放"""
    file.save(filepath)
    pil_img = Image.open(filepath)  # 惰性加载，不立即解码全部像素
    w, h = pil_img.size

    if max(w, h) > max_dim:
        ratio = max_dim / max(w, h)
        pil_img = pil_img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
        pil_img.save(filepath, quality=90)  # 替换原文件

    pil_img = pil_img.convert('RGBA')  # 统一格式
    return {..., 'resized': max(w, h) > max_dim}
```

## 格式校验

```python
ALLOWED = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff'}
ext = os.path.splitext(file.filename)[1].lower()
if ext not in ALLOWED:
    return jsonify({'error': f'不支持 {ext}'}), 400
```

## 异常捕获

```python
try:
    info = save_upload(file)
except MemoryError:
    return jsonify({'error': '像素过大，内存不足'}), 413
except Exception as e:
    return jsonify({'error': str(e)}), 500
```

## 常见问题

| 问题 | 原因 | 修复 |
|------|------|------|
| 上传 100MB 图失败 | Flask 无 MAX_CONTENT_LENGTH | 设为 200MB |
| PIL 报 `DecompressionBombError` | 默认像素上限 89M | `Image.MAX_IMAGE_PIXELS = 100M` |
| 10000×8000 的图爆内存 | RGBA 解码后 ~320MB | 上传时缩放到 4096px |
| 用户不知道为啥失败 | 500 通用错误 | 区分 413(太大) / MemoryError / 格式错误 |
