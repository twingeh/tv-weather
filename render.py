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

# Клипы Mixkit (Free License). Для дождя у Mixkit другой путь к файлу.
CLIPS = {
    "rain":   ("99839", "https://assets.mixkit.co/active_storage/video_items/99839/1717104607/99839-video-1080.mp4"),
    "snow":   ("3352",  "https://assets.mixkit.co/videos/3352/3352-1080.mp4"),
    "clear":  ("51102", "https://assets.mixkit.co/videos/51102/51102-1080.mp4"),
    "partly": ("26108", "https://assets.mixkit.co/videos/26108/26108-1080.mp4"),
    "cloudy": ("118",   "https://assets.mixkit.co/videos/118/118-1080.mp4"),
    "fog":    ("50936", "https://assets.mixkit.co/videos/50936/50936-1080.mp4"),
    "storm":  ("4422",  "https://assets.mixkit.co/videos/4422/4422-1080.mp4"),
    "night":  ("4433",  "https://assets.mixkit.co/videos/4433/4433-1080.mp4"),
}

URL = ("https://api.open-meteo.com/v1/forecast?latitude=55.7558&longitude=37.6173"
       "&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m,is_day"
       "&hourly=temperature_2m,weather_code,is_day&daily=weather_code,temperature_2m_max,temperature_2m_min"
       "&forecast_days=4&timezone=Europe/Moscow&wind_speed_unit=ms")
d = json.loads(urllib.request.urlopen(URL, timeout=30).read())

MONTHS = "января февраля марта апреля мая июня июля августа сентября октября ноября декабря".split()
WD = "понедельник вторник среда четверг пятница суббота воскресенье".split()
WDS = "Пн Вт Ср Чт Пт Сб Вс".split()

def wmo(code, day=True):
    if code == 0: return ("sun" if day else "moon"), "Ясно", "clear"
    if code in (1, 2): return ("cloud-sun" if day else "moon"), "Переменная облачность", "partly"
    if code == 3: return "cloud", "Пасмурно", "cloudy"
    if code in (45, 48): return "cloud-fog", "Туман", "fog"
    if code in (51, 53, 55, 56, 57): return "cloud-rain", "Морось", "rain"
    if code in (61, 63, 65, 66, 67, 80, 81, 82): return "cloud-rain", "Дождь", "rain"
    if code in (71, 73, 75, 77, 85, 86): return "cloud-snow", "Снег", "snow"
    if code in (95, 96, 99): return "cloud-lightning", "Гроза", "storm"
    return "cloud", "Облачно", "cloudy"

def icon(name, size):
    svg = (HERE / "icons" / f"{name}.svg").read_text()
    return re.sub(r'\sfill="[^"]*"', "", svg).replace("<svg", f'<svg width="{size}" height="{size}" fill="currentColor"', 1)

def t(v):
    r = round(v); return "0°" if r == 0 else f"{r}°"   # минус — типографский
def tm(v): return t(v).replace("-", "−")

cur = d["current"]; now = datetime.datetime.fromisoformat(cur["time"])
day = bool(cur.get("is_day", 1))
ic, desc, kind = wmo(cur["weather_code"], day)
clip_kind = "night" if (not day and kind in ("clear", "partly")) else kind

# ближайшие 12 часов с шагом в 2 часа
hrs = []
for i, ts in enumerate(d["hourly"]["time"]):
    tt = datetime.datetime.fromisoformat(ts)
    if tt > now and (tt - now).total_seconds() <= 12 * 3600 and tt.hour % 2 == 0:
        hrs.append((f"{tt.hour:02d}", wmo(d["hourly"]["weather_code"][i], bool(d["hourly"]["is_day"][i]))[0], d["hourly"]["temperature_2m"][i]))
days = []
for i in range(1, 4):
    dd = datetime.date.fromisoformat(d["daily"]["time"][i])
    days.append((WDS[dd.weekday()], wmo(d["daily"]["weather_code"][i])[0], d["daily"]["temperature_2m_min"][i], d["daily"]["temperature_2m_max"][i]))

hrs_html = "".join(f'<li><span class="k">{h}</span>{icon(n,34)}<span class="v">{tm(v)}</span></li>' for h, n, v in hrs[:6])
days_html = "".join(f'<li><span class="k">{w}</span>{icon(n,30)}<span class="v">{tm(lo)}<i></i>{tm(hi)}</span></li>' for w, n, lo, hi in days)

FONT = next((p for p in ["/usr/share/fonts/opentype/inter/InterVariable.ttf", "/usr/share/fonts/truetype/inter/Inter-Regular.ttf",
                         str(HERE / "fonts" / "InterVariable.ttf")] if pathlib.Path(p).exists()), None)
font_face = f"@font-face{{font-family:'Inter';src:url('file://{FONT}');font-weight:100 900}}" if FONT else ""

html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
{font_face}
html,body{{margin:0;width:{W}px;height:{H}px;background:transparent;overflow:hidden}}
body{{font-family:'Inter','SF Pro Display','Helvetica Neue',Arial,sans-serif;color:#fff;
  font-feature-settings:'tnum' 1,'cv11' 1;-webkit-font-smoothing:antialiased}}
