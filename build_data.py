# -*- coding: utf-8 -*-
"""
Gaming in Russia 2026 — dashboard data builder.
Reads the NAFI/RVI .sav, produces compact microdata JSON for the client-side
interactive dashboard (all cross-tabs, filters and correlations are computed
in the browser from record-level data).
"""
import pyreadstat, json, math, sys
import numpy as np
import pandas as pd

SAV = '/opt/data/workspace/soc_research/data/Города_НАФИ_РВИ_Видеоигры.sav'
OUT = '/opt/data/workspace/gaming2026/data.js'

df, meta = pyreadstat.read_sav(SAV)
vl = meta.variable_value_labels
lab = meta.column_names_to_labels

W = df['WEIGHT'].values.astype(float)

def wshare(mask):
    """weighted share of masked rows among all respondents"""
    m = np.asarray(mask, dtype=bool)
    return float(W[m].sum() / W.sum() * 100)

# ---------------- single-choice variables to keep (code -> label ru) ----------
SINGLE = {
    'sex':      ('S1', {1: 'm', 2: 'f'}),
    'age':      ('S2_1', {1: '14-17', 2: '18-24', 3: '25-34', 4: '35-44', 5: '45-54', 6: '55+'}),
    'fo':       ('FO', {1: 'CFO', 2: 'Moscow', 3: 'SZFO', 4: 'StPetersburg', 5: 'YuFO', 6: 'SKFO', 7: 'PFO', 8: 'UFO', 9: 'SFO', 10: 'DFO'}),
    'mil':      ('MIL_S0_2', {77: 'Moscow', 78: 'StPetersburg', 201: 'Ufa', 1601: 'Kazan', 2301: 'Krasnodar', 2401: 'Krasnoyarsk', 3401: 'Volgograd', 3601: 'Voronezh', 6101: 'RostovOnDon', 6301: 'Samara', 6601: 'Yekaterinburg', 74001: 'Chelyabinsk', 520001: 'NizhnyNovgorod', 540001: 'Novosibirsk', 550001: 'Omsk', 590001: 'Perm'}),
    'citysize': ('LOC_RAZM', {1: 'lt100k', 2: '101-500k', 3: '501k-1m', 4: '1m+'}),
    'gamer':    ('S4_DOP', {1: 'gamer', 2: 'nongamer'}),
    'freq':     ('G1', {1: 'daily', 2: 'weekly', 3: 'rare', 97: 'notlastmonth'}),
    'trend':    ('G2', {1: 'more', 2: 'same', 3: 'less', 99: 'na'}),
    'session':  ('G3', {1: 'lt30m', 2: '30m-1h', 3: '1-3h', 4: '3-5h', 5: '5h+', 99: 'na'}),
    'wkhours':  ('G4_1', {1: 'lt3', 2: '3-6', 3: '7-14', 4: '15+', 99: 'na'}),
    'maindev':  ('G5_0', {1: 'pc', 2: 'console', 3: 'mobile', 4: 'handheld'}),
    'format':   ('G9', {1: 'multiplayer', 2: 'single', 3: 'both', 99: 'na'}),
    'comm':     ('G9_1', {1: 'yes', 2: 'no'}),
    'videos':   ('G10_DOP', {1: 'watch', 97: 'nowatch'}),
    'selfid':   ('G14_DOP', {1: 'yes', 2: 'no'}),
    'esports_aware': ('E1', {1: 'know_well', 2: 'roughly', 3: 'heard', 4: 'first_time'}),
    'esports_def':   ('E2_DOP', {1: 'correct', 2: 'incorrect'}),
    'buy':      ('P1_DOP', {1: 'bought', 97: 'notbought'}),
    'pay_trouble':  ('P5', {1: 'yes', 2: 'no'}),
    'would_buy_if_easy': ('P7', {1: 'rather_yes', 2: 'rather_no', 99: 'na'}),
    'foreign_acc':    ('P8', {1: 'yes', 2: 'no'}),
    'knows_ru_games': ('G11_1_2_DOP', {1: 'knows', 2: 'not'}),
    'plays_ru_games': ('G12_1_2_DOP', {1: 'plays', 2: 'not'}),
    'wants_ru_games': ('G13_1_2_DOP', {1: 'wants', 2: 'not'}),
    'community': ('K1', {1: 'member', 2: 'not'}),
    'child_plays':   ('C1_DOP', {1: 'plays', 2: 'not'}),
    'child_attitude': ('C2', {1: 'positive', 2: 'negative', 99: 'na'}),
    'child_interest': ('C4', {1: 'yes', 2: 'no'}),
    'play_with_child': ('C5', {1: 'yes', 2: 'no'}),
    'child_control':   ('C6', {1: 'yes', 2: 'no', 3: 'sometimes'}),
    'child_time':  ('C7', {1: 'lt30m', 2: '30m-1h', 3: '1-3h', 4: '3-5h', 5: '5h+', 99: 'na'}),
    'edu':     ('D1_DOP', {1: 'no_degree', 2: 'degree'}),
    'work':    ('D2_DOP', {1: 'working', 2: 'not_working'}),
    'income':  ('D3_DOP', {1: 'low', 2: 'mid', 3: 'high'}),
    'marital': ('D4_DOP', {1: 'single', 2: 'married'}),
    'want_start': ('R2_DOP', {1: 'want', 2: 'not'}),
}

