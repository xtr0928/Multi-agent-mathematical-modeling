#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_pdf.py — report.html → PDF（playwright）"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 1280, 'height': 900})
        await pg.goto('file:///home/zhenjinchao/projects/mcm-2026/paper/report.html')
        await pg.wait_for_timeout(800)
        await pg.pdf(path='/home/zhenjinchao/projects/mcm-2026/paper/DWTS_Solution.pdf',
                     format='A4', print_background=True,
                     margin={'top': '0', 'bottom': '0', 'left': '0', 'right': '0'})
        await b.close()
        print('PDF saved')

asyncio.run(main())