/* мягкая подложка: держит контраст текста над любым роликом, не превращаясь в карточку */
.scrim{{position:absolute;inset:0;
  background:radial-gradient(90% 75% at 0% 0%,rgba(0,0,0,.42) 0%,rgba(0,0,0,0) 70%),
             linear-gradient(180deg,rgba(0,0,0,.50) 0%,rgba(0,0,0,.34) 26%,rgba(0,0,0,.06) 48%,rgba(0,0,0,0) 60%)}}
.w{{position:absolute;left:112px;top:84px;display:grid;grid-template-columns:auto auto auto;column-gap:88px;align-items:start;
  text-shadow:0 1px 3px rgba(0,0,0,.35),0 4px 24px rgba(0,0,0,.30)}}
.city{{font-size:44px;font-weight:600;letter-spacing:-.01em}}
.date{{font-size:24px;font-weight:450;opacity:.82;margin-top:6px}}
.temp{{font-size:176px;font-weight:200;line-height:.86;letter-spacing:-.04em;margin:26px 0 0 -8px}}
.cond{{display:flex;align-items:center;gap:12px;font-size:30px;font-weight:500;margin-top:20px}}
.cond svg{{opacity:.95}}
.hl{{font-size:24px;font-weight:450;opacity:.82;margin-top:8px}}
.col{{padding-top:12px}}
h2{{margin:0 0 18px;font-size:20px;font-weight:600;opacity:.72;letter-spacing:.01em}}
ul{{list-style:none;margin:0;padding:0}}
.hrs{{display:flex;gap:34px;padding-top:6px;border-top:1px solid rgba(255,255,255,.28)}}
.hrs li{{display:flex;flex-direction:column;align-items:center;gap:12px;padding-top:16px}}
.hrs .k{{font-size:22px;font-weight:500;opacity:.78}} .hrs .v{{font-size:27px;font-weight:550}}
.dys{{border-top:1px solid rgba(255,255,255,.28)}}
.dys li{{display:grid;grid-template-columns:52px 40px auto;align-items:center;gap:14px;height:60px;font-size:26px;
  border-bottom:1px solid rgba(255,255,255,.14)}}
.dys li:last-child{{border-bottom:0}}
.dys .k{{font-weight:500;opacity:.85}} .dys .v{{display:flex;align-items:center;gap:12px;font-weight:550}}
.dys i{{display:inline-block;width:64px;height:5px;border-radius:3px;background:linear-gradient(90deg,#9fd6ff,#ffe08a)}}
</style></head><body><div class="scrim"></div>
<div class="w">
 <div><div class="city">Москва</div><div class="date">{WD[now.weekday()].capitalize()}, {now.day} {MONTHS[now.month-1]}</div>
  <div class="temp">{tm(cur['temperature_2m'])}</div>
  <div class="cond">{icon(ic,34)}{desc}</div>
  <div class="hl">Макс. {tm(d['daily']['temperature_2m_max'][0])}  ·  мин. {tm(d['daily']['temperature_2m_min'][0])}</div></div>
 <div class="col"><h2>Ближайшие часы</h2><ul class="hrs">{hrs_html}</ul></div>
 <div class="col"><h2>3 дня</h2><ul class="dys">{days_html}</ul></div>
</div></body></html>"""
page = OUT / "overlay.html"; page.write_text(html, encoding="utf-8")

from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch(**({"channel": "chrome"} if "--chrome" in sys.argv else {}))
    pg = b.new_page(viewport={"width": W, "height": H}); pg.goto(page.as_uri()); pg.wait_for_timeout(600)
    pg.screenshot(path=str(OUT / "overlay.png"), omit_background=True)
    b.close()
if "--overlay" in sys.argv:
    print("overlay", kind, clip_kind); sys.exit()

cid, curl = CLIPS[clip_kind]
src = CACHE / f"{cid}.mp4"
if not src.exists():
    req = urllib.request.Request(curl, headers={"User-Agent": "Mozilla/5.0"})
    src.write_bytes(urllib.request.urlopen(req, timeout=300).read())

dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
                           capture_output=True, text=True, check=True).stdout.strip())
L = min(dur, 20.0)          # длина петли
X = 1.0                     # перекрёстная склейка конца с началом — шва не видно
fc = (f"[0:v]trim=0:{L},setpts=PTS-STARTPTS,scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=25,format=yuv420p,split[a][b];"
      f"[a]trim={X}:{L},setpts=PTS-STARTPTS[main];[b]trim=0:{X},setpts=PTS-STARTPTS[head];"
      f"[main][head]xfade=transition=fade:duration={X}:offset={L-2*X}[loop];"
      f"[loop][1:v]overlay=0:0:format=auto,format=yuv420p[v]")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-i", str(OUT / "overlay.png"), "-filter_complex", fc,
                "-map", "[v]", "-an", "-c:v", "libx264", "-profile:v", "high", "-crf", "21", "-preset", "medium",
                "-movflags", "+faststart", str(OUT / "wall.mp4")], check=True)
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
print("ok", kind, clip_kind, cur["temperature_2m"])