# ---------------- multi-select variables --------------------------------------
MULTI = {
    # key: (columns, per-column label)
    'devices':   ([('G5_1', 'pc'), ('G5_2', 'console'), ('G5_3', 'mobile'), ('G5_4', 'handheld')]),
    'ways':      ([(f'G5_1_{i}', v) for i, v in [(1, 'installed'), (2, 'cloud'), (3, 'browser'), (4, 'clubs'), (5, 'vr'), (98, 'other')]]),
    'genres_pc': ([(f'G6_1_{i}', v) for i, v in [(1, 'shooters'), (2, 'simulators'), (3, 'strategy'), (4, 'rpg'), (5, 'puzzles'), (6, 'adventure'), (7, 'sandbox'), (8, 'racing'), (9, 'horror'), (10, 'moba'), (11, 'mmorpg'), (12, 'crpg')]]),
    'genres_console': ([(f'G6_2_{i}', v) for i, v in [(1, 'shooters'), (2, 'simulators'), (3, 'strategy'), (4, 'rpg'), (5, 'puzzles'), (6, 'adventure'), (7, 'sandbox'), (8, 'racing'), (9, 'horror'), (10, 'mmorpg'), (11, 'crpg')]]),
    'genres_mobile': ([(f'G6_3_{i}', v) for i, v in [(1, 'shooters'), (2, 'simulators'), (3, 'strategy'), (4, 'rpg'), (5, 'puzzles'), (6, 'adventure'), (7, 'sandbox'), (8, 'racing'), (9, 'horror'), (10, 'mmorpg')]]),
    'comm_platforms': ([(f'G9_2_{i}', v) for i, v in [(1, 'discord'), (2, 'steam_chat'), (3, 'messengers'), (4, 'videoconf'), (5, 'mumble'), (6, 'revolt'), (7, 'teamspeak'), (8, 'ingame_chat'), (98, 'other')]]),
    'video_types': ([('G10_1', 'streams'), ('G10_2', 'vods'), ('G10_3', 'reviews'), ('G10_4', 'news'), ('G10_98', 'other')]),
    'start_motives': ([(f'M1_{i}', v) for i, v in [(1, 'relax'), (2, 'boredom'), (3, 'immersion'), (4, 'improve'), (5, 'friends_invite'), (6, 'socialize'), (7, 'compete'), (8, 'new_game'), (9, 'skills'), (10, 'habit'), (11, 'content'), (12, 'daily_loot'), (98, 'other'), (99, 'na')]]),
    'stop_motives': ([(f'M2_{i}', v) for i, v in [(1, 'no_time'), (2, 'game_fatigue'), (3, 'failures'), (4, 'lost_interest'), (5, 'tech'), (6, 'toxicity'), (7, 'paywall'), (8, 'guilt'), (9, 'ads'), (98, 'other'), (99, 'na')]]),
    'skills':    ([(f'M4_{i}', v) for i, v in [(1, 'strategy'), (2, 'creativity'), (3, 'teamwork'), (4, 'languages'), (5, 'decisions'), (6, 'coordination'), (7, 'logic'), (8, 'discipline'), (98, 'other'), (97, 'none')]]),
    'sources':   ([(f'M3_{i}', v) for i, v in [(1, 'video_platforms'), (2, 'tg_social'), (3, 'tv'), (4, 'press'), (5, 'online_media'), (6, 'radio'), (98, 'other'), (99, 'na')]]),
    'purchases': ([(f'P1_{i}', v) for i, v in [(1, 'digital'), (2, 'physical'), (3, 'season_pass'), (4, 'subscriptions'), (5, 'ingame'), (97, 'none')]]),
    'buy_ways':  ([(f'P3_{i}', v) for i, v in [(1, 'offline'), (2, 'online'), (3, 'resellers'), (4, 'torrent'), (98, 'other'), (97, 'none')]]),
    'stores':    ([(f'P4_{i}', v) for i, v in [(1, 'vk_play'), (2, 'rustore'), (3, 'cn_stores'), (4, 'ag_ru'), (5, 'steam'), (6, 'appstore'), (7, 'google_play'), (8, 'epic'), (9, 'origin'), (10, 'xbox_store'), (11, 'ps_store'), (12, 'uplay'), (13, 'battle_net'), (98, 'other'), (99, 'na')]]),
    'pay_diffs': ([(f'P6_{i}', v) for i, v in [(1, 'card_limits'), (2, 'prices_fx'), (3, 'fraud'), (4, 'regional_blocks'), (5, 'region_change'), (98, 'other'), (99, 'na')]]),
    'esports_jobs': ([(f'E3_{i}', v) for i, v in [(1, 'developer'), (2, 'game_designer'), (3, 'artist'), (4, 'qa_tester'), (5, 'pro_player'), (6, 'streamer'), (7, 'producer'), (98, 'other'), (97, 'none')]]),
    'notgaming_reasons': ([(f'R1_{i}', v) for i, v in [(1, 'other_leisure'), (2, 'waste_of_time'), (3, 'health'), (4, 'no_time'), (5, 'no_device'), (6, 'dont_know_how'), (7, 'disapproval'), (8, 'age'), (9, 'no_games'), (10, 'lost_interest'), (11, 'never_tried'), (12, 'expensive'), (98, 'other'), (99, 'na')]]),
    'child_games': ([(f'C3_1{i}', v) for i, v in [(1, 'cod'), (2, 'cs'), (3, 'gta'), (4, 'minecraft'), (5, 'dota'), (6, 'genshin'), (7, 'nfs'), (8, 'pubg'), (9, 'sims'), (10, 'fifa')]]),
    'child_devices': ([('C8_1', 'pc'), ('C8_2', 'console'), ('C8_3', 'mobile'), ('C8_4', 'handheld')]),
    'hobbies':   ([(f'S5_{i}', v) for i, v in [(1, 'games'), (2, 'photo_video'), (3, 'digital_art'), (4, 'blog_podcast'), (5, 'programming'), (6, '3d'), (7, 'online_courses'), (98, 'other'), (97, 'none')]]),
    'leisure':   ([(f'S4_{i}', v) for i, v in [(1, 'videogames'), (2, 'boardgames'), (3, 'tv_movies'), (4, 'cinema_theater'), (5, 'books'), (6, 'sport'), (7, 'crafts'), (8, 'internet'), (9, 'learning'), (10, 'travel'), (11, 'music_audiobooks')]]),
}

