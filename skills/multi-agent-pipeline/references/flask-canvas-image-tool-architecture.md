# Flask + Canvas 实时图像预览架构

## 适用场景

需要用户在浏览器中上传图片、调整参数、实时预览处理结果的前后端分离项目。

## 架构

```
┌─────────────────────┐       HTTP/JSON       ┌──────────────────┐
│   frontend/         │ ◄──────────────────► │   backend/        │
│   index.html        │   fetch() + FormData │   server.py       │
│   (纯 HTML+CSS+JS)  │                      │   color_utils.py  │
│                     │   /api/upload        │   kimi_client.py  │
│   Canvas 2D preview │   /api/extract-*     │                   │
│   HLS sliders       │   /api/transfer-*    │   PIL + numpy     │
└─────────────────────┘                      └──────────────────┘
```

## 后端模式

### 文件结构
```
backend/
├── server.py          # Flask routes（薄层，只做路由）
├── xxx_utils.py       # 核心逻辑（纯函数，无 Flask 依赖）
├── yyy_client.py      # 第三方 API 封装
├── requirements.txt
└── uploads/           # 临时文件缓存（内存 + 磁盘双存储）
```

### 内存图片存储模式
```python
image_store = {}  # {image_id: {'path': str, 'pil': Image, ...}}

# 上传时双写（磁盘 + 内存）
def save_upload(file):
    image_id = uuid.uuid4().hex[:12]
    filepath = os.path.join(UPLOAD_DIR, f'{image_id}.png')
    file.save(filepath)
    pil_img = Image.open(filepath)
    image_store[image_id] = {'path': filepath, 'pil': pil_img, ...}
    return {'image_id': image_id, 'width': w, 'height': h}
```

**优点**：处理请求时直接从内存取 PIL 对象，不必反复读磁盘。
**限制**：生产环境需换 Redis/DB（内存无限增长）。

### 端点设计原则
- `/api/upload` — POST multipart，返回 `{image_id, width, height}`
- `/api/images/<id>` — GET，返回原图 JPEG（用于 Canvas 绘制）
- `/api/extract-*` — POST JSON，返回 `{success, color: {rgb, hls, hex}, region}`
- `/api/transfer-*` — POST JSON，返回 `{success, result_image_id}`
- `/api/preview-*` — POST JSON，返回 `{success, image_base64}`（不存盘，快速预览）
- `/api/health` — GET 健康检查

### 格式兼容性
```python
def _normalize_hls(hls_data):
    """兼容 dict {h,l,s} 和 list [h,l,s]"""
    if isinstance(hls_data, dict):
        return (hls_data.get('h',0), hls_data.get('l',50), hls_data.get('s',50))
    if isinstance(hls_data, (list, tuple)) and len(hls_data) == 3:
        return (hls_data[0], hls_data[1], hls_data[2])
    return (0, 50, 50)
```

## 前端模式

### 单文件 SPA 布局
```
┌─toolbar: 标题 + 设置按钮────────────────────┐
├─left panel──┬──preview canvas──┬─right panel─┤
│ 源图片/取色  │  目标图/结果/对比 │ 目标图片/区域 │
│ 三模式切换   │                  │ 三模式切换    │
│ 颜色显示     │                  │ 颜色显示      │
├─────────────┴──────────────────┴─────────────┤
│ HLS 滑块: H(-180~180) | L(0~200%) | S(0~200%)│
│ [重置] [应用迁移]                              │
└──────────────────────────────────────────────┘
```

### 实时预览防抖
```javascript
let debounceTimer = null;
function debouncePreview() {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => updateResultPreview(), 300);
}
```
滑块 `oninput` → 更新 state → 300ms 防抖 → POST `/api/preview-transfer` → base64 → Canvas drawImage

### Canvas 绘制模式
- **目标图**：drawImage(targetImg)
- **结果预览**：drawImage(resultImg)
- **左右对比**：split view，左半边原图，右半边结果，中间红线分隔

```javascript
function drawSplitPreview(canvas, ctx, areaW, areaH) {
  const halfW = areaW / 2;
  // 左：目标原图
  ctx.drawImage(target, 0, (areaH - th) / 2, tw, th);
  // 中轴线
  ctx.strokeStyle = '#e94560'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(halfW, 20); ctx.lineTo(halfW, areaH-20); ctx.stroke();
  // 右：结果
  ctx.drawImage(result, halfW, (areaH - rh) / 2, rw, rh);
}
```

### API Key 设置模式
- localStorage 存储 `kimi_api_key`
- 弹窗 modal 输入 + 测试 + 保存
- 每次 API 调用时从 state 读取，不写死在前端代码

## 验证模式

```python
# 创建测试图 → upload → extract → transfer → 验证颜色变化
img = Image.new('RGB', (200, 100), 'red')
img.paste(Image.new('RGB', (100, 100), 'blue'), (100, 0))
# ... API calls ...
assert after_transfer['rgb'][0] > 100  # 原蓝色 R=0，迁移后应 >100
```

## 颜色精度注意事项

- Canvas 2D：8-bit/通道 sRGB，标准 Web 色域
- PIL/Pillow：处理时保持原始位深，输出 JPEG 时 8-bit
- 如需 PS 级别精度（10/16-bit），需换 WebGL + float texture 或桌面 PyQt
- 当前方案（Canvas 8-bit）对 99% 日常场景足够

## numpy 矢量化 HLS 避坑：除零警告

矢量化 RGB→HLS 时，`np.where(cond, x/y, fallback)` 会**先求值 x/y 再判断条件**，导致 `diff=0` 的像素仍然触发除零：

```python
# ❌ 错误：diff=0 时 ((g-b)/diff) 仍被求值 → RuntimeWarning
h_arr = np.where(mask & (max_rgb == r), ((g - b) / diff) % 6, h_arr)

# ✅ 正确：用 safe_diff 替换 0 值为 1.0（反正 mask 会筛掉这些像素）
safe_diff = np.where(diff < 1e-10, 1.0, diff)
h_arr = np.where(mask & (max_rgb == r), ((g - b) / safe_diff) % 6, h_arr)
```

**触发场景**：灰色区域（R=G=B → diff=0）、纯白、纯黑。日志中会刷屏 `RuntimeWarning: invalid value encountered in divide`。
