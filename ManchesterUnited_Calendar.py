#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
曼联中文赛程终极版 - 多源校对 + FotMob 核对
"""

import requests
from icalendar import Calendar
import json
import os
import re
from datetime import datetime
# 假设 FotMob 客户端已实现
from fotmob_client import FotMobClient

# ==================== 配置 ====================
GOOGLE_CAL_ICS_URL = "https://calendar.google.com/calendar/ical/ov0dk4m6dedaob7oqse4nrda4s%40group.calendar.google.com/public/basic.ics"
OUTPUT_FILE = "manutd_fixtures_final.ics"
LOCAL_MAP_FILE = "translation_mapping.json"
# =============================================

# 初始化翻译映射表（包含简称）
translation_map = {
    "teams": { "Manchester United": "曼联", "Liverpool": "利物浦" },
    "competitions": { "Premier League": "英超", "FA Cup": "足总杯" },
    "stadiums": { "Old Trafford": "老特拉福德球场" }
}

# 1. 数据获取与解析
def fetch_and_parse_ics(url):
    # ... 下载并解析ICS，返回事件列表 ...

# 2. 多源校对模块
def multi_source_verify(term, context='team'):
    """
    从百度百科、维基百科、懂球帝获取译名并投票
    返回最可靠的译名
    """
    # ... 实现并行查询和投票逻辑 ...
    return verified_term

# 3. FotMob 核对模块
def verify_with_fotmob(date, home_team, away_team):
    """
    与 FotMob 数据核对，返回准确的轮次和赛程信息
    """
    client = FotMobClient()
    match_info = client.search_match(date, home_team, away_team)
    if match_info:
        return {
            'round': match_info.get('round'),
            'home': match_info['home_team'],
            'away': match_info['away_team'],
            'competition': match_info['competition']
        }
    return None

# 4. 主处理逻辑
def main():
    raw_events = fetch_and_parse_ics(GOOGLE_CAL_ICS_URL)
    processed_events = []
    
    for event in raw_events:
        # 从原始标题提取信息
        raw_title = event['summary']
        home_guess, away_guess, comp_guess = extract_info(raw_title)
        date = event['date']
        
        # FotMob 核对
        fotmob_data = verify_with_fotmob(date, home_guess, away_guess)
        
        if fotmob_data:
            # 使用FotMob的数据，确保准确性
            comp_cn = translation_map['competitions'].get(fotmob_data['competition'], fotmob_data['competition'])
            home_cn = translation_map['teams'].get(fotmob_data['home'], fotmob_data['home'])
            away_cn = translation_map['teams'].get(fotmob_data['away'], fotmob_data['away'])
            round_info = f"第{fotmob_data['round']}轮" if fotmob_data['round'] else ""
            
            # 如果本地没有，触发多源校对并更新映射
            if home_cn == fotmob_data['home']:
                home_cn = multi_source_verify(fotmob_data['home'], 'team')
                translation_map['teams'][fotmob_data['home']] = home_cn
            # ... 类似处理away和comp
            
        else:
            # FotMob无匹配，使用本地映射+多源校对
            comp_cn = translation_map['competitions'].get(comp_guess, multi_source_verify(comp_guess, 'competition'))
            home_cn = translation_map['teams'].get(home_guess, multi_source_verify(home_guess, 'team'))
            away_cn = translation_map['teams'].get(away_guess, multi_source_verify(away_guess, 'team'))
            round_info = "" # 轮次未知
        
        # 构建最终标题
        final_title = f"{comp_cn} {round_info} {home_cn} VS {away_cn}".strip()
        # 清理英文，确保纯中文（VS除外）
        final_title = force_chinese_except_vs(final_title)
        
        # 更新事件并保存
        event['summary'] = final_title
        event['location'] = translation_map['stadiums'].get(event['location_raw'], multi_source_verify(event['location_raw'], 'stadium'))
        processed_events.append(event)
    
    # 生成新的ICS文件
    generate_ics(processed_events, OUTPUT_FILE)
    # 保存更新后的映射表
    save_mapping(translation_map, LOCAL_MAP_FILE)

if __name__ == "__main__":
    main()