# L1 attitudes: 1 agree, 2 disagree, 99 na
L1_COLS = {
    1: 'full_culture', 2: 'relax_stress', 3: 'useful_skills', 4: 'communication',
    5: 'interactive_unique', 6: 'competitive_spirit', 7: 'addiction', 8: 'social_isolation',
    9: 'waste_of_time', 10: 'health_harm', 11: 'profession', 12: 'esports_sport',
    13: 'hurts_grades', 14: 'more_violent', 15: 'violence_causes', 16: 'women_play_better',
    17: 'girls_for_characters', 18: 'girls_for_attention', 19: 'women_not_competitive',
    20: 'women_simpler_games',
}
# K2 community attitudes
K2_COLS = {
    1: 'find_like_minded', 2: 'share_experience', 3: 'stay_updated', 4: 'toxic_atmosphere',
    5: 'no_benefit', 6: 'misinformation',
}

# ---------------- extract compact microdata -----------------------------------
n = len(df)
records = {}
# singles
for key, (col, mapping) in SINGLE.items():
    s = df[col]
    out = []
    for v in s:
        try:
            out.append(mapping.get(int(v), None) if pd.notna(v) else None)
        except Exception:
            out.append(None)
    records[key] = out

# multis: store list of tags per respondent
for key, (cols) in MULTI.items():
    out = []
    for i in range(n):
        tags = []
        for col, tag in cols:
            v = df[col].iloc[i]
            if pd.notna(v):
                tags.append(tag)
        out.append(tags)
    records[key] = out

# L1 / K2 attitudes: store 'a' (agree) / 'd' (disagree) / None
for prefix, cols in [('att', L1_COLS), ('att_comm', K2_COLS)]:
    for num, key in cols.items():
        col = f'{prefix[0]}{num}' if False else (f'L1_{num}' if prefix == 'att' else f'K2_{num}')
        s = df[col]
        out = []
        for v in s:
            if pd.isna(v):
                out.append(None)
            elif int(v) == 1:
                out.append('a')
            elif int(v) == 2:
                out.append('d')
            else:
                out.append(None)
        records[key] = out

# weekly hours numeric
records['hours'] = [None if pd.isna(v) else float(v) for v in df['G4_1N']]

# spending: midpoints in RUB per year (for correlation & means)
P2_MID = {1: 500, 2: 2000, 3: 4000, 4: 6500, 5: 9000, 6: 15000, 99: None}
spend = []
for i in range(n):
    total = 0.0
    has = False
    for c in ['P2_1', 'P2_2', 'P2_3', 'P2_4', 'P2_5']:
        v = df[c].iloc[i]
        if pd.notna(v):
            m = P2_MID.get(int(v))
            if m is not None:
                total += m
                has = True
    spend.append(total if has else None)
records['spend'] = spend

# games played last year (G7 slots) — collapse slot columns into tag list
G7_GAME_LABELS = {int(k): v for k, v in vl['G7_11'].items()}
# keep top games by weighted frequency, map to short ids
slot_cols = [f'G7_1{i}' for i in range(1, 11)]
game_counts = {}
for c in slot_cols:
    for v, cnt in df[c].value_counts().items():
        if pd.notna(v) and int(v) not in (98, 999):
            game_counts[int(v)] = game_counts.get(int(v), 0) + int(cnt)
TOPG = sorted(game_counts.items(), key=lambda kv: -kv[1])[:40]
GAME_ID = {g: f'g{i}' for i, (g, _) in enumerate(TOPG)}
games_out = []
for i in range(n):
    tags = []
    for c in slot_cols:
        v = df[c].iloc[i]
        if pd.notna(v):
            iv = int(v)
            if iv in GAME_ID:
                tags.append(GAME_ID[iv])
    games_out.append(tags)
records['games'] = games_out

# russian games know/play/want (G11/G12/G13 columns each = one game)
RU_PC = [('Мир Танков (Леста)', [f'G11_1_{i}' for i in range(1,15)]),
         ]
# build ru game lists
ru_pc_cols = [(f'G11_1_{i}', list(vl[f'G11_1_{i}'].values())[0]) for i in range(1, 15)]
ru_mob_cols = [(f'G11_2_{i}', list(vl[f'G11_2_{i}'].values())[0]) for i in range(1, 9)]
# map ru games to ids for know/play/want
RU_GAMES = {}
for c, name in ru_pc_cols + ru_mob_cols:
    code = int(list(vl[c].keys())[0])
    RU_GAMES[code] = name.split(' (')[0]
