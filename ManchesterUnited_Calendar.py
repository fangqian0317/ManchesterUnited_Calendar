#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
曼联赛程智能汉化脚本 v5.1 - 专业数据源版 + 增强回退
- 使用 football-data.org API 获取准确信息
- API 失败时，通过本地映射和智能解析保证基本翻译
"""

import requests
from icalendar import Calendar
import json
import os
import re
import time
from datetime import datetime

try:
    from zhconv import convert
    ZHCONV_AVAILABLE = True
except ImportError:
    ZHCONV_AVAILABLE = False
    print("警告：zhconv 未安装，繁体转换将跳过。请运行：pip install zhconv")

# ==================== 配置 ====================
OFFICAL_ICS_URL = "https://calendar.google.com/calendar/ical/ov0dk4m6dedaob7oqse4nrda4s%40group.calendar.google.com/public/basic.ics"
OUTPUT_FILE = "manutd_fixtures_chinese.ics"
MAPPING_FILE = "translation_mapping.json"

# football-data.org API 配置（请替换为您的真实密钥）
FOOTBALL_DATA_API_KEY = "b82d8542ddb94bf0975928cba4f5e9c3"
FOOTBALL_DATA_API_URL = "https://api.football-data.org/v4/matches"

# 球队ID映射（提高API匹配率）
TEAM_IDS = {
    "Manchester United": 66,
    "Man Utd": 66,
    "Liverpool": 64,
    "Arsenal": 57,
    "Chelsea": 61,
    "Tottenham": 73,
    "Manchester City": 65,
    "Real Madrid": 86,
    "Barcelona": 81,
    "Bayern Munich": 5,
    "Borussia Dortmund": 4,
    "Paris Saint-Germain": 83,
    "Juventus": 98,
    "AC Milan": 98,  # 注意：米兰双雄ID需核实，这里只是示例
    "Inter Milan": 98,
    # 可继续补充
}

# ==================== 本地翻译字典（扩充版）====================
TEAM_MAP = {
    # 曼联
    "Man Utd": "曼联", "Manchester United": "曼联",
    # 英超球队（补充）
    "Brentford": "布伦特福德",
    "Brighton and Hove Albion": "布莱顿",  # 注意：Brighton 简称是“布莱顿”
    "Brighton & Hove Albion": "布莱顿",
    "Brighton": "布莱顿",
    "Hull City": "赫尔城",
    "Manchester City": "曼城",
    "Man City": "曼城",
    "Liverpool": "利物浦",
    "Chelsea": "切尔西",
    "Arsenal": "阿森纳",
    "Tottenham Hotspur": "热刺",
    "Tottenham": "热刺",
    "Newcastle United": "纽卡斯尔联",
    "Leicester City": "莱斯特城",
    "Everton": "埃弗顿",
    "Aston Villa": "阿斯顿维拉",
    "Southampton": "南安普顿",
    "Wolverhampton Wanderers": "狼队",
    "Wolves": "狼队",
    "Crystal Palace": "水晶宫",
    "West Ham United": "西汉姆联",
    "Fulham": "富勒姆",
    "Leeds United": "利兹联",
    "Nottingham Forest": "诺丁汉森林",
    "Sunderland": "桑德兰",
    "Bournemouth": "伯恩茅斯",
    # 欧战球队
    "Partizan Belgrade": "贝尔格莱德游击",
    "CSKA Moscow": "莫斯科中央陆军",
    "Real Madrid": "皇家马德里",
    "Barcelona": "巴塞罗那",
    "Bayern Munich": "拜仁慕尼黑",
    "Borussia Dortmund": "多特蒙德",
    "Paris Saint-Germain": "巴黎圣日耳曼",
    "Juventus": "尤文图斯",
    "AC Milan": "AC米兰",
    "Inter Milan": "国际米兰",
    "Ajax": "阿贾克斯",
    "Celtic": "凯尔特人",
    "Rangers": "流浪者",
    "Porto": "波尔图",
    "Benfica": "本菲卡",
    "Shakhtar Donetsk": "顿涅茨克矿工",
    "Dynamo Kyiv": "基辅迪纳摩",
    # 其他常见球队
    "Lyon": "里昂",
    "Wrexham": "雷克瑟姆",
    "Real Betis": "皇家贝蒂斯",
    "Sevilla": "塞维利亚",
    "Valencia": "巴伦西亚",
    "Villarreal": "比利亚雷亚尔",
    "Athletic Bilbao": "毕尔巴鄂竞技",
    "Nice": "尼斯",
    "Monaco": "摩纳哥",
    "Marseille": "马赛",
    "Lille": "里尔",
    "Eintracht Frankfurt": "法兰克福",
    "RB Leipzig": "莱比锡红牛",
    "Wolfsburg": "沃尔夫斯堡",
    "Napoli": "那不勒斯",
    "Lazio": "拉齐奥",
    "Atalanta": "亚特兰大",
    "Roma": "罗马",
}

COMP_MAP = {
    "Premier League": "英超",
    "English Premier League": "英超",
    "FA Cup": "足总杯",
    "Carabao Cup": "联赛杯",
    "English League Cup": "联赛杯",
    "UEFA Champions League": "欧冠",
    "Champions League": "欧冠",
    "UEFA Europa League": "欧联",
    "Europa League": "欧联",
    "UEFA Conference League": "欧协联",
    "Friendly": "友谊赛",
    "International Friendly": "友谊赛",
    "Club Friendly": "友谊赛",
    "La Liga": "西甲",
    "Bundesliga": "德甲",
    "Serie A": "意甲",
    "Ligue 1": "法甲",
    "Eredivisie": "荷甲",
    "Primeira Liga": "葡超",
}

STADIUM_MAP = {
    "Old Trafford": "老特拉福德球场",
    "Brentford Community Stadium": "布伦特福德社区球场",
    "Amex Stadium": "美国运通社区球场",
    "KCOM Stadium": "KC球场",
    "Etihad Stadium": "伊蒂哈德球场",
    "Anfield": "安菲尔德球场",
    "Stamford Bridge": "斯坦福桥球场",
    "Emirates Stadium": "酋长球场",
    "Tottenham Hotspur Stadium": "托特纳姆热刺球场",
    "Wembley Stadium": "温布利球场",
    "St. James' Park": "圣詹姆斯公园球场",
    "Villa Park": "维拉公园球场",
    "Goodison Park": "古迪逊公园球场",
    "Craven Cottage": "克拉文农场球场",
    "King Power Stadium": "王权球场",
    "St Mary's Stadium": "圣玛丽球场",
    "Molineux Stadium": "莫利纽克斯球场",
    "Selhurst Park": "塞尔赫斯特公园球场",
    "London Stadium": "伦敦体育场",
    "American Express Stadium": "美国运通社区球场",
    "Vitality Stadium": "活力球场",
    "Stadium of Light": "光明球场",
    "City Ground": "城市球场",
    "Bramall Lane": "布拉莫巷球场",
    "Portman Road": "波特曼路球场",
    "Carrow Road": "卡罗路球场",
    "Turf Moor": "特夫摩尔球场",
    "Kenilworth Road": "克尼尔沃思路球场",
    "The Hawthorns": "山楂球场",
    "St Andrew's": "圣安德鲁斯球场",
    "Ewood Park": "埃伍德公园球场",
    "Deepdale": "迪普戴尔球场",
    "Fratton Park": "法顿公园球场",
    "Home Park": "家园公园球场",
    "Stadium MK": "MK球场",
    "Prenton Park": "普伦顿公园球场",
    "Blundell Park": "布伦德尔公园球场",
    "Abbey Stadium": "修道院球场",
    "Whaddon Road": "瓦顿路球场",
    "The Recreation Ground": "娱乐场球场",
    "The Shay": "谢伊球场",
    "The Hive": "蜂巢球场",
    "The Walks": "步行者球场",
    "The Dripping Pan": "滴水盘球场",
    "The Amex": "美国运通社区球场",
    "The American Express Community Stadium": "美国运通社区球场",
    "The Withdean Stadium": "威斯迪恩球场",
    "The Goldstone Ground": "金石球场",
    "The Priestfield Stadium": "普里斯特菲尔德球场",
    "The MEMS Priestfield Stadium": "MEMS普里斯特菲尔德球场",
    "The Gallagher Stadium": "加拉格尔球场",
    "The Crabble Athletic Ground": "克拉布尔体育场",
    "The Homelands": "家园球场",
    "The Fullicks Stadium": "富利克斯球场",
    "The South Kelsey Stadium": "南凯尔西球场",
    "The Northolme": "诺索尔姆球场",
    "The Marsh Lane": "沼泽巷球场",
    "The JimGreenhalgh Stadium": "吉姆格林哈尔希球场",
    "The Brian Addison Stadium": "布莱恩艾迪生球场",
    "The Arriva Stadium": "阿里瓦球场",
    "The Halton Stadium": "哈尔顿球场",
    "The Deva Stadium": "德瓦球场",
    "The Exacta Stadium": "埃克萨克塔球场",
    "The B2net Stadium": "B2网络球场",
    "The Proact Stadium": "普洛科特球场",
    "The Keepmoat Stadium": "基普莫特球场",
    "The Eco-Power Stadium": "生态动力球场",
    "The Merseyrail Community Stadium": "默西铁路社区球场",
    "The Haig Avenue": "黑格大道球场",
    "The Victoria Road": "维多利亚路球场",
    "The Chigwell Construction Stadium": "奇格韦尔建筑球场",
    "The Mayesbrook Park": "梅斯布鲁克公园球场",
    "The Oakside": "橡树边球场",
    "The Millfield": "米尔菲尔德球场",
    "The North Street": "北街球场",
    "The Central Ground": "中央球场",
    "The Queensgate": "皇后门球场",
    "The 3G Pitch": "3G球场",
    "The London Marathon Community Track": "伦敦马拉松社区跑道",
}

# ==================== 工具函数 ====================
def to_simplified(text):
    if ZHCONV_AVAILABLE and text:
        return convert(text, 'zh-hans')
    return text

def clean_team_name(name):
    """去除球队名称中的冗余后缀，但保留“女子”等区分词"""
    if not name:
        return name
    name = to_simplified(name)
    # 去除“足球俱乐部”、“FC”等，但不删除“女子”
    name = re.sub(r'足球俱乐部$|足球队$|俱乐部$', '', name)
    name = re.sub(r'\s*(FC|CF|F\.C\.|C\.F\.|United|City|Athletic|Albion)\s*$', '', name, flags=re.IGNORECASE)
    return name.strip()

def clean_location(loc):
    """清理球场地址：去除反斜杠，取逗号前，翻译，繁转简"""
    if not loc:
        return ""
    loc = loc.replace('\\', '')
    if ',' in loc:
        loc = loc.split(',')[0].strip()
    else:
        loc = loc.strip()
    # 翻译
    for eng, chn in STADIUM_MAP.items():
        if eng in loc:
            loc = loc.replace(eng, chn)
            break
    return to_simplified(loc)

def preprocess_title(title):
    """
    预处理标题：去除开头的数字/字母+空格/横线等，例如“1友谊赛” -> “友谊赛”
    """
    # 去除开头可能存在的序号或特殊字符
    title = re.sub(r'^[\d\W]+\s*', '', title)
    return title.strip()

def extract_teams_and_comp(title):
    """
    从标题中提取主队、客队、赛事，支持多种格式
    返回 (home, away, comp)
    """
    title = preprocess_title(title)
    # 尝试匹配 “赛事 - 主队 vs 客队” 或 “主队 vs 客队 - 赛事”
    match = re.search(r'(.+?)\s*[-–—]\s*(.+?)\s+vs\s+(.+?)\s*$', title, re.IGNORECASE)
    if match:
        comp = match.group(1).strip()
        home = match.group(2).strip()
        away = match.group(3).strip()
        return home, away, comp

    match = re.search(r'(.+?)\s+vs\s+(.+?)\s*[-–—]\s*(.+?)\s*$', title, re.IGNORECASE)
    if match:
        home = match.group(1).strip()
        away = match.group(2).strip()
        comp = match.group(3).strip()
        return home, away, comp

    # 如果没有明确分隔符，假设只有两队
    if ' vs ' in title.lower():
        parts = re.split(r'\s+vs\s+', title, flags=re.IGNORECASE)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip(), ""
    return "", "", ""

# ==================== 足球数据API客户端 ====================
class FootballDataClient:
    # ...（与v5.0相同，略，保持原样）...
    def __init__(self, api_key):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-Auth-Token': api_key,
            'User-Agent': 'Mozilla/5.0'
        })
        self.cache_file = "api_cache.json"
        self.cache = self.load_cache()
    
    def load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_cache(self):
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    def get_match_info(self, date, home_team, away_team):
        # 同v5.0，略
        # 注意：需要完整复制之前的实现
        pass

# ==================== 主处理器 ====================
class CalendarProcessor:
    def __init__(self, api_client):
        self.api_client = api_client
        self.team_map = TEAM_MAP.copy()
        self.comp_map = COMP_MAP.copy()
    
    def process_event(self, event):
        orig_summary = str(event.get('SUMMARY', ''))
        print(f"\n原始标题: {orig_summary}")
        
        # 获取比赛日期
        dtstart = event.get('DTSTART')
        if dtstart and hasattr(dtstart, 'dt'):
            event_date = dtstart.dt
            if isinstance(event_date, datetime):
                date_str = event_date.strftime('%Y-%m-%d')
            else:
                date_str = event_date.strftime('%Y-%m-%d')
        else:
            date_str = None
        
        # 尝试API查询
        home_guess, away_guess, comp_guess = extract_teams_and_comp(orig_summary)
        match_info = None
        if date_str and home_guess and away_guess:
            print(f"  尝试API查询: {date_str} {home_guess} vs {away_guess}")
            match_info = self.api_client.get_match_info(date_str, home_guess, away_guess)
        
        if match_info:
            print(f"  ✅ API匹配成功")
            comp = self.comp_map.get(match_info['competition'], match_info['competition'])
            round_str = f"第{match_info.get('matchday')}轮" if match_info.get('matchday') else ""
            home = self.team_map.get(match_info['homeTeam'], match_info['homeTeam'])
            away = self.team_map.get(match_info['awayTeam'], match_info['awayTeam'])
            home = clean_team_name(home)
            away = clean_team_name(away)
            if round_str:
                new_summary = f"{comp} {round_str} - {home} vs {away}"
            else:
                new_summary = f"{comp} - {home} vs {away}"
            # 地点
            if match_info.get('venue'):
                new_location = clean_location(match_info['venue'])
            else:
                new_location = clean_location(event.get('LOCATION', ''))
        else:
            print(f"  ⚠️ API无匹配，使用本地回退")
            # 回退：使用本地映射翻译
            # 翻译球队
            home = home_guess
            away = away_guess
            # 赛事识别：从原始标题中提取，如果没有则默认为“友谊赛”
            comp = comp_guess
            if not comp:
                # 尝试从标题中找关键词
                lower = orig_summary.lower()
                if 'friendly' in lower or '友谊' in lower:
                    comp = "Friendly"
                elif 'premier' in lower or '英超' in lower:
                    comp = "Premier League"
                elif 'champions league' in lower or '欧冠' in lower:
                    comp = "Champions League"
                elif 'europa league' in lower or '欧联' in lower:
                    comp = "Europa League"
                elif 'fa cup' in lower or '足总杯' in lower:
                    comp = "FA Cup"
                elif 'league cup' in lower or '联赛杯' in lower:
                    comp = "League Cup"
                else:
                    comp = "Friendly"
            # 翻译球队（使用本地映射）
            if home:
                # 先直接映射，如果没找到，保留原词
                home = self.team_map.get(home, home)
            if away:
                away = self.team_map.get(away, away)
            # 清理球队名称（去除冗余后缀）
            home = clean_team_name(home)
            away = clean_team_name(away)
            # 翻译赛事
            comp = self.comp_map.get(comp, comp)
            new_summary = f"{comp} - {home} vs {away}"
            # 地点
            new_location = clean_location(event.get('LOCATION', ''))
        
        print(f"  新标题: {event['SUMMARY']}")
        print(f"  新地点: {new_location}")
        return event

# ==================== 主程序 ====================
def fetch_calendar():
    headers = {'User-Agent': 'Mozilla/5.0'}
    url = OFFICAL_ICS_URL
    if url.startswith('webcal://'):
        url = 'https://' + url[8:]
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        return Calendar.from_ical(resp.text)
    except Exception as e:
        print(f"获取日历失败: {e}")
        return None

def main():
    print("="*70)
    print("曼联中文赛程智能汉化系统 v5.1 - 专业数据源版 + 增强回退")
    print("="*70)
    
    if FOOTBALL_DATA_API_KEY == "YOUR_API_KEY_HERE":
        print("\n❌ 请先在脚本中配置您的 football-data.org API 密钥！")
        print("注册地址：https://www.football-data.org/register")
        return
    
    cal = fetch_calendar()
    if not cal:
        print("❌ 无法获取日历，请检查链接。")
        return
    
    api_client = FootballDataClient(FOOTBALL_DATA_API_KEY)
    processor = CalendarProcessor(api_client)
    
    modified = 0
    for comp in cal.walk():
        if comp.name == "VEVENT":
            processor.process_event(comp)
            modified += 1
    
    with open(OUTPUT_FILE, 'wb') as f:
        f.write(cal.to_ical())
    
    print(f"\n✅ 处理完成，共修改 {modified} 个事件")
    print(f"💾 文件已保存为: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
