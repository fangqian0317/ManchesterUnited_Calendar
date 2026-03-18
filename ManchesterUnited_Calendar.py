#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
曼联赛程智能汉化脚本 v2.0 - 优化版
功能：
- 球队名称简化（去除“足球俱乐部”等后缀）
- 强制简体中文（繁转简）
- Friendly → 友谊赛
- 球场名称汉化，删除多余地址和反斜杠
- 标题格式：{赛事} - 主队 vs 客队
"""

import requests
from icalendar import Calendar
import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional

# 尝试导入繁简转换库（需安装：pip install zhconv）
try:
    from zhconv import convert
    ZHCONV_AVAILABLE = True
except ImportError:
    ZHCONV_AVAILABLE = False
    print("警告：zhconv 未安装，繁体转换将跳过。请运行：pip install zhconv")

# ==================== 配置区域 ====================
OFFICAL_ICS_URL = "https://calendar.google.com/calendar/ical/ov0dk4m6dedaob7oqse4nrda4s%40group.calendar.google.com/public/basic.ics"
OUTPUT_FILE = "manutd_fixtures_chinese.ics"
CACHE_FILE = "translation_cache.json"
MAPPING_FILE = "translation_mapping.json"
CACHE_EXPIRY_DAYS = 30

# ==================== 基础翻译映射表 ====================
BASE_TEAM_TRANSLATION = {
    "Man Utd": "曼联",
    "Manchester United": "曼联",
    "Liverpool": "利物浦",
    "Chelsea": "切尔西",
    "Arsenal": "阿森纳",
    "Man City": "曼城",
    "Tottenham": "热刺",
    "Bournemouth": "伯恩茅斯",
    "Leeds United": "利兹联",
    "Leeds": "利兹联",
    "Brentford": "布伦特福德",
    "Sunderland": "桑德兰",
    "Nottingham Forest": "诺丁汉森林",
    "Nott'm Forest": "诺丁汉森林",
    "Brighton": "布莱顿",
    "Brighton & Hove Albion": "布莱顿",
    # 增加常见球队的完整名称映射（简化用）
    "Real Madrid": "皇家马德里",
    "Real Madrid CF": "皇家马德里",
    "Borussia Dortmund": "多特蒙德",
    "Bayer 04 Leverkusen": "勒沃库森",
    "Paris Saint-Germain": "巴黎圣日耳曼",
    "FC Bayern München": "拜仁慕尼黑",
    "Bayern Munich": "拜仁慕尼黑",
    "Juventus": "尤文图斯",
    "AC Milan": "AC米兰",
    "Inter Milan": "国际米兰",
    "Ajax": "阿贾克斯",
}

BASE_VENUE_TRANSLATION = {
    "Old Trafford": "老特拉福德球场",
    "Vitality Stadium": "活力球场",
    "Stamford Bridge": "斯坦福桥球场",
    "Emirates Stadium": "酋长球场",
    "Etihad Stadium": "伊蒂哈德球场",
    "Anfield": "安菲尔德球场",
    "Tottenham Hotspur Stadium": "托特纳姆热刺球场",
    "Stadium of Light": "光明球场",
    "American Express Stadium": "美国运通社区球场",
    "Wembley Stadium": "温布利球场",
    "Camp Nou": "诺坎普球场",
    "Santiago Bernabéu": "伯纳乌球场",
    "Signal Iduna Park": "威斯特法伦球场",
    "Allianz Arena": "安联球场",
    "Parc des Princes": "王子公园球场",
    "San Siro": "圣西罗球场",
    "Johan Cruijff ArenA": "约翰·克鲁伊夫竞技场",
}

BASE_COMPETITION_TRANSLATION = {
    "Premier League": "英超",
    "English Premier League": "英超",
    "FA Cup": "足总杯",
    "Carabao Cup": "联赛杯",
    "UEFA Champions League": "欧冠",
    "UEFA Europa League": "欧联",
    "Friendly": "友谊赛",
    "International Friendly": "友谊赛",
    "Club Friendly": "友谊赛",
}

# ==================== 工具函数 ====================
def to_simplified(text: str) -> str:
    """繁体转简体（如果zhconv可用）"""
    if ZHCONV_AVAILABLE and text:
        return convert(text, 'zh-hans')
    return text

def clean_team_name(name: str) -> str:
    """简化球队名称：去除常见后缀（足球俱乐部、FC等）"""
    # 去除尾部的“足球俱乐部”、“FC”、“CF”等（忽略大小写）
    patterns = [
        r'足球俱乐部$', r'FC$', r'F\.C\.$', r'CF$', r'C\.F\.$',
        r'United$', r'City$', r' Athletic$', r'Albion$',
        r'[•·]?$'  # 去除多余符号
    ]
    cleaned = name
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE).strip()
    return cleaned if cleaned else name  # 避免清空

def clean_location(location: str) -> str:
    """
    清理地点字段：
    - 删除反斜杠 \
    - 提取逗号前的部分（球场名）
    - 去除多余空格
    """
    if not location:
        return ""
    # 去除反斜杠
    location = location.replace('\\', '')
    # 按逗号分割，取第一部分
    parts = location.split(',')
    main_part = parts[0].strip()
    return main_part

# ==================== 自动联网翻译获取器 ====================
class TranslationFetcher:
    # ... 保持原有代码不变，与之前版本相同 ...
    def __init__(self):
        self.cache = self.load_cache()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def load_cache(self) -> Dict:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    now = time.time()
                    for key in list(cache.keys()):
                        if now - cache[key].get('timestamp', 0) > CACHE_EXPIRY_DAYS * 86400:
                            del cache[key]
                    return cache
            except:
                return {}
        return {}
    
    def save_cache(self):
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    def fetch_from_baidu_baike(self, term: str) -> Optional[str]:
        try:
            search_url = f"https://baike.baidu.com/search/word?word={term}"
            response = self.session.get(search_url, timeout=5)
            if response.status_code == 200:
                title_match = re.search(r'<title>(.+?)[_|]百度百科</title>', response.text)
                if title_match:
                    chinese_title = title_match.group(1).strip()
                    chinese_title = re.sub(r'\s+', '', chinese_title)
                    return chinese_title
            time.sleep(1)
            return None
        except Exception as e:
            print(f"  百度百科查询失败 [{term}]: {str(e)}")
            return None
    
    def fetch_from_zh_wikipedia(self, term: str) -> Optional[str]:
        try:
            api_url = "https://zh.wikipedia.org/w/api.php"
            params = {
                'action': 'query',
                'list': 'search',
                'srsearch': term,
                'format': 'json',
                'srlimit': 1
            }
            response = self.session.get(api_url, params=params, timeout=5)
            data = response.json()
            if data.get('query', {}).get('search'):
                title = data['query']['search'][0]['title']
                return title
            time.sleep(0.5)
            return None
        except:
            return None
    
    def get_translation(self, term: str, context: str = 'team') -> str:
        cache_key = f"{context}:{term}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached['timestamp'] < CACHE_EXPIRY_DAYS * 86400:
                print(f"  使用缓存 [{term}] -> {cached['translation']}")
                return cached['translation']
        
        print(f"  🔍 正在查询 [{term}] 的中文译名...")
        translation = None
        if context == 'team':
            translation = self.fetch_from_baidu_baike(term)
            if not translation:
                translation = self.fetch_from_zh_wikipedia(term)
        elif context == 'stadium':
            translation = self.fetch_from_baidu_baike(term)
            if not translation:
                translation = self.smart_stadium_translation(term)
        elif context == 'competition':
            translation = self.translate_competition(term)
        
        if not translation:
            translation = self.fallback_translation(term)
        
        self.cache[cache_key] = {
            'translation': translation,
            'term': term,
            'context': context,
            'timestamp': time.time()
        }
        self.save_cache()
        print(f"  ✅ 获取到 [{term}] -> {translation}")
        return translation
    
    def smart_stadium_translation(self, term: str) -> str:
        stadium_patterns = [
            (r'Stadium$', '球场'),
            (r'Park$', '公园球场'),
            (r'Ground$', '球场'),
            (r'Old Trafford', '老特拉福德球场'),
            (r'Stamford Bridge', '斯坦福桥球场'),
            (r'Emirates', '酋长球场'),
            (r'Etihad', '伊蒂哈德球场'),
            (r'Anfield', '安菲尔德球场'),
            (r'Vitality', '活力球场'),
            (r'American Express', '美国运通社区球场'),
        ]
        for pattern, replacement in stadium_patterns:
            if re.search(pattern, term, re.IGNORECASE):
                return re.sub(pattern, replacement, term, flags=re.IGNORECASE)
        return term + "球场"
    
    def translate_competition(self, term: str) -> str:
        comp_map = {
            'Premier League': '英超',
            'English Premier League': '英超',
            'FA Cup': '足总杯',
            'Carabao Cup': '联赛杯',
            'UEFA Champions League': '欧冠',
            'UEFA Europa League': '欧联',
            'Community Shield': '社区盾',
            'Friendly': '友谊赛',
            'International Friendly': '友谊赛',
            'Club Friendly': '友谊赛',
        }
        for eng, chn in comp_map.items():
            if eng.lower() in term.lower():
                return chn
        return term
    
    def fallback_translation(self, term: str) -> str:
        return term

# ==================== ICS处理器 ====================
class ICSChineseProcessor:
    def __init__(self):
        self.fetcher = TranslationFetcher()
        self.team_dict = self.load_mapping('teams', BASE_TEAM_TRANSLATION)
        self.stadium_dict = self.load_mapping('stadiums', BASE_VENUE_TRANSLATION)
        self.comp_dict = self.load_mapping('competitions', BASE_COMPETITION_TRANSLATION)
        self.new_teams = set()
        self.new_stadiums = set()
        self.new_comps = set()
    
    def load_mapping(self, key: str, default_dict: Dict) -> Dict:
        if os.path.exists(MAPPING_FILE):
            try:
                with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
                    if key in mapping:
                        return mapping[key]
            except:
                pass
        return default_dict.copy()
    
    def save_all_mappings(self):
        mapping = {
            'teams': self.team_dict,
            'stadiums': self.stadium_dict,
            'competitions': self.comp_dict,
            'updated_at': datetime.now().isoformat()
        }
        with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        print(f"\n📁 翻译映射表已保存到 {MAPPING_FILE}")
        print(f"   - 球队: {len(self.team_dict)} 个")
        print(f"   - 球场: {len(self.stadium_dict)} 个")
        print(f"   - 赛事: {len(self.comp_dict)} 个")
    
    def extract_entities_from_calendar(self, cal: Calendar):
        for component in cal.walk():
            if component.name == "VEVENT":
                if 'SUMMARY' in component:
                    summary = str(component.get('SUMMARY'))
                    self._extract_from_summary(summary)
                if 'LOCATION' in component:
                    location = str(component.get('LOCATION'))
                    if location and location not in self.stadium_dict:
                        self.new_stadiums.add(location)
    
    def _extract_from_summary(self, summary: str):
        if ' vs ' in summary:
            parts = summary.split(' vs ')
            if len(parts) >= 2:
                team1 = parts[0].strip()
                remaining = parts[1]
                if ' - ' in remaining:
                    team2_part = remaining.split(' - ')[0]
                    team2 = team2_part.strip()
                    comp_part = remaining.split(' - ')[-1]
                    if comp_part and comp_part not in self.comp_dict:
                        self.new_comps.add(comp_part)
                else:
                    team2 = remaining.strip()
                if team1 and team1 not in self.team_dict:
                    self.new_teams.add(team1)
                if team2 and team2 not in self.team_dict:
                    self.new_teams.add(team2)
    
    def fetch_new_translations(self):
        print("\n🔍 开始查询新实体的中文译名...")
        if self.new_teams:
            print(f"\n📋 新球队 ({len(self.new_teams)} 个):")
            for team in sorted(self.new_teams):
                translation = self.fetcher.get_translation(team, 'team')
                self.team_dict[team] = translation
        if self.new_stadiums:
            print(f"\n🏟️ 新球场 ({len(self.new_stadiums)} 个):")
            for stadium in sorted(self.new_stadiums):
                translation = self.fetcher.get_translation(stadium, 'stadium')
                self.stadium_dict[stadium] = translation
        if self.new_comps:
            print(f"\n🏆 新赛事 ({len(self.new_comps)} 个):")
            for comp in sorted(self.new_comps):
                translation = self.fetcher.get_translation(comp, 'competition')
                self.comp_dict[comp] = translation
    
    def translate_calendar(self, cal: Calendar) -> Calendar:
        """翻译日历并按照标准格式重组标题和地点"""
        event_count = 0
        print("\n🔄 开始翻译赛程...")
        
        for component in cal.walk():
            if component.name == "VEVENT":
                event_count += 1
                
                # ---------- 处理标题 ----------
                if 'SUMMARY' in component:
                    original = str(component.get('SUMMARY'))
                    
                    # 提取主队、客队和赛事信息
                    home_team = ""
                    away_team = ""
                    competition = ""
                    
                    # 简单解析：格式通常为 "TeamA vs TeamB - Competition" 或 "TeamA vs TeamB (Competition)"
                    # 先按 " vs " 分割
                    if ' vs ' in original:
                        parts = original.split(' vs ')
                        home_team_raw = parts[0].strip()
                        rest = parts[1]
                        # 移除可能的前后空格
                        # 尝试提取赛事
                        comp_match = re.search(r'[-–—(]?\s*(.+?)\s*[)]?$', rest)
                        if comp_match:
                            away_team_raw = rest[:comp_match.start()].strip()
                            competition_raw = comp_match.group(1).strip()
                        else:
                            away_team_raw = rest
                            competition_raw = ""
                    else:
                        # 如果没有 vs，可能是不标准格式，直接全部翻译
                        home_team_raw = original
                        away_team_raw = ""
                        competition_raw = ""
                    
                    # 翻译球队名称
                    home_team = self.team_dict.get(home_team_raw, home_team_raw)
                    away_team = self.team_dict.get(away_team_raw, away_team_raw) if away_team_raw else ""
                    
                    # 简化球队名称（去除“足球俱乐部”等）
                    home_team = clean_team_name(home_team)
                    away_team = clean_team_name(away_team) if away_team else ""
                    
                    # 翻译赛事
                    competition = self.comp_dict.get(competition_raw, competition_raw)
                    # 如果赛事为空，默认设为“友谊赛”？
                    if not competition and ("Friendly" in original or "friendly" in original):
                        competition = "友谊赛"
                    
                    # 构建新标题：格式 "{赛事} - {主队} vs {客队}"
                    if home_team and away_team:
                        if competition:
                            new_summary = f"{competition} - {home_team} vs {away_team}"
                        else:
                            new_summary = f"{home_team} vs {away_team}"
                    else:
                        # 如果解析失败，直接用翻译后的原字符串
                        new_summary = original
                        for eng, chn in self.team_dict.items():
                            new_summary = new_summary.replace(eng, chn)
                        for eng, chn in self.comp_dict.items():
                            new_summary = new_summary.replace(eng, chn)
                    
                    # 繁体转简体
                    new_summary = to_simplified(new_summary)
                    component['SUMMARY'] = new_summary
                    print(f"  比赛{event_count}: {new_summary[:60]}...")
                
                # ---------- 处理地点 ----------
                if 'LOCATION' in component:
                    original_loc = str(component.get('LOCATION'))
                    # 清理地址：去反斜杠，取逗号前，去除多余空格
                    cleaned = clean_location(original_loc)
                    # 翻译球场名称
                    translated_loc = self.stadium_dict.get(cleaned, cleaned)
                    # 繁体转简体
                    translated_loc = to_simplified(translated_loc)
                    component['LOCATION'] = translated_loc
                
                # ---------- 处理描述（可选，这里清空或保留部分）----------
                # 为了简洁，可以删除描述，只保留必要的
                if 'DESCRIPTION' in component:
                    # 可选择性保留一些信息，这里置空或简单处理
                    # 原描述可能包含地址，我们已经提取地点，所以可以删除
                    component['DESCRIPTION'] = ""  # 或保留简洁信息
        
        print(f"\n✅ 翻译完成，共处理 {event_count} 场比赛")
        return cal

# ==================== 主程序 ====================
def fetch_calendar_from_source():
    urls = [
        OFFICAL_ICS_URL,
        "https://www.manutd.com/en/fixtures-calendar/mens.ics",
        "https://www.manutd.com/en/fixtures-calendar/mens.ics?t=web",
    ]
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/calendar,application/ical,text/plain,*/*',
    }
    for i, url in enumerate(urls, 1):
        print(f"\n尝试链接 {i}/{len(urls)}: {url}")
        try:
            if url.startswith('webcal://'):
                url = 'https://' + url[8:]
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                if response.text.strip().startswith('<!DOCTYPE') or response.text.strip().startswith('<?xml'):
                    print(f"  返回的是HTML页面，尝试下一个...")
                    continue
                try:
                    cal = Calendar.from_ical(response.text)
                    print(f"✅ 成功获取日历！")
                    return cal
                except Exception as e:
                    print(f"  解析失败: {e}")
                    continue
            else:
                print(f"  状态码: {response.status_code}")
        except Exception as e:
            print(f"  连接失败: {e}")
            continue
    return None

def main():
    print("=" * 60)
    print("曼联中文赛程智能汉化系统 v2.0（优化版）")
    print("功能：球队简称、简体强制、地址清理、标准格式")
    print("=" * 60)
    
    cal = fetch_calendar_from_source()
    if not cal:
        print("\n❌ 无法获取官方日历！")
        print("请检查链接或网络。")
        return
    
    processor = ICSChineseProcessor()
    print("\n🔎 正在分析赛程内容...")
    processor.extract_entities_from_calendar(cal)
    processor.fetch_new_translations()
    translated_cal = processor.translate_calendar(cal)
    
    with open(OUTPUT_FILE, 'wb') as f:
        f.write(translated_cal.to_ical())
    
    processor.save_all_mappings()
    
    print(f"\n✅ 完成！中文赛程已保存到：{OUTPUT_FILE}")
    if os.path.exists(OUTPUT_FILE):
        file_size = os.path.getsize(OUTPUT_FILE) / 1024
        print(f"📊 文件大小：{file_size:.2f} KB")

if __name__ == "__main__":
    main()
