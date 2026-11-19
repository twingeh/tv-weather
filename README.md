# tv-weather

Живой фон для Projectivy Launcher (плагин Overflight): погода в Москве поверх ролика, который подобран под текущую погоду и время суток.

- `render.py` — берёт погоду с Open-Meteo, выбирает ролик Mixkit, накладывает слой с погодой и выкладывает `wall_<время>.mp4` и `videos.json` для Overflight.
- `.github/workflows/build.yml` — запускает `render.py` каждые 30 минут и публикует результат на GitHub Pages.
- Источник для Overflight: `https://twingeh.github.io/tv-weather/videos.json`
- Ролики — Mixkit (Mixkit Stock Video Free License). Иконки погоды — Meteocons monochrome (MIT, `meteocons.json`). Шрифт — Commissioner (SIL OFL, `OFL-Commissioner.txt`).
