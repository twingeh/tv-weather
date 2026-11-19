"""Живой фон для Projectivy: погода в Москве с анимацией под текущую погоду.

Запуск:  python3 render.py out/            — свежая погода, кадры + wall.mp4 + wall.png
         python3 render.py out/ --preview  — один кадр wall.png (без видео)
Данные: Open-Meteo (бесплатно, без ключа). Иконки: Phosphor (MIT).
Нужны: playwright (chromium) и ffmpeg.
"""
import json, re, sys, math, random, pathlib, datetime, subprocess, urllib.request

OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
PREVIEW = "--preview" in sys.argv
HERE = pathlib.Path(__file__).parent
W, H, FPS, SECONDS = 1920, 1080, 25, 8

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
    return re.sub(r'\sfill="[^"]*"', "", svg).replace("<svg", f'<svg width="{size}" height="{size}" fill="white"', 1)

def t(v):
    r = round(v); return "0°" if r == 0 else f"{r}°"

cur = d["current"]; now = datetime.datetime.fromisoformat(cur["time"])
day = bool(cur.get("is_day", 1))
ic, desc, kind = wmo(cur["weather_code"], day)

hours = []
for i, ts in enumerate(d["hourly"]["time"]):
    tt = datetime.datetime.fromisoformat(ts)
    if tt > now and tt.hour % 2 == 0 and len(hours) < 8:
        hours.append((f"{tt.hour:02d}", wmo(d["hourly"]["weather_code"][i], bool(d["hourly"]["is_day"][i]))[0], d["hourly"]["temperature_2m"][i]))
days = []
for i in range(1, 4):
    dd = datetime.date.fromisoformat(d["daily"]["time"][i])
    days.append((WDS[dd.weekday()], wmo(d["daily"]["weather_code"][i])[0], d["daily"]["temperature_2m_min"][i], d["daily"]["temperature_2m_max"][i]))

SKY = {("clear",1):("#2f6fc2","#7fb6e8"),("clear",0):("#070d22","#1f2d55"),("partly",1):("#4a72a6","#9cb6d6"),("partly",0):("#0f1830","#2f3d62"),
       ("cloudy",1):("#52617a","#8b98a8"),("cloudy",0):("#161c2a","#353e52"),("fog",1):("#77818f","#a6aeb8"),("fog",0):("#262c35","#474f5a"),
       ("rain",1):("#364a62","#66798f"),("rain",0):("#111824","#2c384b"),("snow",1):("#74889f","#b4c2d3"),("snow",0):("#222e45","#52627b"),
       ("storm",1):("#262d3b","#4e576a"),("storm",0):("#0d1018","#262b37")}
top, bot = SKY[(kind, int(day))]

hours_html = "".join(f'<div class="h"><div class="hl">{h}</div>{icon(n,40)}<div class="ht">{t(v)}</div></div>' for h, n, v in hours)
days_html = "".join(f'<div class="d"><span class="dl">{w}</span>{icon(n,34)}<span class="dt">{t(lo)}<span class="bar"></span>{t(hi)}</span></div>' for w, n, lo, hi in days)

html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;width:{W}px;height:{H}px;overflow:hidden;background:{bot};
 font-family:-apple-system,'SF Pro Display','Inter','Helvetica Neue',Arial,sans-serif;color:#fff}}
canvas{{position:absolute;inset:0}}
.top{{position:absolute;left:110px;top:70px;display:flex;align-items:flex-start;gap:56px;text-shadow:0 2px 14px rgba(0,0,0,.22)}}
.city{{font-size:40px;font-weight:500}} .date{{font-size:24px;opacity:.78;margin-top:4px}}
.temp{{font-size:150px;font-weight:200;line-height:1;margin-top:6px;letter-spacing:-4px}}
.desc{{font-size:28px;margin-top:2px}} .hl2{{font-size:24px;opacity:.78;margin-top:4px}}
.card{{margin-top:96px;border-radius:34px;padding:22px 28px;background:rgba(255,255,255,.13);
 box-shadow:inset 0 1.5px 0 rgba(255,255,255,.45),inset 0 0 0 1px rgba(255,255,255,.14),0 14px 40px rgba(0,0,0,.12)}}
