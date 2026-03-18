#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
曼联赛程智能汉化脚本 v5.2 - 最终修复版
- 大幅扩充本地球队/球场/赛事翻译映射表
- API 查询失败时，依赖本地映射保证翻译质量
- 标题格式统一为：赛事 - 主队 vs 客队
- 强制简体中文，去除冗余后缀
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
    # 可继续补充
}

# ==================== 本地翻译字典（大幅扩充版）====================
TEAM_MAP = {
    # 曼联
    "Man Utd": "曼联",
    "Manchester United": "曼联",
    "Man United": "曼联",
    # 英超球队
    "Liverpool": "利物浦",
    "Chelsea": "切尔西",
    "Arsenal": "阿森纳",
    "Man City": "曼城",
    "Manchester City": "曼城",
    "Tottenham": "热刺",
    "Tottenham Hotspur": "热刺",
    "Bournemouth": "伯恩茅斯",
    "AFC Bournemouth": "伯恩茅斯",
    "Leeds United": "利兹联",
    "Leeds": "利兹联",
    "Brentford": "布伦特福德",
    "Sunderland": "桑德兰",
    "Nottingham Forest": "诺丁汉森林",
    "Nott'm Forest": "诺丁汉森林",
    "Brighton": "布莱顿",
    "Brighton & Hove Albion": "布莱顿",
    "Brighton and Hove Albion": "布莱顿",
    "Everton": "埃弗顿",
    "Aston Villa": "阿斯顿维拉",
    "Newcastle United": "纽卡斯尔联",
    "Wolverhampton": "狼队",
    "Wolves": "狼队",
    "Crystal Palace": "水晶宫",
    "Fulham": "富勒姆",
    "West Ham United": "西汉姆联",
    "West Ham": "西汉姆联",
    "Southampton": "南安普顿",
    "Leicester City": "莱斯特城",
    "Hull City": "赫尔城",
    "Norwich City": "诺维奇",
    "Watford": "沃特福德",
    "Burnley": "伯恩利",
    "Sheffield United": "谢菲尔德联",
    "Sheffield Utd": "谢菲尔德联",
    "Luton Town": "卢顿",
    "Ipswich Town": "伊普斯维奇",
    "Derby County": "德比郡",
    "Middlesbrough": "米德尔斯堡",
    "Stoke City": "斯托克城",
    "Swansea City": "斯旺西",
    "Cardiff City": "加的夫城",
    "Blackburn Rovers": "布莱克本",
    "Preston North End": "普雷斯顿",
    "Millwall": "米尔沃尔",
    "Bristol City": "布里斯托尔城",
    "Queens Park Rangers": "女王公园巡游者",
    "QPR": "女王公园巡游者",
    "Reading": "雷丁",
    "Birmingham City": "伯明翰",
    "Huddersfield Town": "哈德斯菲尔德",
    "Coventry City": "考文垂",
    "Rotherham United": "罗瑟汉姆",
    "Wycombe Wanderers": "威科姆流浪者",
    "Accrington Stanley": "阿克灵顿斯坦利",
    "Burton Albion": "伯顿",
    "Cambridge United": "剑桥联",
    "Cheltenham Town": "切尔滕汉姆",
    "Exeter City": "埃克塞特城",
    "Forest Green Rovers": "绿色森林",
    "Fleetwood Town": "弗利特伍德",
    "Gillingham": "吉林汉姆",
    "Harrogate Town": "哈罗盖特",
    "Hartlepool United": "哈特尔浦联",
    "Leyton Orient": "莱顿东方",
    "Mansfield Town": "曼斯菲尔德",
    "Newport County": "纽波特郡",
    "Northampton Town": "北安普顿",
    "Oldham Athletic": "奥尔德姆",
    "Port Vale": "韦尔港",
    "Rochdale": "罗奇代尔",
    "Salford City": "索尔福德城",
    "Scunthorpe United": "斯肯索普联",
    "Stevenage": "斯蒂文尼奇",
    "Swindon Town": "斯温登",
    "Tranmere Rovers": "特兰米尔",
    "Walsall": "沃尔索尔",
    "Wigan Athletic": "维冈竞技",
    # 欧战球队
    "Partizan Belgrade": "贝尔格莱德游击",
    "CSKA Moscow": "莫斯科中央陆军",
    "Real Madrid": "皇家马德里",
    "Barcelona": "巴塞罗那",
    "Atletico Madrid": "马德里竞技",
    "Bayern Munich": "拜仁慕尼黑",
    "Borussia Dortmund": "多特蒙德",
    "Bayer Leverkusen": "勒沃库森",
    "Paris Saint-Germain": "巴黎圣日耳曼",
    "PSG": "巴黎圣日耳曼",
    "Juventus": "尤文图斯",
    "AC Milan": "AC米兰",
    "Inter Milan": "国际米兰",
    "Roma": "罗马",
    "Lazio": "拉齐奥",
    "Napoli": "那不勒斯",
    "Ajax": "阿贾克斯",
    "PSV": "埃因霍温",
    "Feyenoord": "费耶诺德",
    "Celtic": "凯尔特人",
    "Rangers": "流浪者",
    "Porto": "波尔图",
    "Benfica": "本菲卡",
    "Sporting CP": "葡萄牙体育",
    "Shakhtar Donetsk": "顿涅茨克矿工",
    "Dynamo Kyiv": "基辅迪纳摩",
    "Lyon": "里昂",
    "Marseille": "马赛",
    "Monaco": "摩纳哥",
    "Nice": "尼斯",
    "Lille": "里尔",
    "Rennes": "雷恩",
    "Real Betis": "皇家贝蒂斯",
    "Sevilla": "塞维利亚",
    "Valencia": "巴伦西亚",
    "Villarreal": "比利亚雷亚尔",
    "Athletic Bilbao": "毕尔巴鄂竞技",
    "Eintracht Frankfurt": "法兰克福",
    "RB Leipzig": "莱比锡红牛",
    "Wolfsburg": "沃尔夫斯堡",
    "Stuttgart": "斯图加特",
    "Mönchengladbach": "门兴格拉德巴赫",
    "Gladbach": "门兴",
    "Köln": "科隆",
    "Hertha Berlin": "柏林赫塔",
    "Union Berlin": "柏林联合",
    "Bochum": "波鸿",
    "Augsburg": "奥格斯堡",
    "Mainz": "美因茨",
    "Hoffenheim": "霍芬海姆",
    "Freiburg": "弗赖堡",
    "Bremen": "不莱梅",
    "Schalke": "沙尔克04",
    "Hamburg": "汉堡",
    "Wrexham": "雷克瑟姆",
    "Wrexham AFC": "雷克瑟姆",
    "Stockport County": "斯托克波特",
    "Chesterfield": "切斯特菲尔德",
    "Woking": "沃金",
    "Barnet": "巴尼特",
    "Bromley": "布罗姆利",
    "Maidenhead United": "梅登黑德联",
    "Dagenham & Redbridge": "达根汉姆",
    "Eastleigh": "伊斯特利",
    "Solihull Moors": "索利赫尔",
    "York City": "约克城",
    "Boston United": "波士顿联",
    "Kidderminster Harriers": "基德明斯特",
    "Hereford": "赫里福德",
    "Aldershot Town": "奥尔德肖特",
    "Torquay United": "托基联",
    "Yeovil Town": "约维尔",
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
    "Russian Premier League": "俄超",
    "Turkish Super Lig": "土超",
    "Belgian Pro League": "比甲",
    "Scottish Premiership": "苏超",
    "Jupiler Pro League": "比甲",
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

# ==================== 工具函数 ====================
def to_simplified(text):
    """繁体转简体"""
    if ZHCONV_AVAILABLE and text:
        return convert(text, 'zh-hans')
    return text

def clean_team_name(name):
    """去除球队名称中的冗余后缀，但保留“女子”等区分词"""
    if not name:
        return name
    name = to_simplified(name)
    # 去除常见后缀（中文）
    name = re.sub(r'足球俱乐部$|足球队$|俱乐部$', '', name)
    # 去除英文后缀（如果翻译后残留）
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
    """预处理标题：去除开头的数字/字母+空格/横线等"""
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
    """从football-data.org获取准确比赛信息"""
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
        """根据日期和球队名查询比赛信息"""
        # 尝试使用球队ID提高准确性
        home_id = TEAM_IDS.get(home_team)
        away_id = TEAM_IDS.get(away_team)

        params = {
            'dateFrom': date,
            'dateTo': date,
            'status': 'SCHEDULED'
        }
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
            resp = self.session.get(FOOTBALL_DATA_API_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            matches = data.get('matches', [])
            if len(matches) == 1:
                match = matches[0]
                result = {
                    'competition': match['competition']['name'],
                    'matchday': match.get('matchday'),
                    'stage': match.get('stage'),
                    'venue': match.get('venue'),
                    'homeTeam': match['homeTeam']['name'],
                    'awayTeam': match['awayTeam']['name'],
                }
                self.cache[cache_key] = {'data': result, 'timestamp': time.time()}
                self.save_cache()
                return result
            elif len(matches) > 1:
                for match in matches:
                    if (match['homeTeam']['name'].lower() == home_team.lower() and
                        match['awayTeam']['name'].lower() == away_team.lower()):
                        result = {
                            'competition': match['competition']['name'],
                            'matchday': match.get('matchday'),
                            'stage': match.get('stage'),
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
            # 赛事识别：从原始标题中提取，如果没有则根据关键词判断
            comp = comp_guess
            if not comp:
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
                home = self.team_map.get(home, home)
            if away:
                away = self.team_map.get(away, away)
            home = clean_team_name(home)
            away = clean_team_name(away)
            # 翻译赛事
            comp = self.comp_map.get(comp, comp)
            new_summary = f"{comp} - {home} vs {away}"
            # 地点
            new_location = clean_location(event.get('LOCATION', ''))

        # 去除多余空格
        new_summary = re.sub(r'\s+', ' ', new_summary).strip()
        event['SUMMARY'] = new_summary
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
    print("曼联中文赛程智能汉化系统 v5.2 - 最终修复版")
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
