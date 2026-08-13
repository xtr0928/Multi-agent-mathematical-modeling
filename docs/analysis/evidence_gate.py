#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evidence_gate.py — 渲染前证据门禁
校验论文 build_report.py 引用的结果文件磁盘哈希 == manifest 记录。
不一致 = results 已变但论文未重跑 → 拒绝渲染。
用法: python3 evidence_gate.py <manifest.json> <引用文件列表...>
"""
import json, sys, os, hashlib

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    if len(sys.argv) < 3:
        print('用法: evidence_gate.py <manifest.json> <file1> [file2 ...]')
        sys.exit(2)
    manifest_path, refs = sys.argv[1], sys.argv[2:]
    manifest = json.load(open(manifest_path))
    fails = []
    for ref in refs:
        fname = os.path.basename(ref)
        if fname not in manifest['files']:
            fails.append(f'{fname}: manifest 中无记录（新文件？需先跑 hash_results.py）')
            continue
        cur = sha256(ref)
        rec = manifest['files'][fname]['sha256']
        if cur != rec:
            fails.append(f'{fname}: 磁盘哈希 {cur[:12]} ≠ manifest {rec[:12]}（结果已变更，需重跑下游脚本后重新生成 manifest）')
    if fails:
        print('❌ 证据门禁 FAIL：')
        for f in fails:
            print(f'  {f}')
        sys.exit(1)
    print(f'✅ 证据门禁 PASS：{len(refs)} 个引用文件哈希全部一致')

if __name__ == '__main__':
    main()
