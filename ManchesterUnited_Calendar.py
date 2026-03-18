#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
曼联赛程智能汉化脚本 v6.1 - 赛事翻译锁定 + API轮次修复
- 赛事名称仅从本地映射，禁用多源查询，杜绝错误翻译
- 强制“Friendly”译为“友谊赛”
- 详细输出API返回数据，便于调试轮次
- 球队和球场保留多源查询
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
CACHE_FILE = "translation_cache.json"
CACHE_EXPIRY_DAYS = 30

# football-data.org API 配置
FOOTBALL_DATA_API_KEY = "b82d8542ddb94bf0975928cba4f5e9c3"  # 请确认此密钥有效
FOOTBALL_DATA_API_URL = "https://api.football-data.org/v4/matches"

# 球队ID映射
TEAM_IDS = {
    "Manchester United": 66,
    "Man Utd": 66,
    "Liverpool": 64,
    "Arsenal": 57,
    "Chelsea": 61,
    "Tottenham": 73,
    "Manchester City": 65,
    "Real Madrid": 86,
}

# ==================== 本地翻译字典（基础）====================
TEAM_MAP = {
    "Man Utd": "曼联", "Manchester United": "曼联", "Man United": "曼联",
    "Liverpool": "利物浦", "Chelsea": "切尔西", "Arsenal": "阿森纳",
    "Man City": "曼城", "Manchester City": "曼城", "Tottenham": "热刺",
    "Tottenham Hotspur": "热刺", "Bournemouth": "伯恩茅斯", "AFC Bournemouth": "伯恩茅斯",
    "Leeds United": "利兹联", "Leeds": "利兹联", "Brentford": "布伦特福德",
    "Sunderland": "桑德兰", "Nottingham Forest": "诺丁汉森林", "Nott'm Forest": "诺丁汉森林",
    "Brighton": "布莱顿", "Brighton & Hove Albion": "布莱顿", "Brighton and Hove Albion": "布莱顿",
    "Everton": "埃弗顿", "Aston Villa": "阿斯顿维拉", "Newcastle United": "纽卡斯尔联",
    "Wolverhampton": "狼队", "Wolves": "狼队", "Crystal Palace": "水晶宫",
    "Fulham": "富勒姆", "West Ham United": "西汉姆联", "West Ham": "西汉姆联",
    "Southampton": "南安普顿", "Leicester City": "莱斯特城", "Hull City": "赫尔城",
    "Norwich City": "诺维奇", "Watford": "沃特福德", "Burnley": "伯恩利",
    "Sheffield United": "谢菲尔德联", "Sheffield Utd": "谢菲尔德联", "Luton Town": "卢顿",
    "Ipswich Town": "伊普斯维奇", "Derby County": "德比郡", "Middlesbrough": "米德尔斯堡",
    "Stoke City": "斯托克城", "Swansea City": "斯旺西", "Cardiff City": "加的夫城",
    "Blackburn Rovers": "布莱克本", "Preston North End": "普雷斯顿", "Millwall": "米尔沃尔",
    "Bristol City": "布里斯托尔城", "Queens Park Rangers": "女王公园巡游者", "QPR": "女王公园巡游者",
    "Reading": "雷丁", "Birmingham City": "伯明翰", "Huddersfield Town": "哈德斯菲尔德",
    "Coventry City": "考文垂", "Rotherham United": "罗瑟汉姆", "Wycombe Wanderers": "威科姆流浪者",
    "Galatasaray": "加拉塔萨雷", "Galatasaray SK": "加拉塔萨雷",
    "Fenerbahçe": "费内巴切", "Fenerbahce": "费内巴切",
    "Besiktas": "贝西克塔斯", "Beşiktaş": "贝西克塔斯",
    "Rosenborg": "罗森博格", "Rosenborg BK": "罗森博格",
    "Partizan Belgrade": "贝尔格莱德游击", "FK Partizan": "贝尔格莱德游击",
    "Red Star Belgrade": "贝尔格莱德红星", "Crvena Zvezda": "贝尔格莱德红星",
    "CSKA Moscow": "莫斯科中央陆军", "PFC CSKA Moskva": "莫斯科中央陆军",
    "Spartak Moscow": "莫斯科斯巴达", "Lokomotiv Moscow": "莫斯科火车头",
    "Zenit": "泽尼特", "Zenit St Petersburg": "泽尼特",
    "Dynamo Kyiv": "基辅迪纳摩", "Shakhtar Donetsk": "顿涅茨克矿工",
    "Ajax": "阿贾克斯", "PSV": "埃因霍温", "Feyenoord": "费耶诺德",
    "Celtic": "凯尔特人", "Rangers": "流浪者",
    "Porto": "波尔图", "Benfica": "本菲卡", "Sporting CP": "葡萄牙体育",
    "Real Madrid": "皇家马德里", "Barcelona": "巴塞罗那", "Atletico Madrid": "马德里竞技",
    "Bayern Munich": "拜仁慕尼黑", "Borussia Dortmund": "多特蒙德", "Bayer Leverkusen": "勒沃库森",
    "Paris Saint-Germain": "巴黎圣日耳曼", "PSG": "巴黎圣日耳曼", "Lyon": "里昂",
    "Marseille": "马赛", "Monaco": "摩纳哥", "Nice": "尼斯",
    "Juventus": "尤文图斯", "AC Milan": "AC米兰", "Inter Milan": "国际米兰",
    "Roma": "罗马", "Lazio": "拉齐奥", "Napoli": "那不勒斯",
    "Real Betis": "皇家贝蒂斯", "Sevilla": "塞维利亚", "Valencia": "巴伦西亚",
    "Villarreal": "比利亚雷亚尔", "Athletic Bilbao": "毕尔巴鄂竞技",
    "Eintracht Frankfurt": "法兰克福", "RB Leipzig": "莱比锡红牛", "Wolfsburg": "沃尔夫斯堡",
    "Wrexham": "雷克瑟姆", "Wrexham AFC": "雷克瑟姆",
}

