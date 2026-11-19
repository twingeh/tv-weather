"""Живой фон для Projectivy (через плагин Overflight): реальная съёмка под текущую погоду
в Москве + слой с погодой сверху слева.

Запуск:  python3 render.py out/             — свежая погода: overlay.png, wall.mp4, wall.png, videos.json
         python3 render.py out/ --overlay   — только слой overlay.png (для проверки дизайна)
Погода: Open-Meteo (без ключа). Видео: Mixkit, клипы с Mixkit Stock Video Free License.
Иконки: Phosphor (MIT). Шрифт: Inter (SIL OFL).
"""
import json, re, sys, pathlib, datetime, subprocess, urllib.request

OUT = pathlib.Path(sys.argv[1]).resolve(); OUT.mkdir(parents=True, exist_ok=True)
HERE = pathlib.Path(__file__).resolve().parent
CACHE = HERE / ".clips"; CACHE.mkdir(exist_ok=True)
W, H = 1920, 1080
BASE = "https://twingeh.github.io/tv-weather/"

# Клипы Mixkit (Free License). У части клипов бесплатно открыт только 720p — тогда берётся он.
def mx(i): return [f"https://assets.mixkit.co/videos/{i}/{i}-1080.mp4", f"https://assets.mixkit.co/videos/{i}/{i}-720.mp4"]
SRC = {
    "99839": ["https://assets.mixkit.co/active_storage/video_items/99839/1717104607/99839-video-1080.mp4"],
    "99841": ["https://assets.mixkit.co/active_storage/video_items/99841/1717105845/99841-video-1080.mp4"],
}
# Только горизонтальные клипы: вертикальные (3352, 99841) после обрезки до 16:9 мылятся.
# Пулы по погоде и времени суток; внутри пула ролик меняется раз в 3 часа.
POOLS = {
    ("rain", 1): ["99839"],                    ("rain", 0): ["21144"],
    ("snow", 1): ["26471", "3323"],    ("snow", 0): ["8353", "27439", "27776"],
    ("blizzard", 1): ["29453"],                ("blizzard", 0): ["27377"],
    ("thaw", 1): ["15404"],                    ("thaw", 0): ["21144"],
    ("cloudy", 1): ["118", "9680"],            ("cloudy", 0): ["15711", "12025"],
    ("fog", 1): ["50936"],                     ("fog", 0): ["9678"],
    ("clear", 1): ["51102"],                   ("clear", 0): ["4433", "34873"],
    ("partly", 1): ["26108"],                  ("partly", 0): ["4433", "34873"],
    ("frost", 1): ["47459", "8146"],           ("frost", 0): ["34873"],
    ("storm", 1): ["4422"],                    ("storm", 0): ["4422"],
}

def scene(kind, code, temp, wind):
    """Погода для подбора ролика: базовый вид + редкие случаи."""
    if code in (56, 57, 66, 67): return "thaw"                    # ледяной дождь / морось
    if kind == "snow" and wind >= 9: return "blizzard"           # снег с ветром от 9 м/с
    if kind == "snow" and temp >= 1: return "thaw"               # мокрый снег в оттепель
    if kind in ("clear", "partly") and temp <= -15: return "frost"
    return kind

