#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
曼联赛程自动汉化脚本
"""

import requests
from icalendar import Calendar
import json
import os
import re
from datetime import datetime

# 官方日历地址（使用您从官网复制的地址）
OFFICAL_ICS_URL = "https://www.manutd.com/en/fixtures-calendar/mens.ics"
OUTPUT_FILE = "manutd_fixtures_chinese.ics"

# 球队翻译映射表
TEAM_TRANSLATION = {
    "Man Utd": "曼联",
    "Manchester United": "曼联",
    "Liverpool": "利物浦",
    "Chelsea": "切尔西",
    "Arsenal": "阿森纳",
    "Man City": "曼城",
    "Tottenham": "热刺",
    "Bournemouth": "伯恩茅斯",
    "Leeds United": "利兹联",
    "Brentford": "布伦特福德",
    "Sunderland": "桑德兰",
    "Nottingham Forest": "诺丁汉森林",
    "Brighton": "布莱顿",
    "Brighton & Hove Albion": "布莱顿",
}

# 球场翻译
VENUE_TRANSLATION = {
    "Old Trafford": "老特拉福德球场",
    "Vitality Stadium": "活力球场",
    "Stamford Bridge": "斯坦福桥球场",
    "Emirates Stadium": "酋长球场",
    "Etihad Stadium": "伊蒂哈德球场",
    "Anfield": "安菲尔德球场",
    "Stadium of Light": "光明球场",
    "American Express Stadium": "美国运通社区球场",
}

# 赛事翻译
COMPETITION_TRANSLATION = {
    "Premier League": "英超",
    "English Premier League": "英超",
    "FA Cup": "足总杯",
    "Carabao Cup": "联赛杯",
    "UEFA Champions League": "欧冠",
    "UEFA Europa League": "欧联",
}

def translate_text(text, translation_dict):
    """翻译文本"""
    result = text
    for eng, chn in translation_dict.items():
        result = result.replace(eng, chn)
    return result

def main():
    print("开始处理曼联赛程...")
    
    # 下载官方ICS
    response = requests.get(OFFICAL_ICS_URL)
    cal = Calendar.from_ical(response.text)
    
    # 翻译每个事件
    for component in cal.walk():
        if component.name == "VEVENT":
            if 'SUMMARY' in component:
                summary = str(component.get('SUMMARY'))
                # 翻译球队
                summary = translate_text(summary, TEAM_TRANSLATION)
                # 翻译赛事
                summary = translate_text(summary, COMPETITION_TRANSLATION)
                component['SUMMARY'] = summary
            
            if 'LOCATION' in component:
                location = str(component.get('LOCATION'))
                location = translate_text(location, VENUE_TRANSLATION)
                component['LOCATION'] = location
    
    # 保存文件
    with open(OUTPUT_FILE, 'wb') as f:
        f.write(cal.to_ical())
    
    print(f"翻译完成！已生成 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