STADIUM_MAP = {
    "Old Trafford": "老特拉福德球场",
    "Rams Global Stadium": "拉姆斯全球体育场",
    "Lerkendal Stadium": "莱肯达尔体育场",
    "Wembley Stadium": "温布利球场",
    "Brentford Community Stadium": "布伦特福德社区球场",
    "Amex Stadium": "美国运通社区球场",
    "American Express Stadium": "美国运通社区球场",
    "Etihad Stadium": "伊蒂哈德球场",
    "Anfield": "安菲尔德球场",
    "Stamford Bridge": "斯坦福桥球场",
    "Emirates Stadium": "酋长球场",
    "Tottenham Hotspur Stadium": "托特纳姆热刺球场",
    "St. James' Park": "圣詹姆斯公园球场",
    "Villa Park": "维拉公园球场",
    "Goodison Park": "古迪逊公园球场",
    "Craven Cottage": "克拉文农场球场",
    "King Power Stadium": "王权球场",
    "St Mary's Stadium": "圣玛丽球场",
    "Molineux Stadium": "莫利纽克斯球场",
    "Selhurst Park": "塞尔赫斯特公园球场",
    "London Stadium": "伦敦体育场",
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
    "Snapdragon Stadium": "骁龙体育场",
    "SoFi Stadium": "SoFi体育场",
    "MetLife Stadium": "大都会人寿体育场",
    "NRG Stadium": "NRG体育场",
    "Allegiant Stadium": "忠实体育场",
    "Williams Brice Stadium": "威廉姆斯布莱斯体育场",
    "Murrayfield Stadium": "默里菲尔德球场",
    "Camp Nou": "诺坎普球场",
    "Santiago Bernabéu": "伯纳乌球场",
    "Allianz Arena": "安联球场",
    "Parc des Princes": "王子公园球场",
    "Signal Iduna Park": "威斯特法伦球场",
    "San Siro": "圣西罗球场",
}

COMP_MAP = {
    "Premier League": "英超",
    "English Premier League": "英超",
    "FA Cup": "足总杯",
    "English FA Cup": "足总杯",
    "Carabao Cup": "联赛杯",
    "English League Cup": "联赛杯",
    "EFL Cup": "联赛杯",
    "UEFA Champions League": "欧冠",
    "Champions League": "欧冠",
    "UEFA Europa League": "欧联",
    "Europa League": "欧联",
    "UEFA Conference League": "欧协联",
    "Friendly": "友谊赛",
    "International Friendly": "友谊赛",
    "Club Friendly": "友谊赛",
}