RU_ID = {}
for code, name in RU_GAMES.items():
    RU_ID[code] = 'ru' + str(code)

def ru_tags(prefix_cols):
    out = []
    for i in range(n):
        tags = []
        for c, _ in prefix_cols:
            v = df[c].iloc[i]
            if pd.notna(v):
                code = int(list(vl[c].keys())[0])
                tags.append(RU_ID[code])
        out.append(tags)
    return out

records['ru_know'] = ru_tags(ru_pc_cols + ru_mob_cols)
# play: G12
ru_pc12 = [(f'G12_1_{i}', None) for i in range(1, 15)]
ru_mob12 = [(f'G12_2_{i}', None) for i in range(1, 9)]
records['ru_play'] = ru_tags(ru_pc12 + ru_mob12)
ru_pc13 = [(f'G13_1_{i}', None) for i in range(1, 15)]
ru_mob13 = [(f'G13_2_{i}', None) for i in range(1, 9)]
records['ru_want'] = ru_tags(ru_pc13 + ru_mob13)

# weights
records['_w'] = [round(float(w), 4) for w in W]

# ---------------- dictionaries for the UI -------------------------------------
# category label dictionaries ru/en
def D(**kw):
    return kw

DICTS = {
    'sex': D(m=('Мужчины', 'Men'), f=('Женщины', 'Women')),
    'age': D(**{a: (a + ' лет' if a[0].isdigit() and '-' in a else a, {'14-17': '14–17', '18-24': '18–24', '25-34': '25–34', '35-44': '35–44', '45-54': '45–54', '55+': '55+'}[a]) for a in ['14-17', '18-24', '25-34', '35-44', '45-54', '55+']}),
    'fo': D(CFO=('ЦФО (без Москвы)', 'Central FD (w/o Moscow)'), Moscow=('Москва', 'Moscow'), SZFO=('СЗФО (без СПб)', 'Northwestern FD (w/o St. Petersburg)'), StPetersburg=('Санкт-Петербург', 'St. Petersburg'), YuFO=('ЮФО', 'Southern FD'), SKFO=('СКФО', 'North Caucasian FD'), PFO=('ПФО', 'Volga FD'), UFO=('УФО', 'Ural FD'), SFO=('СФО', 'Siberian FD'), DFO=('ДФО', 'Far Eastern FD')),
    'mil': D(Moscow=('Москва', 'Moscow'), StPetersburg=('Санкт-Петербург', 'St. Petersburg'), Ufa=('Уфа', 'Ufa'), Kazan=('Казань', 'Kazan'), Krasnodar=('Краснодар', 'Krasnodar'), Krasnoyarsk=('Красноярск', 'Krasnoyarsk'), Volgograd=('Волгоград', 'Volgograd'), Voronezh=('Воронеж', 'Voronezh'), RostovOnDon=('Ростов-на-Дону', 'Rostov-on-Don'), Samara=('Самара', 'Samara'), Yekaterinburg=('Екатеринбург', 'Yekaterinburg'), Chelyabinsk=('Челябинск', 'Chelyabinsk'), NizhnyNovgorod=('Нижний Новгород', 'Nizhny Novgorod'), Novosibirsk=('Новосибирск', 'Novosibirsk'), Omsk=('Омск', 'Omsk'), Perm=('Пермь', 'Perm')),
    'citysize': D(**{k: (v, v) for k, v in {'lt100k': '< 100 тыс.', '101-500k': '101–500 тыс.', '501k-1m': '501 тыс. – 1 млн', '1m+': '1 млн+'}.items()}),
    'gamer': D(gamer=('Игроки', 'Gamers'), nongamer=('Не играют', 'Non-gamers')),
    'freq': D(daily=('Ежедневно/почти', 'Daily/almost daily'), weekly=('1–2 раза в неделю', '1–2 times a week'), rare=('Эпизодически', 'Occasionally'), notlastmonth=('Не играли за месяц', 'Did not play last month')),
    'trend': D(more=('Больше времени', 'More time'), same=('Столько же', 'About the same'), less=('Меньше времени', 'Less time'), na=('Затрудняюсь', 'Hard to say')),
    'session': D(**{k: (v, v) for k, v in {'lt30m': '< 30 мин', '30m-1h': '30 мин – 1 ч', '1-3h': '1–3 ч', '3-5h': '3–5 ч', '5h+': '5+ ч', 'na': '—'}.items()}),
    'wkhours': D(**{k: (v, v) for k, v in {'lt3': '< 3 ч', '3-6': '3–6 ч', '7-14': '7–14 ч', '15+': '15+ ч', 'na': '—'}.items()}),
    'maindev': D(pc=('Компьютер/ноутбук', 'PC/laptop'), console=('Консоль к ТВ', 'TV console'), mobile=('Телефон/планшет', 'Phone/tablet'), handheld=('Портативная консоль', 'Handheld')),
    'format': D(multiplayer=('Командные игры', 'Multiplayer'), single=('Одиночные прохождения', 'Single-player'), both=('И те, и другие', 'Both'), na=('Затрудняюсь', 'Hard to say')),
    'comm': D(yes=('Общаются', 'Communicate'), no=('Не общаются', 'Do not communicate')),
    'videos': D(watch=('Смотрят', 'Watch'), nowatch=('Не смотрят', 'Do not watch')),
    'selfid': D(yes=('Да', 'Yes'), no=('Нет', 'No')),
    'esports_aware': D(know_well=('Хорошо знаю', 'Know it well'), roughly=('Примерно представляю', 'Roughly understand'), heard=('Слышал слово', 'Heard the word'), first_time=('Впервые слышу', 'First time hearing')),
    'esports_def': D(correct=('Верно определяют', 'Correct definition'), incorrect=('Не верно', 'Incorrect')),
    'buy': D(bought=('Покупали', 'Bought'), notbought=('Не покупали', 'Did not buy')),
    'pay_trouble': D(yes=('Да', 'Yes'), no=('Нет', 'No')),
    'would_buy_if_easy': D(rather_yes=('Скорее да', 'Rather yes'), rather_no=('Скорее нет', 'Rather no'), na=('Затрудняюсь', 'Hard to say')),
    'foreign_acc': D(yes=('Да', 'Yes'), no=('Нет', 'No')),
    'knows_ru_games': {'knows': ('Знают', 'Aware'), 'not': ('Не знают', 'Not aware')},
    'plays_ru_games': {'plays': ('Играют', 'Play'), 'not': ('Не играют', "Don't play")},
    'wants_ru_games': {'wants': ('Хотят', 'Want to'), 'not': ('Не хотят', "Don't want")},
    'community': {'member': ('Состоят', 'Members'), 'not': ('Не состоят', 'Not members')},
    'child_plays': {'plays': ('Дети играют', 'Children play'), 'not': ('Не играют', "Don't play")},
    'child_attitude': D(positive=('Положительно', 'Positive'), negative=('Отрицательно', 'Negative'), na=('Затрудняюсь', 'Hard to say')),
    'child_interest': D(yes=('Интересуются', 'Interested'), no=('Нет', 'Not interested')),
    'play_with_child': D(yes=('Играют вместе', 'Play together'), no=('Не играют вместе', "Don't play together")),
    'child_control': D(yes=('Да', 'Yes'), no=('Нет', 'No'), sometimes=('Иногда', 'Sometimes')),
    'child_time': D(**{k: (v, v) for k, v in {'lt30m': '< 30 мин', '30m-1h': '30 мин – 1 ч', '1-3h': '1–3 ч', '3-5h': '3–5 ч', '5h+': '5+ ч', 'na': '—'}.items()}),
    'edu': D(no_degree=('Без высшего образования', 'No higher education'), degree=('Высшее образование', 'Higher education')),
    'work': D(working=('Работают', 'Working'), not_working=('Не работают', 'Not working')),
    'income': D(low=('Низкий доход', 'Low income'), mid=('Средний доход', 'Middle income'), high=('Высокий доход', 'High income')),
    'marital': D(single=('Не в браке', 'Not married'), married=('В браке', 'Married')),
    'want_start': {'want': ('Хотели бы', 'Would like'), 'not': ('Нет', 'No')},
}

