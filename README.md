# tv-weather

Живой фон для Projectivy Launcher: погода в Москве с анимацией под текущую погоду.

- `render.py` — берёт погоду с Open-Meteo, рисует 8-секундный зацикленный ролик 1920×1080 (`wall.mp4`) и картинку (`wall.png`).
- `.github/workflows/build.yml` — запускает `render.py` каждые 30 минут и выкладывает результат на GitHub Pages.
- Ссылка для Projectivy: `https://twingeh.github.io/tv-weather/wall.mp4`
- Иконки погоды — Phosphor Icons (MIT).
