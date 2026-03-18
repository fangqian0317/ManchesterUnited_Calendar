#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
曼联赛程智能汉化脚本 v1.0 - 完整自动翻译版
功能：自动从网络获取最新中文译名，动态更新翻译映射表
"""

import requests
from icalendar import Calendar
import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional

# ==================== 配置区域 ====================
# 官方日历地址（请替换为您从官网复制的真实地址）
OFFICAL_ICS_URL = "https://calendar.google.com/calendar/ical/ov0dk4m6dedaob7oqse4nrda4s%40group.calendar.google.com/public/basic.ics"
OUTPUT_FILE = "manutd_fixtures_chinese.ics"
CACHE_FILE = "translation_cache.json"  # 翻译缓存文件
MAPPING_FILE = "translation_mapping.json"  # 映射表文件
CACHE_EXPIRY_DAYS = 30  # 缓存有效期（天）

# ==================== 基础翻译映射表（备用）====================
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
}

BASE_COMPETITION_TRANSLATION = {
    "Premier League": "英超",
    "English Premier League": "英超",
    "FA Cup": "足总杯",
    "Carabao Cup": "联赛杯",
    "UEFA Champions League": "欧冠",
    "UEFA Europa League": "欧联",
}

# ==================== 自动联网翻译获取器 ====================

class TranslationFetcher:
    """从网络自动获取中文译名的获取器"""
    
    def __init__(self):
        self.cache = self.load_cache()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def load_cache(self) -> Dict:
        """加载本地缓存"""
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    # 清理过期缓存
                    now = time.time()
                    for key in list(cache.keys()):
                        if now - cache[key].get('timestamp', 0) > CACHE_EXPIRY_DAYS * 86400:
                            del cache[key]
                    return cache
            except:
                return {}
        return {}
    
    def save_cache(self):
        """保存缓存"""
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    def fetch_from_baidu_baike(self, term: str) -> Optional[str]:
        """
        从百度百科获取中文译名
        示例：搜索 "Manchester United" 返回 "曼联"
        """
        try:
            # 构造搜索URL
            search_url = f"https://baike.baidu.com/search/word?word={term}"
            response = self.session.get(search_url, timeout=5)
            
            if response.status_code == 200:
                # 从HTML中提取中文标题
                # 匹配百科页面的标题，格式如：<title>曼联_百度百科</title>
                title_match = re.search(r'<title>(.+?)[_|]百度百科</title>', response.text)
                if title_match:
                    chinese_title = title_match.group(1).strip()
                    # 清理多余字符
                    chinese_title = re.sub(r'\s+', '', chinese_title)
                    return chinese_title
            
            time.sleep(1)  # 礼貌性延迟，避免请求过快
            return None
            
        except Exception as e:
            print(f"  百度百科查询失败 [{term}]: {str(e)}")
            return None
    
    def fetch_from_zh_wikipedia(self, term: str) -> Optional[str]:
        """
        从中文维基百科获取译名（备用源）
        """
        try:
            # 使用MediaWiki API
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
            
        except Exception as e:
            return None
    
    def get_translation(self, term: str, context: str = 'team') -> str:
        """
        获取中文译名的主方法
        term: 英文名称
        context: 上下文类型（team/stadium/competition）
        """
        cache_key = f"{context}:{term}"
        
        # 1. 先检查缓存
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached['timestamp'] < CACHE_EXPIRY_DAYS * 86400:
                print(f"  使用缓存 [{term}] -> {cached['translation']}")
                return cached['translation']
        
        # 2. 缓存中没有，从网络获取
        print(f"  🔍 正在查询 [{term}] 的中文译名...")
        translation = None
        
        if context == 'team':
            # 球队名称：优先用百度百科
            translation = self.fetch_from_baidu_baike(term)
            if not translation:
                translation = self.fetch_from_zh_wikipedia(term)
        
        elif context == 'stadium':
            # 球场名称：百度百科
            translation = self.fetch_from_baidu_baike(term)
            if not translation:
                # 如果没找到，用规则翻译
                translation = self.smart_stadium_translation(term)
        
        elif context == 'competition':
            # 赛事名称：用规则翻译
            translation = self.translate_competition(term)
        
        # 3. 如果还是没找到，使用默认规则
        if not translation:
            translation = self.fallback_translation(term)
        
        # 4. 存入缓存
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
        """智能球场名称翻译"""
        # 常见球场翻译规则
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
        """赛事名称翻译"""
        comp_map = {
            'Premier League': '英超',
            'English Premier League': '英超',
            'FA Cup': '足总杯',
            'Carabao Cup': '联赛杯',
            'UEFA Champions League': '欧冠',
            'UEFA Europa League': '欧联',
            'Community Shield': '社区盾',
        }
        
        for eng, chn in comp_map.items():
            if eng.lower() in term.lower():
                return chn
        
        return term
    
    def fallback_translation(self, term: str) -> str:
        """备用翻译规则"""
        # 简单规则：直接返回原词（可以扩展为拼音等）
        return term


# ==================== 主处理器 ====================

class ICSChineseProcessor:
    """ICS文件中文处理器"""
    
    def __init__(self):
        self.fetcher = TranslationFetcher()
        # 加载已有的映射表
        self.team_dict = self.load_mapping('teams', BASE_TEAM_TRANSLATION)
        self.stadium_dict = self.load_mapping('stadiums', BASE_VENUE_TRANSLATION)
        self.comp_dict = self.load_mapping('competitions', BASE_COMPETITION_TRANSLATION)
        
        # 记录新发现的实体
        self.new_teams = set()
        self.new_stadiums = set()
        self.new_comps = set()
    
    def load_mapping(self, key: str, default_dict: Dict) -> Dict:
        """加载已保存的映射表"""
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
        """保存所有映射表"""
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
        """从日历中提取需要翻译的实体"""
        for component in cal.walk():
            if component.name == "VEVENT":
                # 从标题提取
                if 'SUMMARY' in component:
                    summary = str(component.get('SUMMARY'))
                    self._extract_from_summary(summary)
                
                # 从地点提取
                if 'LOCATION' in component:
                    location = str(component.get('LOCATION'))
                    if location and location not in self.stadium_dict:
                        self.new_stadiums.add(location)
    
    def _extract_from_summary(self, summary: str):
        """从标题中提取实体"""
        # 提取球队名称（格式如："Man Utd vs Liverpool - Premier League"）
        if ' vs ' in summary:
            parts = summary.split(' vs ')
            if len(parts) >= 2:
                # 第一部分可能包含球队1
                team1 = parts[0].strip()
                # 第二部分可能包含球队2和赛事
                remaining = parts[1]
                if ' - ' in remaining:
                    team2_part = remaining.split(' - ')[0]
                    team2 = team2_part.strip()
                    # 赛事名称在最后
                    comp_part = remaining.split(' - ')[-1]
                    if comp_part and comp_part not in self.comp_dict:
                        self.new_comps.add(comp_part)
                else:
                    team2 = remaining.strip()
                
                # 检查是否需要查询新球队
                if team1 and team1 not in self.team_dict:
                    self.new_teams.add(team1)
                if team2 and team2 not in self.team_dict:
                    self.new_teams.add(team2)
    
    def fetch_new_translations(self):
        """批量获取新实体的翻译"""
        print("\n🔍 开始查询新实体的中文译名...")
        
        # 查询新球队
        if self.new_teams:
            print(f"\n📋 新球队 ({len(self.new_teams)} 个):")
            for team in sorted(self.new_teams):
                translation = self.fetcher.get_translation(team, 'team')
                self.team_dict[team] = translation
        
        # 查询新球场
        if self.new_stadiums:
            print(f"\n🏟️ 新球场 ({len(self.new_stadiums)} 个):")
            for stadium in sorted(self.new_stadiums):
                translation = self.fetcher.get_translation(stadium, 'stadium')
                self.stadium_dict[stadium] = translation
        
        # 查询新赛事
        if self.new_comps:
            print(f"\n🏆 新赛事 ({len(self.new_comps)} 个):")
            for comp in sorted(self.new_comps):
                translation = self.fetcher.get_translation(comp, 'competition')
                self.comp_dict[comp] = translation
    
    def translate_calendar(self, cal: Calendar) -> Calendar:
        """翻译日历"""
        event_count = 0
        
        print("\n🔄 开始翻译赛程...")
        for component in cal.walk():
            if component.name == "VEVENT":
                event_count += 1
                
                # 翻译标题
                if 'SUMMARY' in component:
                    original = str(component.get('SUMMARY'))
                    translated = original
                    
                    # 应用球队翻译
                    for eng, chn in self.team_dict.items():
                        translated = translated.replace(eng, chn)
                    
                    # 应用赛事翻译
                    for eng, chn in self.comp_dict.items():
                        translated = translated.replace(eng, chn)
                    
                    component['SUMMARY'] = translated
                    print(f"  比赛{event_count}: {translated[:50]}...")
                
                # 翻译地点
                if 'LOCATION' in component:
                    original = str(component.get('LOCATION'))
                    translated = original
                    for eng, chn in self.stadium_dict.items():
                        translated = translated.replace(eng, chn)
                    component['LOCATION'] = translated
        
        print(f"\n✅ 翻译完成，共处理 {event_count} 场比赛")
        return cal
    
    def add_round_info(self, cal: Calendar):
        """添加轮次信息（可选增强功能）"""
        # 这里可以根据日期添加轮次
        # 可以从外部API获取，也可以手动维护映射
        pass


# ==================== 主程序 ====================

def fetch_calendar_from_manutd():
    """从曼联官网获取日历（带重试和错误处理）"""
    
    # 多个备用链接
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
            # 处理webcal协议
            if url.startswith('webcal://'):
                url = 'https://' + url[8:]
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                # 检查是否是HTML
                if response.text.strip().startswith('<!DOCTYPE') or response.text.strip().startswith('<?xml'):
                    print(f"  返回的是HTML页面，尝试下一个...")
                    continue
                
                # 尝试解析
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
    print("曼联中文赛程智能汉化系统 v1.0")
    print("（带自动联网翻译功能）")
    print("=" * 60)
    
    # 1. 获取日历
    cal = fetch_calendar_from_manutd()
    if not cal:
        print("\n❌ 无法获取官方日历！")
        print("请检查：")
        print("1. 网络连接")
        print("2. 在脚本中配置正确的日历链接")
        sys.exit(1)
    
    # 2. 创建处理器
    processor = ICSChineseProcessor()
    
    # 3. 提取实体
    print("\n🔎 正在分析赛程内容...")
    processor.extract_entities_from_calendar(cal)
    
    # 4. 获取新实体的翻译
    processor.fetch_new_translations()
    
    # 5. 翻译日历
    translated_cal = processor.translate_calendar(cal)
    
    # 6. 保存翻译后的文件
    with open(OUTPUT_FILE, 'wb') as f:
        f.write(translated_cal.to_ical())
    
    # 7. 保存映射表
    processor.save_all_mappings()
    
    # 8. 显示统计
    print(f"\n✅ 完成！中文赛程已保存到：{OUTPUT_FILE}")
    if os.path.exists(OUTPUT_FILE):
        file_size = os.path.getsize(OUTPUT_FILE) / 1024
        print(f"📊 文件大小：{file_size:.2f} KB")

if __name__ == "__main__":
    main()