# ==================== 多源翻译获取器（仅用于球队和球场）====================
class TranslationFetcher:
    def __init__(self):
        self.cache = self.load_cache()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})

    def load_cache(self):
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

    def fetch_from_baidu(self, term):
        try:
            url = f"https://baike.baidu.com/search/word?word={term}"
            resp = self.session.get(url, timeout=5)
            if resp.status_code == 200:
                match = re.search(r'<title>(.+?)[_|]百度百科</title>', resp.text)
                if match:
                    return match.group(1).strip()
            time.sleep(0.5)
        except:
            pass
        return None

    def fetch_from_wikipedia(self, term):
        try:
            url = "https://zh.wikipedia.org/w/api.php"
            params = {'action': 'query', 'list': 'search', 'srsearch': term, 'format': 'json', 'srlimit': 1}
            resp = self.session.get(url, params=params, timeout=5)
            data = resp.json()
            if data.get('query', {}).get('search'):
                return data['query']['search'][0]['title']
            time.sleep(0.5)
        except:
            pass
        return None

    def get_translation(self, term, context='team'):
        cache_key = f"{context}:{term}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached['timestamp'] < CACHE_EXPIRY_DAYS * 86400:
                return cached['translation']

        print(f"  多源查询 [{term}]...")
        translation = self.fetch_from_baidu(term)
        if not translation:
            translation = self.fetch_from_wikipedia(term)
        if not translation:
            translation = term

        self.cache[cache_key] = {'translation': translation, 'term': term, 'timestamp': time.time()}
        self.save_cache()
        return translation

# ==================== 工具函数 ====================
def to_simplified(text):
    if ZHCONV_AVAILABLE and text:
        return convert(text, 'zh-hans')
    return text

def clean_team_name(name):
    if not name:
        return name
    name = to_simplified(name)
    name = re.sub(r'足球俱乐部$|足球队$|俱乐部$', '', name)
    name = re.sub(r'\s*(FC|CF|F\.C\.|C\.F\.|United|City|Athletic|Albion|SK|BK)\s*$', '', name, flags=re.IGNORECASE)
    return name.strip()

def clean_location(loc):
    if not loc:
        return ""
    loc = loc.replace('\\', '')
    if ',' in loc:
        loc = loc.split(',')[0].strip()
    else:
        loc = loc.strip()
    for eng, chn in STADIUM_MAP.items():
        if eng.lower() in loc.lower():
            return chn
    return to_simplified(loc)

def preprocess_title(title):
    """去除开头的数字/字母+横线等无关字符"""
    title = re.sub(r'^[A-Za-z0-9]+\s*[-–—]?\s*', '', title)
    title = re.sub(r'^\d+\s*', '', title)
    return title.strip()

def extract_competition(title):
    """从标题中识别赛事名称，仅使用本地COMP_MAP，禁止多源"""
    title_lower = title.lower()
    # 精确匹配COMP_MAP中的键（包括大小写变体）
    for eng, chn in COMP_MAP.items():
        if eng.lower() in title_lower:
            # 找到后，从标题中移除该部分（避免后续干扰球队提取）
            # 但为了简单，我们只返回赛事名，剩余部分可能还需处理
            return chn, title
    # 关键词匹配（确保不会错误匹配）
    if 'friendly' in title_lower or '友谊' in title_lower:
        return "友谊赛", title
    if 'premier' in title_lower or '英超' in title_lower:
        return "英超", title
    if 'champions' in title_lower or '欧冠' in title_lower:
        return "欧冠", title
    if 'europa' in title_lower or '欧联' in title_lower:
        return "欧联", title
    if 'fa cup' in title_lower or '足总杯' in title_lower:
        return "足总杯", title
    if 'league cup' in title_lower or '联赛杯' in title_lower:
        return "联赛杯", title
    return "友谊赛", title  # 默认

