#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hash_results.py — 扫描 results/*.json 生成 manifest.json
v4.0 证据门禁第一步：每个结果文件记录 sha256 + mtime + 关键指标摘要
"""
import json, os, sys, hashlib, datetime

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def main(results_dir, out_path):
    manifest = {'generated_at': datetime.datetime.now().isoformat(), 'files': {}}
    if not os.path.isdir(results_dir):
        print(f'ERR: {results_dir} 不存在')
        sys.exit(1)
    for fname in sorted(os.listdir(results_dir)):
        if not fname.endswith('.json'):
            continue
        path = os.path.join(results_dir, fname)
        st = os.stat(path)
        manifest['files'][fname] = {
            'sha256': sha256(path),
            'mtime': datetime.datetime.fromtimestamp(st.st_mtime).isoformat(),
            'size': st.st_size,
        }
    with open(out_path, 'w') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    n = len(manifest['files'])
    print(f'[manifest] {n} 个文件 → {out_path}')
    for fname, info in manifest['files'].items():
        print(f'  {fname}: {info["sha256"][:12]}… {info["size"]}B')

if __name__ == '__main__':
    results_dir = sys.argv[1] if len(sys.argv) > 1 else '/home/zhenjinchao/projects/mcm-2026/analysis'
    out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(results_dir, 'manifest.json')
    main(results_dir, out_path)
