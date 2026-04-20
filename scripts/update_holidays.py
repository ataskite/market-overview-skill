#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法定节假日缓存检查脚本

功能：检查下一年节假日缓存是否存在，不存在则输出提示。
由 SKILL.md Step 1 调用，配合 Claude MCP 搜索工具补全数据。
"""
import json
import os
import sys
from datetime import datetime

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(SKILL_DIR, "assets")


def check_holiday_cache(year):
    """检查指定年份的节假日缓存是否存在且有效"""
    cache_file = os.path.join(ASSETS_DIR, f"holidays_{year}.json")
    if not os.path.exists(cache_file):
        return False, cache_file
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data.get('year') == year and len(data.get('holidays', [])) >= 3:
            return True, cache_file
    except Exception:
        pass
    return False, cache_file


def main():
    now = datetime.now()
    current_year = now.year

    # 当前年份缓存检查
    exists, path = check_holiday_cache(current_year)
    if not exists:
        print(f"⚠️ {current_year}年节假日缓存缺失或无效！请手动补全: {path}")
    else:
        print(f"✅ {current_year}年节假日缓存正常")

    # 12月20日起检查下一年（国务院一般在12月下旬发布）
    if now.month == 12 and now.day >= 20:
        next_year = current_year + 1
        exists, path = check_holiday_cache(next_year)
        if not exists:
            print(f"⚠️ {next_year}年节假日缓存不存在！")
            print(f"📋 请使用 MCP 搜索工具搜索「{next_year}年放假安排 国务院办公厅 site:gov.cn」")
            print(f"📋 然后创建 {path}，格式参考现有的 holidays_{current_year}.json")
        else:
            print(f"✅ {next_year}年节假日缓存已就绪")


if __name__ == "__main__":
    main()