def extract_teams(title):
    """从标题中提取主客队（假设标题已去除赛事部分）"""
    if ' vs ' in title.lower():
        parts = re.split(r'\s+vs\s+', title, flags=re.IGNORECASE)
        if len(parts) == 2:
            home = parts[0].strip()
            away = parts[1].strip()
            # 移除可能残留的赛事后缀
            home = re.sub(r'\s*[-–—].*$', '', home)
            away = re.sub(r'\s*[-–—].*$', '', away)
            return home, away
    return "", ""

# ==================== 足球数据API客户端 ====================
class FootballDataClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({'X-Auth-Token': api_key, 'User-Agent': 'Mozilla/5.0'})
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
        """改进版：优先使用球队ID，若失败则从当天所有比赛中模糊匹配"""
        # 尝试使用球队ID构建精确查询
        home_id = TEAM_IDS.get(home_team)
        away_id = TEAM_IDS.get(away_team)
        params = {'dateFrom': date, 'dateTo': date, 'status': 'SCHEDULED'}
        if home_id:
            params['homeTeamId'] = home_id
        if away_id:
            params['awayTeamId'] = away_id

        cache_key = f"{date}|{home_team}|{away_team}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached['timestamp'] < 7*24*3600:
                return cached['data']

        try:
            # 第一次请求：使用球队ID
            resp = self.session.get(FOOTBALL_DATA_API_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            matches = data.get('matches', [])
            if len(matches) == 1:
                match = matches[0]
                result = {
                    'competition': match['competition']['name'],
                    'matchday': match.get('matchday'),
                    'venue': match.get('venue'),
                    'homeTeam': match['homeTeam']['name'],
                    'awayTeam': match['awayTeam']['name'],
                }
                self.cache[cache_key] = {'data': result, 'timestamp': time.time()}
                self.save_cache()
                return result
            elif len(matches) > 1:
                # 如果有多个结果，尝试精确匹配球队名称
                for match in matches:
                    if (home_team.lower() in match['homeTeam']['name'].lower() and
                        away_team.lower() in match['awayTeam']['name'].lower()):
                        result = {
                            'competition': match['competition']['name'],
                            'matchday': match.get('matchday'),
                            'venue': match.get('venue'),
                            'homeTeam': match['homeTeam']['name'],
                            'awayTeam': match['awayTeam']['name'],
                        }
                        self.cache[cache_key] = {'data': result, 'timestamp': time.time()}
                        self.save_cache()
                        return result

            # 如果第一次请求失败（可能因为缺少ID），回退到无ID的全量查询，然后模糊匹配
            if not home_id or not away_id:
                params_no_id = {'dateFrom': date, 'dateTo': date, 'status': 'SCHEDULED'}
                resp2 = self.session.get(FOOTBALL_DATA_API_URL, params=params_no_id, timeout=10)
                resp2.raise_for_status()
                data2 = resp2.json()
                matches2 = data2.get('matches', [])
                for match in matches2:
                    if (home_team.lower() in match['homeTeam']['name'].lower() and
                        away_team.lower() in match['awayTeam']['name'].lower()):
                        result = {
                            'competition': match['competition']['name'],
                            'matchday': match.get('matchday'),
                            'venue': match.get('venue'),
                            'homeTeam': match['homeTeam']['name'],
                            'awayTeam': match['awayTeam']['name'],
                        }
                        self.cache[cache_key] = {'data': result, 'timestamp': time.time()}
                        self.save_cache()
                        return result
            return None
        except Exception as e:
            print(f"API查询失败: {e}")
            return None

# ==================== 主处理器 ====================
class CalendarProcessor:
    def __init__(self, api_client, translator):
        self.api_client = api_client
        self.translator = translator
        self.team_map = self.load_mapping('teams', TEAM_MAP)
        self.stadium_map = self.load_mapping('stadiums', STADIUM_MAP)
        self.comp_map = COMP_MAP.copy()  # 赛事名称不保存到文件，直接使用硬编码

    def load_mapping(self, key, default_dict):
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
            'teams': self.team_map,
            'stadiums': self.stadium_map,
            'updated_at': datetime.now().isoformat()
        }
        with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        print(f"已保存球队和球场映射到 {MAPPING_FILE}")

    def translate_team(self, name):
        if name in self.team_map:
            return self.team_map[name]
        translation = self.translator.get_translation(name, 'team')
        self.team_map[name] = translation
        return translation

    def translate_stadium(self, name):
        if name in self.stadium_map:
            return self.stadium_map[name]
        translation = self.translator.get_translation(name, 'stadium')
        self.stadium_map[name] = translation
        return translation

    def process_event(self, event):
        orig_summary = str(event.get('SUMMARY', ''))
        print(f"\n原始标题: {orig_summary}")

        # 获取比赛日期
        dtstart = event.get('DTSTART')
        date_str = None
        if dtstart and hasattr(dtstart, 'dt'):
            d = dtstart.dt
            if isinstance(d, datetime):
                date_str = d.strftime('%Y-%m-%d')
            else:
                date_str = d.strftime('%Y-%m-%d')

        # 预处理标题，提取球队
        cleaned = preprocess_title(orig_summary)
        home_guess, away_guess = extract_teams(cleaned)

        # 尝试API查询
        match_info = None
        if date_str and home_guess and away_guess:
            print(f"  尝试API查询: {date_str} {home_guess} vs {away_guess}")
            match_info = self.api_client.get_match_info(date_str, home_guess, away_guess)

        if match_info:
            print("  ✅ API匹配成功")
            comp_raw = match_info['competition']
            home_raw = match_info['homeTeam']
            away_raw = match_info['awayTeam']
            venue_raw = match_info.get('venue', '')
            matchday = match_info.get('matchday')
            print(f"    API返回: 赛事={comp_raw}, 主队={home_raw}, 客队={away_raw}, 轮次={matchday}")

            # 赛事名称仅从本地COMP_MAP翻译，禁止多源
            comp = self.comp_map.get(comp_raw, comp_raw)
            if comp not in self.comp_map.values():
                # 如果没找到，尝试关键词匹配
                comp, _ = extract_competition(comp_raw)
            home = self.translate_team(home_raw)
            away = self.translate_team(away_raw)
            venue = self.translate_stadium(venue_raw) if venue_raw else clean_location(event.get('LOCATION', ''))

            home = clean_team_name(home)
            away = clean_team_name(away)
            round_str = f"第{matchday}轮" if matchday else ""
            if round_str:
                new_summary = f"{comp} {round_str} - {home} vs {away}"
            else:
                new_summary = f"{comp} - {home} vs {away}"
            new_location = venue
        else:
            print("  ⚠️ API无匹配，使用本地回退")
            # 赛事识别（仅从本地映射）
            comp, remaining = extract_competition(orig_summary)
            # 赛事名称确保在COMP_MAP中
            if comp not in self.comp_map.values():
                comp = "友谊赛"
            print(f"  识别赛事: {comp}")

            # 提取球队
            home, away = extract_teams(remaining)
            if not home or not away:
                home, away = extract_teams(orig_summary)

            if home:
                home = self.translate_team(home)
            if away:
                away = self.translate_team(away)
            home = clean_team_name(home)
            away = clean_team_name(away)

            new_summary = f"{comp} - {home} vs {away}"
            new_location = clean_location(event.get('LOCATION', ''))

        # 强制简体中文
        new_summary = to_simplified(new_summary)
        new_location = to_simplified(new_location)

        # 最终清理：如果还有英文字母（除了vs），用本地映射再替换一次
        if re.search(r'[a-zA-Z]', new_summary.replace('vs', '')):
            print("  二次清理英文")
            for eng, chn in self.team_map.items():
                new_summary = new_summary.replace(eng, chn)
            new_summary = to_simplified(new_summary)

        event['SUMMARY'] = re.sub(r'\s+', ' ', new_summary).strip()
        if 'LOCATION' in event:
            event['LOCATION'] = new_location
        if 'DESCRIPTION' in event:
            event['DESCRIPTION'] = ""

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
    print("曼联中文赛程智能汉化系统 v6.1 - 赛事翻译锁定 + API轮次调试")
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
    translator = TranslationFetcher()
    processor = CalendarProcessor(api_client, translator)

    modified = 0
    for comp in cal.walk():
        if comp.name == "VEVENT":
            processor.process_event(comp)
            modified += 1

    with open(OUTPUT_FILE, 'wb') as f:
        f.write(cal.to_ical())

    processor.save_all_mappings()
    print(f"\n✅ 处理完成，共修改 {modified} 个事件")
    print(f"💾 文件已保存为: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
