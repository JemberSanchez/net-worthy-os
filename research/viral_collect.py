"""Qué distingue a un Short de finanzas que EXPLOTA de uno normal.

METODO — corrige el sesgo de supervivencia del intento anterior (mirar solo a los ganadores no
dice nada: hay que ver si los perdedores hacen lo mismo):
  TRATAMIENTO = order='viewCount' -> los que explotaron.
  CONTROL     = order='date'      -> lo que se publica normalmente en el nicho, ganara o no.
Mismas queries, mismo idioma, mismo tipo. Comparamos las DISTRIBUCIONES, no anecdotas.

Reutiliza el filtro _is_english del proyecto (el título manda; muchos canales mislabelan el audio).
"""
import json, re, sys, io, urllib.request, urllib.parse, statistics as st
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from omega.sources.youtube import _is_english

K = [l.split('=', 1)[1].strip() for l in open(ROOT / '.env')
     if l.startswith('YOUTUBE_API_KEY')][0]
OUT = ROOT / 'data' / 'viral.json'   # data/ está gitignored: es dato crudo, no código
QUERIES = ['personal finance', 'how to build wealth', 'investing tips', 'money advice',
           'saving money', 'stock market explained', 'retirement planning', 'passive income']


def api(ep, **p):
    p['key'] = K
    return json.load(urllib.request.urlopen(
        f'https://www.googleapis.com/youtube/v3/{ep}?' + urllib.parse.urlencode(p, doseq=True)))


def dur_s(d):
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', d or '')
    if not m:
        return 0
    return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)


def collect(order):
    ids = {}
    for q in QUERIES:
        r = api('search', part='id', q=q, type='video', videoDuration='short', order=order,
                maxResults=50, relevanceLanguage='en', publishedAfter='2025-07-01T00:00:00Z')
        for it in r.get('items', []):
            ids[it['id']['videoId']] = q
    rows, chs = [], set()
    idl = list(ids)
    for i in range(0, len(idl), 50):
        d = api('videos', part='snippet,statistics,contentDetails', id=','.join(idl[i:i + 50]))
        for v in d.get('items', []):
            sn, stt = v['snippet'], v['statistics']
            row = {'id': v['id'], 'ch': sn['channelId'], 'chname': sn['channelTitle'],
                   'title': sn['title'], 'language': sn.get('defaultAudioLanguage') or '',
                   'views': int(stt.get('viewCount', 0)), 'likes': int(stt.get('likeCount', 0)),
                   'comments': int(stt.get('commentCount', 0)),
                   'dur': dur_s(v['contentDetails']['duration']), 'pub': sn['publishedAt']}
            if not _is_english(row):          # el filtro del proyecto: el título manda
                continue
            if row['dur'] == 0 or row['dur'] > 180:
                continue
            rows.append(row)
            chs.add(row['ch'])
    subs = {}
    cl = list(chs)
    for i in range(0, len(cl), 50):
        d = api('channels', part='statistics', id=','.join(cl[i:i + 50]))
        for c in d.get('items', []):
            subs[c['id']] = int(c['statistics'].get('subscriberCount', 0))
    now = datetime.now(timezone.utc)
    for r in rows:
        r['subs'] = subs.get(r['ch'], 0)
        age = max((now - datetime.fromisoformat(r['pub'].replace('Z', '+00:00'))).days, 1)
        r['age_d'] = age
        r['vpd'] = round(r['views'] / age, 1)              # vistas/día: demanda sostenida
        r['mult'] = round(r['views'] / max(r['subs'], 1), 2)  # vistas por suscriptor propio
        r['like_rate'] = round(r['likes'] / max(r['views'], 1), 4)
        r['cmt_rate'] = round(r['comments'] / max(r['views'], 1), 5)
    return rows


treat, ctrl = collect('viewCount'), collect('date')
json.dump({'treatment': treat, 'control': ctrl}, open(OUT, 'w', encoding='utf-8'),
          ensure_ascii=False)


def med(rows, k):
    v = [r[k] for r in rows]
    return st.median(v) if v else 0


print(f'TRATAMIENTO (explotaron): n={len(treat)}   CONTROL (normales): n={len(ctrl)}')
print(f'  ambos filtrados a EN por el filtro del proyecto, Shorts <=180s\n')
print(f'{"metrica":<28} {"EXPLOTARON":>14} {"CONTROL":>14}')
for k, lbl in [('views', 'vistas (mediana)'), ('subs', 'subs del canal'),
               ('mult', 'vistas / suscriptor'), ('dur', 'duracion s'),
               ('vpd', 'vistas/dia'), ('like_rate', 'likes/vista'), ('cmt_rate', 'comentarios/vista')]:
    print(f'{lbl:<28} {med(treat, k):>14,.4f} {med(ctrl, k):>14,.4f}')

print('\n=== DURACION: distribucion (la unica metrica que no depende de mi interpretacion) ===')
for name, rows in [('EXPLOTARON', treat), ('CONTROL   ', ctrl)]:
    d = sorted(r['dur'] for r in rows)
    if not d:
        continue
    q = lambda p: d[min(int(len(d) * p), len(d) - 1)]
    print(f'  {name}: p10={q(.1):>3}s  p25={q(.25):>3}s  MEDIANA={q(.5):>3}s  p75={q(.75):>3}s  p90={q(.9):>3}s')

print('\n=== TITULOS: que distingue a los que explotan ===')
def feats(rows):
    n = len(rows) or 1
    return {
        'lleva numero': sum(bool(re.search(r'\d', r['title'])) for r in rows) / n,
        'es pregunta': sum('?' in r['title'] for r in rows) / n,
        'lleva hashtag': sum('#' in r['title'] for r in rows) / n,
        'GRITA (2+ MAYUS)': sum(len(re.findall(r'\b[A-Z]{2,}\b', r['title'])) >= 2 for r in rows) / n,
        'dice "you/your"': sum(bool(re.search(r'\byou\b|\byour\b', r['title'], re.I)) for r in rows) / n,
        'largo titulo (car)': st.median([len(r['title']) for r in rows]) if rows else 0,
    }
ft, fc = feats(treat), feats(ctrl)
print(f'{"":<22} {"EXPLOTARON":>12} {"CONTROL":>12}')
for k in ft:
    print(f'{k:<22} {ft[k]:>12.2f} {fc[k]:>12.2f}')
