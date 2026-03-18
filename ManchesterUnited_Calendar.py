#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
曼联中文赛程终极版 - 多源校对 + FotMob 核对 (完整功能版)
"""

import requests
from icalendar import Calendar, Event
import json
import os
import re
import time
from datetime import datetime, timedelta
from collections import Counter

# 尝试导入 FotMob 库
try:
    from pyfotmob import FotMob
    FOTMOB_AVAILABLE = True
except ImportError:
    FOTMOB_AVAILABLE = False
    print("警告: pyfotmob 未安装，FotMob核对功能将不可用。请运行: pip install pyfotmob")
    class FotMob:
        def get_matches_by_date(self, date):
            return None

# 尝试导入 zhconv (繁转简)
try:
    from zhconv import convert
    ZHCONV_AVAILABLE = True
except ImportError:
    ZHCONV_AVAILABLE = False
    print("警告: zhconv 未安装，繁体转换将跳过。请运行: pip install zhconv")

# ==================== 配置 ====================
GOOGLE_CAL_ICS_URL = "https://calendar.google.com/calendar/ical/ov0dk4m6dedaob7oqse4nrda4s%40group.calendar.google.com/public/basic.ics"
OUTPUT_FILE = "manutd_fixtures_final.ics"
LOCAL_MAP_FILE = "translation_mapping.json"
CACHE_FILE = "translation_cache.json"
FOTMOB_CACHE_FILE = "fotmob_cache.json"
CACHE_EXPIRY_DAYS = 30

# ==================== 本地翻译映射表（初始，会与保存的文件合并）====================
DEFAULT_TEAM_MAP = {
    "Manchester United": "曼联", "Man Utd": "曼联", "Man United": "曼联",
    "Liverpool": "利物浦", "Chelsea": "切尔西", "Arsenal": "阿森纳",
    "Manchester City": "曼城", "Man City": "曼城", "Tottenham Hotspur": "热刺",
    "Tottenham": "热刺", "Leicester City": "莱斯特城", "Everton": "埃弗顿",
    "Aston Villa": "阿斯顿维拉", "Newcastle United": "纽卡斯尔联",
    "Wolverhampton Wanderers": "狼队", "Wolves": "狼队", "Crystal Palace": "水晶宫",
    "Southampton": "南安普顿", "Brighton & Hove Albion": "布莱顿", "Brighton": "布莱顿",
    "Burnley": "伯恩利", "Fulham": "富勒姆", "West Ham United": "西汉姆联",
    "Leeds United": "利兹联", "Nottingham Forest": "诺丁汉森林", "Brentford": "布伦特福德",
    "Bournemouth": "伯恩茅斯", "Hull City": "赫尔城", "Sunderland": "桑德兰",
    "Norwich City": "诺维奇", "Watford": "沃特福德", "Sheffield United": "谢菲尔德联",
    "Luton Town": "卢顿", "Ipswich Town": "伊普斯维奇", "Derby County": "德比郡",
    "Middlesbrough": "米德尔斯堡", "Stoke City": "斯托克城", "Swansea City": "斯旺西",
    "Cardiff City": "加的夫城", "Blackburn Rovers": "布莱克本", "Preston North End": "普雷斯顿",
    "Millwall": "米尔沃尔", "Bristol City": "布里斯托尔城", "Queens Park Rangers": "女王公园巡游者",
    "QPR": "女王公园巡游者", "Reading": "雷丁", "Birmingham City": "伯明翰",
    "Huddersfield Town": "哈德斯菲尔德", "Coventry City": "考文垂", "Rotherham United": "罗瑟汉姆",
    "Wycombe Wanderers": "威科姆流浪者",
    "Galatasaray": "加拉塔萨雷", "Fenerbahçe": "费内巴切", "Besiktas": "贝西克塔斯",
    "Rosenborg": "罗森博格", "Partizan Belgrade": "贝尔格莱德游击", "Red Star Belgrade": "贝尔格莱德红星",
    "CSKA Moscow": "莫斯科中央陆军", "Spartak Moscow": "莫斯科斯巴达", "Zenit": "泽尼特",
    "Dynamo Kyiv": "基辅迪纳摩", "Shakhtar Donetsk": "顿涅茨克矿工",
    "Ajax": "阿贾克斯", "PSV": "埃因霍温", "Feyenoord": "费耶诺德",
    "Celtic": "凯尔特人", "Rangers": "流浪者",
    "Porto": "波尔图", "Benfica": "本菲卡", "Sporting CP": "葡萄牙体育",
    "Real Madrid": "皇家马德里", "Barcelona": "巴塞罗那", "Atletico Madrid": "马德里竞技",
    "Bayern Munich": "拜仁慕尼黑", "Borussia Dortmund": "多特蒙德", "Bayer Leverkusen": "勒沃库森",
    "Paris Saint-Germain": "巴黎圣日耳曼", "PSG": "巴黎圣日耳曼", "Lyon": "里昂",
    "Marseille": "马赛", "Monaco": "摩纳哥", "Nice": "尼斯",
    "Lille": "里尔", "Rennes": "雷恩",
    "Juventus": "尤文图斯", "AC Milan": "AC米兰", "Inter Milan": "国际米兰",
    "Roma": "罗马", "Lazio": "拉齐奥", "Napoli": "那不勒斯",
    "Atalanta": "亚特兰大", "Real Betis": "皇家贝蒂斯", "Sevilla": "塞维利亚",
    "Valencia": "巴伦西亚", "Villarreal": "比利亚雷亚尔", "Athletic Bilbao": "毕尔巴鄂竞技",
    "Eintracht Frankfurt": "法兰克福", "RB Leipzig": "莱比锡红牛", "Wolfsburg": "沃尔夫斯堡",
    "Wrexham": "雷克瑟姆", "Wrexham AFC": "雷克瑟姆",
}

DEFAULT_COMP_MAP = {
    "Premier League": "英超", "English Premier League": "英超",
    "FA Cup": "足总杯", "English FA Cup": "足总杯",
    "Carabao Cup": "联赛杯", "English League Cup": "联赛杯", "EFL Cup": "联赛杯",
    "UEFA Champions League": "欧冠", "Champions League": "欧冠",
    "UEFA Europa League": "欧联", "Europa League": "欧联",
    "UEFA Conference League": "欧协联",
    "Friendly": "友谊赛", "International Friendly": "友谊赛", "Club Friendly": "友谊赛",
}

DEFAULT_STADIUM_MAP = {
    "Old Trafford": "老特拉福德球场",
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
    "Snapdragon Stadium": "骁龙体育场",
    "SoFi Stadium": "SoFi体育场",
    "MetLife Stadium": "大都会人寿体育场",
    "NRG Stadium": "NRG体育场",
    "Allegiant Stadium": "忠实体育场",
    "Williams Brice Stadium": "威廉姆斯布莱斯体育场",
    "Murrayfield Stadium": "默里菲尔德球场",
}

# ==================== 工具函数 ====================
def to_simplified(text):
    if ZHCONV_AVAILABLE and text:
        return convert(text, 'zh-hans')
    return text

def clean_team_name(name):
    """去除球队名称中的冗余后缀"""
    if not name:
        return name
    name = to_simplified(name)
    name = re.sub(r'足球俱乐部$|足球队$|俱乐部$', '', name)
    name = re.sub(r'\s*(FC|CF|F\.C\.|C\.F\.|United|City|Athletic|Albion|SK|BK)\s*$', '', name, flags=re.IGNORECASE)
    return name.strip()

def clean_location(loc):
    """清理球场地址：去除反斜杠，取逗号前"""
    if not loc:
        return ""
    loc = loc.replace('\\', '')
    if ',' in loc:
        loc = loc.split(',')[0].strip()
    else:
        loc = loc.strip()
    return loc

def extract_info(raw_title):
    """从原始标题中猜测主队、客队、赛事"""
    home_guess = away_guess = comp_guess = ""
    parts = raw_title.split(' vs ')
    if len(parts) == 2:
        home_guess = parts[0].strip()
        away_part = parts[1]
        if ' - ' in away_part:
            away_guess, comp_guess = away_part.split(' - ', 1)
            away_guess = away_guess.strip()
            comp_guess = comp_guess.strip()
        else:
            away_guess = away_part.strip()
    return home_guess, away_guess, comp_guess

def force_chinese_except_vs(text):
    """强制文本中只保留中文和VS，删除其他英文字母"""
    # 保护 VS 标记
    text = re.sub(r'VS', '‹VS›', text, flags=re.IGNORECASE)
    text = re.sub(r'vs', '‹vs›', text, flags=re.IGNORECASE)
    # 删除所有英文字母
    text = re.sub(r'[a-zA-Z]', '', text)
    # 恢复 VS
    text = text.replace('‹VS›', 'VS').replace('‹vs›', 'VS')
    # 合并多余空格
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ==================== 多源校对模块 ====================
class MultiSourceVerifier:
    def __init__(self):
        self.cache = self._load_cache()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})

    def _load_cache(self):
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

    def _save_cache(self):
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def _baidu_search(self, term):
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

    def _wikipedia_search(self, term):
        try:
            url = "https://zh.wikipedia.org/w/api.php"
            params = {
                'action': 'query',
                'list': 'search',
                'srsearch': term,
                'format': 'json',
                'srlimit': 1
            }
            resp = self.session.get(url, params=params, timeout=5)
            data = resp.json()
            if data.get('query', {}).get('search'):
                return data['query']['search'][0]['title']
            time.sleep(0.5)
        except:
            pass
        return None

    def _dongqiudi_search(self, term):
        """懂球帝搜索（模拟）"""
        # 由于懂球帝没有公开API，这里仅作占位，实际可考虑解析搜索页
        # 或者暂时只使用百度百科和维基百科
        return None

    def verify(self, term, context='team'):
        cache_key = f"{context}:{term}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached['timestamp'] < CACHE_EXPIRY_DAYS * 86400:
                return cached['translation']

        print(f"  🔍 多源校对 [{term}] ({context})...")
        results = []
        baidu = self._baidu_search(term)
        if baidu:
            results.append(baidu)
        wiki = self._wikipedia_search(term)
        if wiki:
            results.append(wiki)
        # 懂球帝暂不启用
        # dongqiudi = self._dongqiudi_search(term)
        # if dongqiudi:
        #     results.append(dongqiudi)

        if results:
            # 投票选择最常见的
            counter = Counter(results)
            best = counter.most_common(1)[0][0]
        else:
            best = term

        self.cache[cache_key] = {
            'translation': best,
            'term': term,
            'timestamp': time.time()
        }
        self._save_cache()
        return best

# ==================== FotMob 核对模块 ====================
class FotMobVerifier:
    def __init__(self):
        self.client = FotMob() if FOTMOB_AVAILABLE else None
        self.cache = self._load_cache()

    def _load_cache(self):
        if os.path.exists(FOTMOB_CACHE_FILE):
            try:
                with open(FOTMOB_CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        with open(FOTMOB_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def get_match_info(self, date_str, home_team, away_team):
        """根据日期和球队名从FotMob获取比赛信息"""
        if not self.client:
            return None

        cache_key = f"{date_str}|{home_team}|{away_team}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached['timestamp'] < 7*24*3600:
                return cached['data']

        # 转换日期格式为 YYYYMMDD
        date_norm = date_str.replace('-', '')
        try:
            matches = self.client.get_matches_by_date(date_norm)
            if not matches or 'leagues' not in matches:
                return None

            for league in matches['leagues']:
                for match in league.get('matches', []):
                    home = match.get('home', {}).get('name', '')
                    away = match.get('away', {}).get('name', '')
                    # 模糊匹配球队名称
                    if (home_team.lower() in home.lower() and
                        away_team.lower() in away.lower()):
                        match_id = match['id']
                        details = self.client.get_match_details(match_id)
                        round_info = details.get('matchRound') or details.get('round')
                        result = {
                            'round': round_info,
                            'home_team': home,
                            'away_team': away,
                            'competition': league.get('name', ''),
                            'venue': match.get('stadium', {}).get('name', '')
                        }
                        self.cache[cache_key] = {'data': result, 'timestamp': time.time()}
                        self._save_cache()
                        return result
            return None
        except Exception as e:
            print(f"FotMob查询出错: {e}")
            return None

# ==================== ICS 获取与解析 ====================
def fetch_and_parse_ics(url):
    """下载并解析Google Calendar ICS，返回事件列表"""
    events = []
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        cal = Calendar.from_ical(resp.text)
        for component in cal.walk():
            if component.name == "VEVENT":
                summary = str(component.get('SUMMARY', ''))
                dtstart = component.get('DTSTART').dt
                dtend = component.get('DTEND').dt if component.get('DTEND') else None
                location = str(component.get('LOCATION', ''))
                # 确保 dtstart 和 dtend 是 datetime 类型
                if not isinstance(dtstart, datetime):
                    dtstart = datetime.combine(dtstart, datetime.min.time())
                if dtend and not isinstance(dtend, datetime):
                    dtend = datetime.combine(dtend, datetime.min.time())
                events.append({
                    'summary': summary,
                    'dtstart': dtstart,
                    'dtend': dtend,
                    'location_raw': location
                })
        print(f"✅ 成功获取 {len(events)} 个事件")
    except Exception as e:
        print(f"❌ 获取或解析ICS失败: {e}")
    return events

# ==================== ICS 生成 ====================
def generate_ics(events, filename):
    """生成 ICS 文件"""
    cal = Calendar()
    cal.add('prodid', '-//曼联中文赛程//manutd.cn//')
    cal.add('version', '2.0')
    for ev in events:
        event = Event()
        event.add('summary', ev['summary'])
        event.add('dtstart', ev['dtstart'])
        if ev.get('dtend'):
            event.add('dtend', ev['dtend'])
        if ev.get('location'):
            event.add('location', ev['location'])
        cal.add_component(event)
    with open(filename, 'wb') as f:
        f.write(cal.to_ical())
    print(f"✅ ICS文件已生成: {filename}，包含 {len(events)} 个事件")

# ==================== 主处理逻辑 ====================
def main():
    print("="*60)
    print("曼联中文赛程终极版 - 完整功能版")
    print("="*60)

    # 加载本地映射表（如果存在）
    translation_map = {
        "teams": DEFAULT_TEAM_MAP.copy(),
        "competitions": DEFAULT_COMP_MAP.copy(),
        "stadiums": DEFAULT_STADIUM_MAP.copy()
    }
    if os.path.exists(LOCAL_MAP_FILE):
        try:
            with open(LOCAL_MAP_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                for key in translation_map:
                    if key in saved:
                        translation_map[key].update(saved[key])
            print("已加载本地映射表")
        except:
            pass

    # 初始化校对器
    verifier = MultiSourceVerifier()
    fotmob = FotMobVerifier() if FOTMOB_AVAILABLE else None

    # 获取原始赛程
    raw_events = fetch_and_parse_ics(GOOGLE_CAL_ICS_URL)
    if not raw_events:
        print("⚠️ 未从ICS获取到事件，程序结束。")
        return

    processed_events = []

    for event in raw_events:
        print(f"\n处理事件: {event.get('summary')}")

        # 提取猜测信息
        home_guess, away_guess, comp_guess = extract_info(event['summary'])
        date_str = event['dtstart'].strftime('%Y-%m-%d')

        # FotMob 核对
        fotmob_info = None
        if fotmob and home_guess and away_guess:
            fotmob_info = fotmob.get_match_info(date_str, home_guess, away_guess)

        if fotmob_info:
            print("  ✅ FotMob匹配成功")
            comp_raw = fotmob_info['competition']
            home_raw = fotmob_info['home_team']
            away_raw = fotmob_info['away_team']
            round_info = fotmob_info.get('round')
            venue_raw = fotmob_info.get('venue', '')

            # 翻译
            comp_cn = translation_map['competitions'].get(comp_raw, comp_raw)
            home_cn = translation_map['teams'].get(home_raw, home_raw)
            away_cn = translation_map['teams'].get(away_raw, away_raw)

            # 如果本地没有，触发多源校对
            if comp_cn == comp_raw:
                comp_cn = verifier.verify(comp_raw, 'competition')
                translation_map['competitions'][comp_raw] = comp_cn
            if home_cn == home_raw:
                home_cn = verifier.verify(home_raw, 'team')
                translation_map['teams'][home_raw] = home_cn
            if away_cn == away_raw:
                away_cn = verifier.verify(away_raw, 'team')
                translation_map['teams'][away_raw] = away_cn

            round_str = f"第{round_info}轮" if round_info else ""
            new_location = translation_map['stadiums'].get(venue_raw, venue_raw)
            if new_location == venue_raw:
                new_location = verifier.verify(venue_raw, 'stadium')
                translation_map['stadiums'][venue_raw] = new_location
        else:
            print("  ⚠️ FotMob无匹配，使用本地映射+多源校对")
            # 翻译
            comp_cn = translation_map['competitions'].get(comp_guess, comp_guess)
            home_cn = translation_map['teams'].get(home_guess, home_guess)
            away_cn = translation_map['teams'].get(away_guess, away_guess)

            if comp_cn == comp_guess:
                comp_cn = verifier.verify(comp_guess, 'competition')
                translation_map['competitions'][comp_guess] = comp_cn
            if home_cn == home_guess:
                home_cn = verifier.verify(home_guess, 'team')
                translation_map['teams'][home_guess] = home_cn
            if away_cn == away_guess:
                away_cn = verifier.verify(away_guess, 'team')
                translation_map['teams'][away_guess] = away_cn

            round_str = ""
            new_location = translation_map['stadiums'].get(event['location_raw'], event['location_raw'])
            if new_location == event['location_raw']:
                new_location = verifier.verify(event['location_raw'], 'stadium')
                translation_map['stadiums'][event['location_raw']] = new_location

        # 清理球队名称中的冗余后缀
        home_cn = clean_team_name(home_cn)
        away_cn = clean_team_name(away_cn)

        # 构建最终标题
        final_title = f"{comp_cn} {round_str} {home_cn} VS {away_cn}".strip()
        final_title = force_chinese_except_vs(final_title)

        # 更新事件
        event['summary'] = final_title
        event['location'] = new_location
        processed_events.append(event)

        print(f"  新标题: {final_title}")
        print(f"  新地点: {new_location}")

    # 生成 ICS 文件
    generate_ics(processed_events, OUTPUT_FILE)

    # 保存更新后的映射表
    with open(LOCAL_MAP_FILE, 'w', encoding='utf-8') as f:
        json.dump(translation_map, f, ensure_ascii=False, indent=2)
    print(f"映射表已保存到 {LOCAL_MAP_FILE}")

if __name__ == "__main__":
    main()
