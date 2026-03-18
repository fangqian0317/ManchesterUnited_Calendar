#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
曼联中文赛程终极版 - 多源校对 + FotMob 核对 (语法修正版)
"""

import requests
from icalendar import Calendar
import json
import os
import re
from datetime import datetime

# 尝试导入 FotMob 库 (如果未安装，程序将降级运行)
try:
    from pyfotmob import FotMob
    FOTMOB_AVAILABLE = True
except ImportError:
    FOTMOB_AVAILABLE = False
    print("警告: pyfotmob 未安装，FotMob核对功能将不可用。请运行: pip install pyfotmob")
    # 定义一个占位类，避免后续代码报错
    class FotMob:
        def get_matches_by_date(self, date):
            return None

# ==================== 配置 ====================
GOOGLE_CAL_ICS_URL = "https://calendar.google.com/calendar/ical/ov0dk4m6dedaob7oqse4nrda4s%40group.calendar.google.com/public/basic.ics"
OUTPUT_FILE = "manutd_fixtures_final.ics"
LOCAL_MAP_FILE = "translation_mapping.json"
# =============================================

# 初始化翻译映射表（包含简称）
translation_map = {
    "teams": {"Manchester United": "曼联", "Liverpool": "利物浦"},
    "competitions": {"Premier League": "英超", "FA Cup": "足总杯"},
    "stadiums": {"Old Trafford": "老特拉福德球场"}
}

# ==================== 辅助函数（占位实现，您可以根据需要完善）====================
def extract_info(raw_title):
    """
    从原始标题中猜测主队、客队、赛事
    返回 (home_guess, away_guess, comp_guess)
    """
    # 这是一个非常简化的实现，您可以根据实际标题格式优化
    home_guess = away_guess = comp_guess = ""
    # 简单的逻辑：尝试分割
    parts = raw_title.split(' vs ')
    if len(parts) == 2:
        home_guess = parts[0].strip()
        # 进一步尝试提取赛事
        away_part = parts[1]
        if ' - ' in away_part:
            away_guess, comp_guess = away_part.split(' - ', 1)
            away_guess = away_guess.strip()
            comp_guess = comp_guess.strip()
        else:
            away_guess = away_part.strip()
    return home_guess, away_guess, comp_guess

def force_chinese_except_vs(text):
    """
    强制文本中只保留中文和VS，删除其他英文字母
    （简化版，仅做演示）
    """
    # 这里应该实现更复杂的清理逻辑，目前先返回原文本
    return text

def generate_ics(events, filename):
    """生成ICS文件（占位实现）"""
    print(f"生成ICS文件: {filename}，包含 {len(events)} 个事件")

def save_mapping(mapping, filename):
    """保存映射表到文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(f"映射表已保存到 {filename}")

def fetch_and_parse_ics(url):
    """下载并解析ICS，返回事件列表（占位实现）"""
    print(f"尝试从 {url} 获取日历...")
    # 这里应添加实际的下载和解析代码
    # 为了框架可运行，返回一个空列表
    return []

def multi_source_verify(term, context='team'):
    """
    从百度百科、维基百科、懂球帝获取译名并投票
    返回最可靠的译名（占位实现）
    """
    print(f"  多源校对 [{term}] ({context})...")
    # 模拟返回原词
    return term

def verify_with_fotmob(date, home_team, away_team):
    """
    与 FotMob 数据核对，返回准确的轮次和赛程信息（占位实现）
    """
    if not FOTMOB_AVAILABLE:
        return None
    print(f"  尝试FotMob核对: {date} {home_team} vs {away_team}")
    # 这里应添加实际的FotMob查询逻辑
    return None
# ==================================================================

# 4. 主处理逻辑
def main():
    print("="*60)
    print("曼联中文赛程终极版启动")
    print("="*60)

    raw_events = fetch_and_parse_ics(GOOGLE_CAL_ICS_URL)
    if not raw_events:
        print("未获取到任何事件，将使用模拟数据进行演示。")
        # 添加一个模拟事件供测试
        raw_events = [{'summary': 'Manchester United vs Liverpool - Premier League', 'date': '2024-05-25', 'location_raw': 'Old Trafford'}]

    processed_events = []

    for event in raw_events:
        print(f"\n处理事件: {event.get('summary')}")

        # 从原始标题提取信息
        raw_title = event.get('summary', '')
        home_guess, away_guess, comp_guess = extract_info(raw_title)
        date = event.get('date', '')

        # FotMob 核对
        fotmob_data = verify_with_fotmob(date, home_guess, away_guess)

        if fotmob_data:
            print("  ✅ FotMob匹配成功")
            # 使用FotMob的数据，确保准确性
            comp_cn = translation_map['competitions'].get(fotmob_data['competition'], fotmob_data['competition'])
            home_cn = translation_map['teams'].get(fotmob_data['home'], fotmob_data['home'])
            away_cn = translation_map['teams'].get(fotmob_data['away'], fotmob_data['away'])
            round_info = f"第{fotmob_data['round']}轮" if fotmob_data.get('round') else ""

            # 如果本地没有，触发多源校对并更新映射
            if home_cn == fotmob_data['home']:
                home_cn = multi_source_verify(fotmob_data['home'], 'team')
                translation_map['teams'][fotmob_data['home']] = home_cn
            if away_cn == fotmob_data['away']:
                away_cn = multi_source_verify(fotmob_data['away'], 'team')
                translation_map['teams'][fotmob_data['away']] = away_cn
            if comp_cn == fotmob_data['competition']:
                comp_cn = multi_source_verify(fotmob_data['competition'], 'competition')
                translation_map['competitions'][fotmob_data['competition']] = comp_cn
        else:
            print("  ⚠️ FotMob无匹配，使用本地映射+多源校对")
            # FotMob无匹配，使用本地映射+多源校对
            comp_cn = translation_map['competitions'].get(comp_guess, multi_source_verify(comp_guess, 'competition'))
            home_cn = translation_map['teams'].get(home_guess, multi_source_verify(home_guess, 'team'))
            away_cn = translation_map['teams'].get(away_guess, multi_source_verify(away_guess, 'team'))
            round_info = ""  # 轮次未知

        # 构建最终标题
        final_title = f"{comp_cn} {round_info} {home_cn} VS {away_cn}".strip()
        # 清理英文，确保纯中文（VS除外）
        final_title = force_chinese_except_vs(final_title)

        # 处理球场
        raw_location = event.get('location_raw', '')
        if raw_location:
            stadium_cn = translation_map['stadiums'].get(raw_location, multi_source_verify(raw_location, 'stadium'))
            translation_map['stadiums'][raw_location] = stadium_cn
        else:
            stadium_cn = ""

        # 更新事件并保存
        event['summary'] = final_title
        event['location'] = stadium_cn
        processed_events.append(event)
        print(f"  新标题: {final_title}")
        print(f"  新地点: {stadium_cn}")

    # 生成新的ICS文件
    generate_ics(processed_events, OUTPUT_FILE)
    # 保存更新后的映射表
    save_mapping(translation_map, LOCAL_MAP_FILE)

if __name__ == "__main__":
    main()