def pick(sc, day, now):
    pool = POOLS[(sc, int(day))]
    return pool[(now.timetuple().tm_yday * 8 + now.hour // 3) % len(pool)]

URL = ("https://api.open-meteo.com/v1/forecast?latitude=55.7558&longitude=37.6173"
       "&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m,is_day"
       "&hourly=temperature_2m,weather_code,is_day,precipitation_probability&daily=weather_code,temperature_2m_max,temperature_2m_min"
       "&forecast_days=4&timezone=Europe/Moscow&wind_speed_unit=ms")
d = json.loads(urllib.request.urlopen(URL, timeout=30).read())

MONTHS = "января февраля марта апреля мая июня июля августа сентября октября ноября декабря".split()
WD = "понедельник вторник среда четверг пятница суббота воскресенье".split()
WDS = "Пн Вт Ср Чт Пт Сб Вс".split()

def wmo(code, day=True):
    """→ (иконка Meteocons, подпись, вид погоды для ролика)"""
    if code == 0: return ("clear-day" if day else "clear-night"), "Ясно", "clear"
    if code in (1, 2): return ("partly-cloudy-day" if day else "partly-cloudy-night"), "Переменная облачность", "partly"
    if code == 3: return "overcast", "Пасмурно", "cloudy"
    if code in (45, 48): return "fog", "Туман", "fog"
    if code in (51, 53, 55): return "drizzle", "Морось", "rain"
    if code in (56, 57): return "sleet", "Ледяная морось", "rain"
    if code in (61, 63, 65, 80, 81, 82): return "rain", "Дождь", "rain"
    if code in (66, 67): return "sleet", "Ледяной дождь", "rain"
    if code in (71, 73, 75, 77, 85, 86): return "snow", "Снег", "snow"
    if code in (95, 96, 99): return "thunderstorms", "Гроза", "storm"
    return "overcast", "Облачно", "cloudy"

METEO = json.loads((HERE / "meteocons.json").read_text())   # Meteocons monochrome, MIT

def icon(name, size):
    # Meteocons monochrome (MIT); у значка широкие поля — обрезаем viewBox, чтобы рисунок был крупнее
    svg = METEO[name]
    return svg.replace('viewBox="0 0 128 128"', 'viewBox="14 14 100 100"').replace(
        "<svg", f'<svg width="{size}" height="{size}" style="color:#fff;flex:none"', 1)

def t(v):
    r = round(v); return "0°" if r == 0 else f"{r}°"
def tm(v): return t(v).replace("-", "−")   # минус — типографский
def th(v): return '<span class="n">' + tm(v)[:-1] + '<span class="dg">°</span></span>'   # градус тонкий и меньше, как на крупной цифре

cur = d["current"]; now = datetime.datetime.fromisoformat(cur["time"])
day = bool(cur.get("is_day", 1))
ic, desc, kind = wmo(cur["weather_code"], day)
sc = scene(kind, cur["weather_code"], cur["temperature_2m"], cur.get("wind_speed_10m", 0))
clip_kind = f"{sc}/{'день' if day else 'ночь'}"
cid = pick(sc, day, now)

# 5 точек с шагом 3 часа и вероятность осадков
hrs = []
for i, ts in enumerate(d["hourly"]["time"]):
    tt = datetime.datetime.fromisoformat(ts)
    if tt > now and tt.hour % 3 == 0 and len(hrs) < 5:
        hrs.append((f"{tt.hour:02d}", wmo(d["hourly"]["weather_code"][i], bool(d["hourly"]["is_day"][i]))[0],
                    d["hourly"]["temperature_2m"][i], d["hourly"]["precipitation_probability"][i]))
days = []
for i in range(1, 4):
    dd = datetime.date.fromisoformat(d["daily"]["time"][i])
    days.append((f"{WDS[dd.weekday()]}, {dd.day}", wmo(d["daily"]["weather_code"][i])[0],
                 d["daily"]["temperature_2m_min"][i], d["daily"]["temperature_2m_max"][i]))

hrs_html = "".join(f'<li><span class="k">{h}</span>{icon(n,64)}<span class="v">{th(v)}</span><span class="p">{p or 0}%</span></li>'
                   for h, n, v, p in hrs)
days_html = "".join(f'<li><span class="k">{w}</span>{icon(n,60)}<span class="v">{th(lo)}<i></i>{th(hi)}</span></li>' for w, n, lo, hi in days)

FONT = HERE / "Commissioner.ttf"   # SIL OFL, кириллица, наклон осью slnt
font_face = f"@font-face{{font-family:'Commissioner';src:url('{FONT.as_uri()}');font-weight:100 900;font-style:oblique 0deg 12deg}}"

# Сетка совпадает с рядом Projectivy на телевизоре: карточки 212 px с шагом 254, первая с x=72.
# Температура — над карточками 1–2, «Сегодня» — над 3–4, «Дальше» — над 5–6.
html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
{font_face}
html,body{{margin:0;width:{W}px;height:{H}px;background:transparent;overflow:hidden}}
body{{font-family:'Commissioner',sans-serif;font-style:oblique 12deg;color:#fff;font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}}
.scrim{{position:absolute;inset:0;background:
 radial-gradient(70% 70% at 0% 0%,rgba(0,0,0,.35),rgba(0,0,0,0) 70%),
 linear-gradient(180deg,rgba(0,0,0,.64) 0%,rgba(0,0,0,.46) 34%,rgba(0,0,0,.30) 55%,rgba(0,0,0,.48) 70%,rgba(0,0,0,.74) 100%)}}
.b{{position:absolute;text-shadow:0 1px 2px rgba(0,0,0,.45),0 2px 16px rgba(0,0,0,.5)}}
.hero{{left:72px;top:84px;width:466px}} .hours{{left:500px;top:150px;height:292px;padding:22px 30px 18px}} .days{{left:1104px;top:150px;height:292px;padding:22px 30px 10px}}
/* стеклянные плашки, как у карточек приложений */
.hours,.days{{box-sizing:border-box;background:rgba(255,255,255,.11);border:1.5px solid rgba(255,255,255,.26);border-radius:40px;box-shadow:inset 0 1px 0 rgba(255,255,255,.35),0 8px 30px rgba(0,0,0,.18)}}
.city{{font-size:56px;font-weight:650;letter-spacing:-.01em}}
.date{{font-size:30px;font-weight:450;opacity:.88;margin-top:4px}}
.temp{{font-size:240px;font-weight:250;line-height:.9;letter-spacing:-.045em;margin:18px 0 0 -6px}}
.cond svg{{margin-left:-8px}}
.dg{{font-weight:300;font-size:.72em;vertical-align:.32em;margin-left:.02em}}
.temp .deg{{font-size:.5em;vertical-align:.68em;margin-left:.04em;letter-spacing:0;font-weight:250}}
.cond{{display:flex;align-items:center;gap:14px;font-size:36px;font-weight:550;margin-top:8px}}
.hl{{font-size:30px;font-weight:450;opacity:.88;margin-top:6px}}
h2{{margin:0 0 10px;font-size:26px;font-weight:600;opacity:.92;letter-spacing:.02em}}
ul{{list-style:none;margin:0;padding:0}}
.hours ul{{display:flex;gap:18px}}
.hours li{{display:flex;flex-direction:column;align-items:center;gap:5px;width:92px}}
.k{{font-size:28px;font-weight:500;opacity:.92}} .v{{font-size:36px;font-weight:600}} .p{{font-size:26px;color:#dff0ff}}
.days li{{display:grid;grid-template-columns:112px 62px 1fr;align-items:center;height:72px}}
.days .v{{display:flex;align-items:center;gap:14px;font-size:34px;margin-left:16px}}
.days i{{display:inline-block;width:60px;height:5px;border-radius:3px;background:#f2c879}}
</style></head><body><div class="scrim"></div>
<div class="b hero"><div class="city">Москва</div><div class="date">{WD[now.weekday()].capitalize()}, {now.day} {MONTHS[now.month-1]}</div>
 <div class="temp">{tm(cur['temperature_2m'])[:-1]}<span class="deg">°</span></div><div class="cond">{icon(ic,80)}{desc}</div>
 <div class="hl">Макс. {th(d['daily']['temperature_2m_max'][0])} · мин. {th(d['daily']['temperature_2m_min'][0])}</div></div>
<div class="b hours"><h2>Сегодня</h2><ul>{hrs_html}</ul></div>
<div class="b days"><h2>Дальше</h2><ul>{days_html}</ul></div>
</body></html>"""
page = OUT / "overlay.html"; page.write_text(html, encoding="utf-8")

P, FPS = 6, 25                      # период анимации иконок, кадров в секунду
FR = HERE / ".frames"                # кадры слоя: вне папки сайта
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch(**({"channel": "chrome"} if "--chrome" in sys.argv else {}))
    pg = b.new_page(viewport={"width": W, "height": H}); pg.goto(page.as_uri()); pg.wait_for_timeout(600)
    pg.screenshot(path=str(OUT / "overlay.png"), omit_background=True)
    if "--overlay" not in sys.argv:
        # Иконки Meteocons анимированы через SMIL, общий период 6 с (1, 2, 3 и 6 с).
        # Снимаем 150 кадров по 1/25 с, останавливая анимацию на нужном моменте.
        FR.mkdir(exist_ok=True)
        for f in FR.glob("*.png"): f.unlink()
        for i in range(P * FPS):
            pg.evaluate("t => document.querySelectorAll('svg').forEach(s => { s.pauseAnimations(); s.setCurrentTime(t); })", i / FPS)
            pg.screenshot(path=str(FR / f"{i:03d}.png"), omit_background=True)
    b.close()
if "--overlay" in sys.argv:
    print("overlay", kind, clip_kind); sys.exit()

src = CACHE / f"{cid}.mp4"
if not src.exists():
    for u in SRC.get(cid, mx(cid)):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            src.write_bytes(urllib.request.urlopen(req, timeout=300).read()); break
        except Exception as e:
            print("нет", u, e)

dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
                           capture_output=True, text=True, check=True).stdout.strip())
X = 1.0                     # перекрёстная склейка конца с началом — шва не видно
k = max(1, int((min(dur, 20.0) - X) // P))
L = k * P + X               # итоговая петля L−X = k·6 с — целое число периодов иконок
fc = (f"[0:v]trim=0:{L},setpts=PTS-STARTPTS,scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=25,format=yuv420p,split[a][b];"
      f"[a]trim={X}:{L},setpts=PTS-STARTPTS[main];[b]trim=0:{X},setpts=PTS-STARTPTS[head];"
      f"[main][head]xfade=transition=fade:duration={X}:offset={L-2*X}[loop];"
      f"[loop][1:v]overlay=0:0:format=auto:shortest=1,format=yuv420p[v]")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-stream_loop", "-1", "-framerate", str(FPS), "-i", str(FR / "%03d.png"), "-filter_complex", fc,
                "-map", "[v]", "-an", "-c:v", "libx264", "-profile:v", "high", "-crf", "21", "-preset", "medium",
                "-movflags", "+faststart", str(OUT / "loop.mp4")], check=True)
# Петля внутри файла бесшовная, а шов виден, когда лаунчер перезапускает ролик.
# Склеиваем петлю саму с собой до ~1 минуты: перезапуск — раз в минуту, а не каждые 18 с.
reps = max(1, round(60 / (L - X)))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", str(reps - 1), "-i", str(OUT / "loop.mp4"),
                "-c", "copy", "-movflags", "+faststart", str(OUT / "wall.mp4")], check=True)
(OUT / "loop.mp4").unlink()
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "2", "-i", str(OUT / "wall.mp4"), "-frames:v", "1", str(OUT / "wall.png")], check=True)

stamp = cur["time"].replace(":", "").replace("-", "")
# Overflight узнаёт видео по окончанию ссылки: дата — в имени файла, не в ?query
import shutil
shutil.copy(OUT / "wall.mp4", OUT / f"wall_{stamp}.mp4")
# Pages при каждой сборке заменяет сайт целиком, а Overflight держит старую ссылку до часа.
# Поэтому три прошлых ролика переносим в новую сборку: старая ссылка живёт ещё ~1,5 часа.
try:
    keep = json.loads(urllib.request.urlopen(BASE + "keep.json", timeout=20).read())
except Exception:
    keep = []
keep = [n for n in keep if n != f"wall_{stamp}.mp4"][-3:]
for n in list(keep):
    try:
        (OUT / n).write_bytes(urllib.request.urlopen(BASE + n, timeout=60).read())
    except Exception:
        keep.remove(n)
(OUT / "keep.json").write_text(json.dumps(keep + [f"wall_{stamp}.mp4"]), encoding="utf-8")
(OUT / "videos.json").write_text(json.dumps([{
    "location": "Москва", "title": f"{desc}, {tm(cur['temperature_2m'])}",
    "url_1080p": f"{BASE}wall_{stamp}.mp4"}], ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "index.html").write_text('<!doctype html><meta charset="utf-8"><title>tv-weather</title>'
    f'<p>Обновлено: {cur["time"]} (Москва), {desc}. <a href="wall.mp4">wall.mp4</a> · <a href="videos.json">videos.json</a></p>', encoding="utf-8")
print("ok", clip_kind, cid, cur["temperature_2m"])