MDICTS = {
    'devices': D(pc=('Компьютер/ноутбук', 'PC/laptop'), console=('Консоль', 'Console'), mobile=('Телефон/планшет', 'Phone/tablet'), handheld=('Портативная консоль', 'Handheld')),
    'ways': D(installed=('Установленные игры', 'Installed games'), cloud=('Облачный гейминг', 'Cloud gaming'), browser=('Браузерные игры', 'Browser games'), clubs=('Компьютерные клубы', 'PC clubs'), vr=('VR-игры', 'VR games'), other=('Другое', 'Other')),
    'genres_pc': D(shooters=('Шутеры', 'Shooters'), simulators=('Симуляторы', 'Simulators'), strategy=('Стратегии', 'Strategy'), rpg=('Ролевые (RPG)', 'RPG'), puzzles=('Головоломки', 'Puzzles'), adventure=('Приключения', 'Adventure'), sandbox=('Песочницы', 'Sandbox'), racing=('Гонки', 'Racing'), horror=('Хорроры', 'Horror'), moba=('MOBA', 'MOBA'), mmorpg=('MMORPG', 'MMORPG'), crpg=('CRPG', 'CRPG')),
    'genres_console': D(shooters=('Шутеры', 'Shooters'), simulators=('Симуляторы', 'Simulators'), strategy=('Стратегии', 'Strategy'), rpg=('Ролевые (RPG)', 'RPG'), puzzles=('Головоломки', 'Puzzles'), adventure=('Приключения', 'Adventure'), sandbox=('Песочницы', 'Sandbox'), racing=('Гонки', 'Racing'), horror=('Хорроры', 'Horror'), moba=('MOBA', 'MOBA'), mmorpg=('MMORPG', 'MMORPG'), crpg=('CRPG', 'CRPG')),
    'genres_mobile': D(shooters=('Шутеры', 'Shooters'), simulators=('Симуляторы', 'Simulators'), strategy=('Стратегии', 'Strategy'), rpg=('Ролевые (RPG)', 'RPG'), puzzles=('Головоломки', 'Puzzles'), adventure=('Приключения', 'Adventure'), sandbox=('Песочницы', 'Sandbox'), racing=('Гонки', 'Racing'), horror=('Хорроры', 'Horror'), casual=('Казуальные', 'Casual'), io=('io-игры', '.io games'), quiz=('Викторины', 'Quiz')),
    'comm_platforms': D(discord=('Discord', 'Discord'), steam_chat=('Steam чат', 'Steam chat'), messengers=('Мессенджеры', 'Messengers'), videoconf=('Видеосвязь', 'Video calls'), mumble=('Mumble', 'Mumble'), revolt=('Revolt', 'Revolt'), teamspeak=('TeamSpeak', 'TeamSpeak'), ingame_chat=('Чаты в играх', 'In-game chats'), other=('Другое', 'Other')),
    'video_types': D(streams=('Стримы', 'Live streams'), vods=('Записи прохождений', 'VODs / walkthroughs'), reviews=('Обзоры', 'Reviews'), news=('Новости индустрии', 'Industry news'), other=('Другое', 'Other')),
    'start_motives': D(relax=('Расслабиться после дел', 'To relax'), boredom=('Скука', 'Boredom'), immersion=('Новые миры и истории', 'New worlds & stories'), improve=('Улучшить результаты', 'Improve results'), friends_invite=('Друзья позвали', 'Friends invited'), socialize=('Общение', 'Socializing'), compete=('Соревнование', 'Competition'), new_game=('Новая игра', 'New game'), skills=('Развитие навыков', 'Skill development'), habit=('Привычка', 'Habit'), content=('Создание контента', 'Content creation'), daily_loot=('Ежедневный лут', 'Daily loot'), other=('Другое', 'Other'), na=('Затрудняюсь', 'Hard to say')),
    'stop_motives': D(no_time=('Нехватка времени', 'Lack of time'), game_fatigue=('Усталость от игры', 'Game fatigue'), failures=('Неудачи в игре', 'Failures in game'), lost_interest=('Потеря интереса', 'Lost interest'), tech=('Технические проблемы', 'Technical issues'), toxicity=('Токсичность игроков', 'Toxic players'), paywall=('Нужно платить', 'Pay-to-progress'), guilt=('Чувство вины', 'Guilt over time'), ads=('Реклама', 'Ads'), other=('Другое', 'Other'), na=('Затрудняюсь', 'Hard to say')),
    'skills': D(strategy=('Стратегическое планирование', 'Strategic planning'), creativity=('Творческое мышление', 'Creative thinking'), teamwork=('Командное взаимодействие', 'Teamwork'), languages=('Иностранные языки', 'Foreign languages'), decisions=('Принятие решений', 'Decision-making'), coordination=('Координация и реакция', 'Coordination & reaction'), logic=('Логическое мышление', 'Logical thinking'), discipline=('Самодисциплина', 'Self-discipline'), other=('Другое', 'Other'), none=('Никакие', 'None')),
    'sources': D(video_platforms=('Видеосервисы', 'Video platforms'), tg_social=('ТГ/соцсети', 'Telegram/social media'), tv=('ТВ', 'TV'), press=('Пресса', 'Press'), online_media=('Интернет-издания', 'Online media'), radio=('Радио', 'Radio'), other=('Другое', 'Other'), na=('Затрудняюсь', 'Hard to say')),
    'purchases': D(digital=('Цифровые копии', 'Digital copies'), physical=('Физические копии', 'Physical copies'), season_pass=('Сезонные пропуски', 'Season passes'), subscriptions=('Подписки', 'Subscriptions'), ingame=('Внутриигровые покупки', 'In-game purchases'), none=('Ничего', 'None')),
    'buy_ways': D(offline=('Офлайн-магазины (лиц.)', 'Offline stores (licensed)'), online=('Онлайн-магазины (лиц.)', 'Online stores (licensed)'), resellers=('Ключи у ресейлеров', 'Reseller keys'), torrent=('Торренты', 'Torrents'), other=('Другое', 'Other'), none=('Не приобретал', 'Did not buy')),
    'stores': D(vk_play=('VK Play', 'VK Play'), rustore=('RuStore', 'RuStore'), cn_stores=('Сторы Xiaomi/Huawei', 'Xiaomi/Huawei stores'), ag_ru=('AG.RU', 'AG.RU'), steam=('Steam', 'Steam'), appstore=('App Store', 'App Store'), google_play=('Google Play', 'Google Play'), epic=('Epic Games', 'Epic Games'), origin=('Origin', 'Origin'), xbox_store=('Xbox Store', 'Xbox Store'), ps_store=('PS Store', 'PS Store'), uplay=('Ubisoft Connect', 'Ubisoft Connect'), battle_net=('Battle.net', 'Battle.net'), other=('Другое', 'Other'), na=('Затрудняюсь', 'Hard to say')),
    'pay_diffs': D(card_limits=('Ограничения карт РФ', 'RU card restrictions'), prices_fx=('Высокие цены', 'High prices (FX)'), fraud=('Мошенничество', 'Fraud'), regional_blocks=('Региональные блокировки', 'Regional blocks'), region_change=('Сложности смены региона', 'Region-change issues'), other=('Другое', 'Other'), na=('Затрудняюсь', 'Hard to say')),
    'esports_jobs': D(developer=('Разработчик', 'Game developer'), game_designer=('Гейм-дизайнер', 'Game designer'), artist=('Художник/3D', 'Artist/3D'), qa_tester=('Тестировщик', 'QA tester'), pro_player=('Киберспортсмен', 'Pro player'), streamer=('Стример/блогер', 'Streamer/blogger'), producer=('Продюсер', 'Producer'), other=('Другое', 'Other'), none=('Ни о каких', 'None')),
    'notgaming_reasons': D(other_leisure=('Другие виды досуга', 'Prefer other leisure'), waste_of_time=('Пустая трата времени', 'Waste of time'), health=('Вред здоровью', 'Health concerns'), no_time=('Нет времени', 'No time'), no_device=('Нет устройства', 'No device'), dont_know_how=('Не умею', "Don't know how"), disapproval=('Не одобряют близкие', 'Disapproved by others'), age=('Не по возрасту', 'Age-appropriate'), no_games=('Нет интересных игр', 'No interesting games'), lost_interest=('Потерял интерес', 'Lost interest'), never_tried=('Никогда не пробовал', 'Never tried'), expensive=('Дорого', 'Too expensive'), other=('Другое', 'Other'), na=('Затрудняюсь', 'Hard to say')),
    'child_games': D(cod=('Call of Duty', 'Call of Duty'), cs=('Counter-Strike', 'Counter-Strike'), gta=('GTA', 'GTA'), minecraft=('Minecraft', 'Minecraft'), dota=('Dota 2', 'Dota 2'), genshin=('Genshin Impact', 'Genshin Impact'), nfs=('Need for Speed', 'Need for Speed'), pubg=('PUBG', 'PUBG'), sims=('The Sims', 'The Sims'), fifa=('FIFA/FC', 'FIFA/FC')),
    'child_devices': D(pc=('Компьютер/ноутбук', 'PC/laptop'), console=('Консоль', 'Console'), mobile=('Телефон/планшет', 'Phone/tablet'), handheld=('Портативная консоль', 'Handheld')),
    'hobbies': D(games=('Видеоигры', 'Video games'), photo_video=('Фото/видео', 'Photo/video'), digital_art=('Диджитал-дизайн', 'Digital design'), blog_podcast=('Блог/подкаст', 'Blog/podcast'), programming=('Программирование', 'Programming'), online_courses=('Онлайн-обучение', 'Online learning'), d3=('3D-моделирование', '3D modelling'), other=('Другое', 'Other'), none=('Ничего', 'None')),
    'leisure': D(videogames=('Видеоигры', 'Video games'), boardgames=('Настольные игры', 'Board games'), tv_movies=('ТВ и кино дома', 'TV & movies at home'), cinema_theater=('Кино, театр, музей', 'Cinema, theater, museum'), books=('Книги', 'Books'), sport=('Спорт', 'Sports'), crafts=('Творчество', 'Crafts'), internet=('Интернет', 'Internet'), learning=('Учёба', 'Learning'), travel=('Путешествия', 'Travel'), music_audiobooks=('Музыка, аудиокниги', 'Music, audiobooks')),
}