.cap{{font-size:17px;letter-spacing:1.2px;text-transform:uppercase;opacity:.62;margin-bottom:14px}}
.hrs{{display:flex;gap:30px}} .h{{display:flex;flex-direction:column;align-items:center;gap:10px}}
.hl{{font-size:20px;opacity:.72}} .ht{{font-size:25px;font-weight:500}}
.d{{display:flex;align-items:center;gap:16px;font-size:24px;height:50px}} .dl{{width:44px;opacity:.8}}
.dt{{display:flex;align-items:center;gap:12px}} .bar{{display:inline-block;width:70px;height:5px;border-radius:3px;background:linear-gradient(90deg,#8fd3ff,#ffd36e)}}
</style></head><body><canvas id="c" width="{W}" height="{H}"></canvas>
<div class="top">
 <div><div class="city">Москва</div><div class="date">{WD[now.weekday()].capitalize()}, {now.day} {MONTHS[now.month-1]}</div>
  <div class="temp">{t(cur['temperature_2m'])}</div><div class="desc">{desc}</div>
  <div class="hl2">Макс. {t(d['daily']['temperature_2m_max'][0])}, мин. {t(d['daily']['temperature_2m_min'][0])}</div></div>
 <div class="card"><div class="cap">Ближайшие часы</div><div class="hrs">{hours_html}</div></div>
 <div class="card"><div class="cap">3 дня</div>{days_html}</div>
</div>
<script>
const KIND="{kind}", DAY={str(day).lower()}, T={SECONDS}, W={W}, H={H};
const c=document.getElementById('c').getContext('2d');
let s=7; const r=()=>(s=(s*16807)%2147483647)/2147483647;
// все движения периодичны с периодом T: видео зацикливается без шва
const rain=[...Array(KIND==='storm'?420:300)].map(()=>({{x:r()*(W+300),y:r()*H,k:1+Math.floor(r()*3),a:.08+r()*.14,l:30+r()*40}}));
const snow=[...Array(380)].map(()=>({{x:r()*W,y:r()*H,k:1,rad:1.5+r()*3.5,a:.25+r()*.5,ph:r()*6.28,amp:10+r()*30}}));
const clouds=[...Array(9)].map(()=>({{x:r()*W,y:-80+r()*620,rx:300+r()*380,ry:90+r()*120,a:.035+r()*.05,k:(r()<.5?1:2)}}));
const stars=[...Array(200)].map(()=>({{x:r()*W,y:r()*H*.7,rad:.6+r()*1.6,ph:r()*6.28,a:.35+r()*.5}}));
window.frame=function(t){{
  const g=c.createLinearGradient(0,0,0,H); g.addColorStop(0,"{top}"); g.addColorStop(1,"{bot}");
  c.fillStyle=g; c.fillRect(0,0,W,H); const p=t/T;
  if(!DAY&&(KIND==='clear'||KIND==='partly')) for(const st of stars){{c.globalAlpha=st.a*(.55+.45*Math.sin(st.ph+p*6.283));c.fillStyle='#fff';c.beginPath();c.arc(st.x,st.y,st.rad,0,6.283);c.fill();}}
  if(KIND==='clear'&&DAY){{const rg=c.createRadialGradient(1500,-60,40,1500,-60,900+40*Math.sin(p*6.283));rg.addColorStop(0,'rgba(255,240,200,.55)');rg.addColorStop(1,'rgba(255,240,200,0)');c.globalAlpha=1;c.fillStyle=rg;c.fillRect(0,0,W,H);}}
  if(['partly','cloudy','fog','rain','snow','storm'].includes(KIND)){{ c.filter='blur(60px)';
    for(const cl of clouds){{
    const x=((cl.x+p*(W+cl.rx*2)*cl.k)%(W+cl.rx*2))-cl.rx; c.globalAlpha=(KIND==='fog'?cl.a*2:cl.a)*1.6; c.fillStyle='#fff';
    c.beginPath(); c.ellipse(x,cl.y,cl.rx,cl.ry,0,0,6.283); c.fill();}} c.filter='none';}}
  if(KIND==='rain'||KIND==='storm'){{c.strokeStyle='#fff';c.lineWidth=2;c.lineCap='round';
    for(const d of rain){{const y=(d.y+p*H*d.k*3)%(H+80)-40, x=d.x-(y*0.28); c.globalAlpha=d.a;
      c.beginPath();c.moveTo(x,y);c.lineTo(x-d.l*0.28,y+d.l);c.stroke();}}}}
  if(KIND==='storm'){{const f=Math.max(0,Math.sin(p*6.283*1)-.97)*25; c.globalAlpha=f*.35; c.fillStyle='#fff'; c.fillRect(0,0,W,H);}}
  if(KIND==='snow') for(const f of snow){{const y=(f.y+p*H*f.k)%(H+20)-10, x=f.x+Math.sin(f.ph+p*6.283)*f.amp;
      c.globalAlpha=f.a;c.fillStyle='#fff';c.beginPath();c.arc(x,y,f.rad,0,6.283);c.fill();}}
  c.globalAlpha=1; const sh=c.createLinearGradient(0,H*.45,0,H); sh.addColorStop(0,'rgba(0,0,0,0)'); sh.addColorStop(1,'rgba(0,0,0,.35)'); c.fillStyle=sh; c.fillRect(0,0,W,H);
}};
window.frame(0);
</script></body></html>"""
page = OUT / "page.html"; page.write_text(html, encoding="utf-8")

from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch(**({"channel": "chrome"} if "--chrome" in sys.argv else {}))
    pg = b.new_page(viewport={"width": W, "height": H}); pg.goto(page.as_uri()); pg.wait_for_timeout(500)
    pg.screenshot(path=str(OUT / "wall.png"))
    if not PREVIEW:
        fr = OUT / "frames"; fr.mkdir(exist_ok=True)
        n = FPS * SECONDS
        for i in range(n):
            pg.evaluate(f"window.frame({i / FPS})")
            pg.screenshot(path=str(fr / f"f{i:04d}.png"))
    b.close()

if not PREVIEW:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(OUT / "frames" / "f%04d.png"),
                    "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "24", "-preset", "slow",
                    "-movflags", "+faststart", str(OUT / "wall.mp4")], check=True)
    (OUT / "index.html").write_text('<!doctype html><meta charset="utf-8"><title>tv-weather</title>'
        f'<p>Обновлено: {cur["time"]} (Москва). <a href="wall.mp4">wall.mp4</a> · <a href="wall.png">wall.png</a></p>', encoding="utf-8")
print("ok", kind, "day" if day else "night", cur["temperature_2m"])
