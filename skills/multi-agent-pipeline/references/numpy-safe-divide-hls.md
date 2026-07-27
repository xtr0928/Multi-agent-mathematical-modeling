# numpy `np.where` 防除零：safe_diff 模式

> 适用：任何用 numpy 做矢量化 RGB↔HLS（或其他色彩空间）转换的场景。

## 问题

`np.where(condition, expr_A, expr_B)` 在 Python 层面会**先求值 expr_A 和 expr_B**，再根据 condition 选择。即使 `diff=0` 时 `condition=False`，`expr_A` 中的除法仍会执行，产生 RuntimeWarning：

```
RuntimeWarning: invalid value encountered in divide
  ((g - b) / diff) % 6,
```

## 修复：safe_diff 代替 diff

```python
# ❌ 坏：diff 可能为零，np.where 仍会求值除法分支
h_arr = np.where(
    mask & (max_rgb == r),
    ((g - b) / diff) % 6,   # diff=0 时仍被求值 → 警告
    h_arr
)

# ✅ 好：用 safe_diff 替换，零值处填 1.0（反正 mask 会排除）
safe_diff = np.where(diff < 1e-10, 1.0, diff)
h_arr = np.where(
    mask & (max_rgb == r),
    ((g - b) / safe_diff) % 6,  # safe_diff 永远 ≥ 1e-10
    h_arr
)
```

## 原理

- `mask = diff > 1e-10` 已经标记了有效像素
- 被 mask 排除的像素（diff≈0 即纯灰色），其色相无意义，用任意值填充即可
- `safe_diff` 把无效像素的除数设为 1.0，避免除零，而 mask 保证这些值不会被实际使用

## 完整 HLS 矢量化骨架

```python
import numpy as np

def rgb_to_hls_vectorized(pixels):
    """pixels: (h, w, 3) float32 [0,1]"""
    r, g, b = pixels[:,:,0], pixels[:,:,1], pixels[:,:,2]
    max_rgb = np.maximum(np.maximum(r, g), b)
    min_rgb = np.minimum(np.minimum(r, g), b)
    diff = max_rgb - min_rgb

    l_arr = (max_rgb + min_rgb) / 2.0

    # 饱和度 — 也用 safe 模式
    denom = np.where(l_arr <= 0.5, max_rgb + min_rgb, 2.0 - max_rgb - min_rgb)
    denom = np.where(denom == 0, 1e-10, denom)
    s_arr = np.where(diff == 0, 0.0, diff / denom)

    # 色相 — safe_diff 防除零
    safe_diff = np.where(diff < 1e-10, 1.0, diff)
    h_arr = np.zeros_like(r)
    mask = diff > 1e-10

    h_arr = np.where(mask & (max_rgb == r), ((g - b) / safe_diff) % 6, h_arr)
    h_arr = np.where(mask & (max_rgb == g), ((b - r) / safe_diff) + 2, h_arr)
    h_arr = np.where(mask & (max_rgb == b), ((r - g) / safe_diff) + 4, h_arr)

    h_arr = h_arr / 6.0
    h_arr = np.where(h_arr < 0, h_arr + 1.0, h_arr)

    return h_arr, l_arr, s_arr
```

## 其他替代方案（不推荐）

- `np.divide(a, b, out=..., where=mask)` — 语法复杂，且 `out` 参数与 `np.where` 组合时不直观
- `np.errstate(divide='ignore')` — 隐藏警告但 NaN 仍会传播到下游计算
- 逐像素 Python 循环 — 太慢，不适用于大图