ATT_LABELS = {
    'full_culture': ('Видеоигры — полноценная форма досуга', 'Video games are a full-fledged form of leisure'),
    'relax_stress': ('Игры помогают расслабиться и снять стресс', 'Games help relax and relieve stress'),
    'useful_skills': ('Игры развивают полезные навыки', 'Games develop useful skills'),
    'communication': ('Игры — способ общения', 'Games are a way to communicate'),
    'interactive_unique': ('Интерактивность делает игры уникальными', 'Interactivity makes games unique'),
    'competitive_spirit': ('Игры развивают соревновательный дух', 'Games develop competitive spirit'),
    'addiction': ('Игры приводят к зависимости', 'Gaming leads to addiction'),
    'social_isolation': ('Игроки теряют интерес к общению', 'Gamers lose interest in real communication'),
    'waste_of_time': ('Игры — пустая трата времени', 'Games are a waste of time'),
    'health_harm': ('Игры вредят здоровью', 'Games harm health'),
    'profession': ('Игры могут быть профессией', 'Games can be a profession'),
    'esports_sport': ('Киберспорт — настоящая спортивная дисциплина', 'Esports is a real sports discipline'),
    'hurts_grades': ('Игры снижают успеваемость детей', 'Games hurt children\'s grades'),
    'more_violent': ('Игры делают людей агрессивнее', 'Games make people more aggressive'),
    'violence_causes': ('Жестокость в играх вызывает насилие в жизни', 'In-game violence causes real-life violence'),
    'women_play_better': ('Женщины играют в игры лучше мужчин', 'Women play games better than men'),
    'girls_for_characters': ('Девушки играют ради красивых персонажей и романтики', 'Girls play for pretty characters and romance'),
    'girls_for_attention': ('Девушки играют, чтобы привлечь мужчин', 'Girls play to attract men'),
    'women_not_competitive': ('Женщины не любят соревноваться', 'Women don\'t like competing'),
    'women_simpler_games': ('Женщины предпочитают более простые игры', 'Women prefer simpler games'),
}

