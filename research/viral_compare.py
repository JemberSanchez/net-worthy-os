"""Segunda pasada: el confounder era el TAMAÑO DEL CANAL.

Comparar "los que explotaron" (166k subs de mediana) contra "los normales" (27 subs) no mide
qué hace explotar: mide que unos tienen audiencia. Aquí se compara SOLO DENTRO de canales
pequeños (<10k subs) — la situación real de Net Worthy — entre los que despegaron y los que no.
"""
import json, re, sys, io, statistics as st
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
p = Path(__file__).resolve().parents[1] / 'data' / 'viral.json'   # lo escribe viral_collect.py
d = json.load(open(p, encoding='utf-8'))
allr = d['treatment'] + d['control']
# dedup por id (un vídeo puede salir en las dos muestras)
seen, rows = set(), []
for r in allr:
    if r['id'] not in seen:
        seen.add(r['id'])
        rows.append(r)

SMALL = 10_000
small = [r for r in rows if r['subs'] < SMALL]
# "despegó" = superó a su propia audiencia por >=10x. Con 1.000 subs eso es 10.000 vistas:
# imposible sin que el ALGORITMO lo empujara fuera de tus seguidores. Ese es el evento a estudiar.
win = [r for r in small if r['mult'] >= 10]
lose = [r for r in small if r['mult'] < 10]

print(f'CANALES PEQUEÑOS (<{SMALL:,} subs), Shorts EN: n={len(small)}')
print(f'  DESPEGARON (>=10x sus subs): {len(win)}')
print(f'  NO despegaron:              {len(lose)}')
print(f'  -> tasa de despegue: {len(win)/max(len(small),1):.1%}\n')

def med(rs, k):
    v = [r[k] for r in rs]
    return st.median(v) if v else 0

print(f'{"metrica":<26} {"DESPEGARON":>12} {"NO":>12}')
for k, lbl in [('subs', 'subs del canal'), ('views', 'vistas'), ('dur', 'duracion s'),
               ('like_rate', 'likes/vista'), ('cmt_rate', 'comentarios/vista'),
               ('age_d', 'edad (dias)'), ('vpd', 'vistas/dia')]:
    print(f'{lbl:<26} {med(win, k):>12,.4f} {med(lose, k):>12,.4f}')

print('\n=== DURACION dentro de canales pequeños ===')
for name, rs in [('DESPEGARON', win), ('NO despeg.', lose)]:
    dd = sorted(r['dur'] for r in rs)
    if not dd:
        continue
    q = lambda pp: dd[min(int(len(dd) * pp), len(dd) - 1)]
    print(f'  {name}: p25={q(.25):>3}s  MEDIANA={q(.5):>3}s  p75={q(.75):>3}s   (n={len(dd)})')

print('\n=== TITULOS dentro de canales pequeños ===')
def feats(rs):
    n = len(rs) or 1
    return {
        'lleva numero': sum(bool(re.search(r'\d', r['title'])) for r in rs) / n,
        'es pregunta': sum('?' in r['title'] for r in rs) / n,
        'lleva hashtag': sum('#' in r['title'] for r in rs) / n,
        'dice you/your': sum(bool(re.search(r'\byou\b|\byour\b', r['title'], re.I)) for r in rs) / n,
        'nombre propio*': sum(bool(re.search(
            r'\b(buffett|ramsey|musk|shaq|bezos|kiyosaki|graham|cuban|trump|powell)\b',
            r['title'], re.I)) for r in rs) / n,
        'largo (caracteres)': st.median([len(r['title']) for r in rs]) if rs else 0,
    }
fw, fl = feats(win), feats(lose)
print(f'{"":<22} {"DESPEGARON":>12} {"NO":>12}')
for k in fw:
    print(f'{k:<22} {fw[k]:>12.2f} {fl[k]:>12.2f}')

print('\n=== LOS QUE DESPEGARON (canal pequeño, ordenados por multiplicador) ===')
for r in sorted(win, key=lambda r: -r['mult'])[:12]:
    print(f"  x{r['mult']:>7,.0f} | {r['views']:>9,}v | {r['subs']:>6,}s | {r['dur']:>3}s | "
          f"like {r['like_rate']:.1%} | {r['title'][:52]}")