ATT_COMM_LABELS = {
    'find_like_minded': ('Помогают найти единомышленников', 'Help find like-minded people'),
    'share_experience': ('Удобно обмениваться опытом', 'Convenient to share experience'),
    'stay_updated': ('Способ быть в курсе обновлений', 'Way to stay updated'),
    'toxic_atmosphere': ('Токсичная атмосфера', 'Toxic atmosphere'),
    'no_benefit': ('Не приносят пользы', 'No benefit'),
    'misinformation': ('Распространяют ложную информацию', 'Spread misinformation'),
}

# games labels
GAME_LABELS = {GAME_ID[g]: (str(G7_GAME_LABELS.get(g, g))[:40], str(G7_GAME_LABELS.get(g, g))[:40]) for g, _ in TOPG}
RU_LABELS = {RU_ID[c]: (RU_GAMES[c][:40], RU_GAMES[c][:40]) for c in RU_GAMES}

# ---------------- variable descriptions for "all sections" ---------------------
# question text ru/en for key blocks (shortened)
QUESTIONS = {
    'leisure': ('Чем занимаются в свободное время (часто)', 'Free-time activities (often)'),
    'hobbies': ('Цифровые хобби', 'Digital hobbies'),
    'gamer': ('Факт игры в видеоигры', 'Plays video games'),
    'freq': ('Частота игры за последний месяц', 'Gaming frequency last month'),
    'trend': ('Изменение времени за игрой за год', 'Change in gaming time over the year'),
    'session': ('Длительность игрового сеанса', 'Typical session length'),
    'wkhours': ('Часов за игрой на прошлой неделе', 'Hours played last week'),
    'devices': ('Устройства для игр за месяц', 'Devices used last month'),
    'ways': ('Способы игры за месяц', 'Ways of playing last month'),
    'genres_pc': ('Жанры (ПК)', 'Genres (PC)'),
    'genres_console': ('Жанры (консоли)', 'Genres (consoles)'),
    'genres_mobile': ('Жанры (мобильные)', 'Genres (mobile)'),
    'games': ('Игры за последний год', 'Games played last year'),
    'ru_know': ('Российские игры — знают', 'Russian games — aware'),
    'ru_play': ('Российские игры — играют', 'Russian games — play'),
    'ru_want': ('Российские игры — хотят', 'Russian games — want to play'),
    'format': ('Формат игр', 'Game format preference'),
    'comm': ('Общаются ли во время игры', 'Communicate while playing'),
    'comm_platforms': ('Платформы общения во время игры', 'Communication platforms'),
    'videos': ('Смотрят игровые видео', 'Watch gaming videos'),
    'video_types': ('Типы игровых видео', 'Types of gaming videos'),
    'selfid': ('Считают себя геймером', 'Identify as a gamer'),
    'start_motives': ('Мотивы начать играть', 'Motives to start playing'),
    'stop_motives': ('Причины прекратить игру', 'Reasons to stop playing'),
    'skills': ('Навыки от видеоигр', 'Skills from video games'),
    'sources': ('Источники информации', 'Information sources'),
    'purchases': ('Покупки за последний год', 'Purchases last year'),
    'buy_ways': ('Способы приобретения игр', 'How games are acquired'),
    'stores': ('Магазины игр', 'Game stores'),
    'pay_trouble': ('Трудности с оплатой', 'Payment difficulties'),
    'pay_diffs': ('Типы трудностей с оплатой', 'Types of payment difficulties'),
    'would_buy_if_easy': ('Покупали бы лицензионное при удобной оплате', 'Would buy licensed if payment were easy'),
    'foreign_acc': ('Зарубежные аккаунты для игр/оплаты', 'Foreign accounts for games/payment'),
    'esports_aware': ('Знают, что такое киберспорт', 'Aware of esports'),
    'esports_def': ('Верно определяют киберспорт', 'Define esports correctly'),
    'esports_jobs': ('Профессии индустрии, о которых слышали', 'Industry jobs heard of'),
    'community': ('Участие в игровых сообществах', 'Participation in gaming communities'),
    'child_plays': ('Дети 7–14 играют в видеоигры', 'Children 7–14 play video games'),
    'child_games': ('Игры детей 7–14', 'Children\'s games'),
    'child_attitude': ('Отношение к играм ребёнка', 'Attitude to child\'s gaming'),
    'child_interest': ('Интересуются достижениями ребёнка', 'Interested in child\'s achievements'),
    'play_with_child': ('Играют вместе с ребёнком', 'Play together with children'),
    'child_control': ('Контролируют время ребёнка', 'Control child\'s playtime'),
    'child_time': ('Время ребёнка за играми в день', 'Child\'s daily playtime'),
    'child_devices': ('Устройства детей', 'Children\'s devices'),
    'notgaming_reasons': ('Почему не играют', 'Why people don\'t play'),
    'want_start': ('Хотели бы начать играть', 'Would like to start playing'),
}

META_INFO = {
    'n': n,
    'n_weighted': round(float(W.sum())),
    'gamers_weighted_pct': round(wshare(df['S4_DOP'] == 1), 1),
}

out = {
    'meta': META_INFO,
    'dicts': DICTS,
    'mdicts': MDICTS,
    'attLabels': ATT_LABELS,
    'attCommLabels': ATT_COMM_LABELS,
    'gameLabels': GAME_LABELS,
    'ruLabels': RU_LABELS,
    'questions': QUESTIONS,
    'records': records,
}

with open(OUT, 'w', encoding='utf-8') as f:
    f.write('window.DATA = ')
    json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    f.write(';\n')

print('written', OUT)
import os
print('size MB:', round(os.path.getsize(OUT) / 1e6, 1))
# sanity
print('gamers weighted %:', META_INFO['gamers_weighted_pct'])
print('daily among gamers (weighted):', round(wshare((df['S4_DOP'] == 1) & (df['G1'] == 1)) / (wshare(df['S4_DOP'] == 1) / 100) * 1, 1), '(доля от игроков, %)')
