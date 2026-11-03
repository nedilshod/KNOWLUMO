# Комплект Episode 01 — Knowlumo

Ветка: [`arena/da8b0093-knowlumo`](https://github.com/nedilshod/KNOWLUMO/tree/arena/da8b0093-knowlumo). Коммит загрузки: `454eddb`.

## Прямые ссылки GitHub

- [Обновлённое длинное видео — просмотр](https://github.com/nedilshod/KNOWLUMO/blob/arena/da8b0093-knowlumo/output/episode01/CSCA_Math_01_Sets_Full_With_Outro.mp4) · [прямой файл](https://github.com/nedilshod/KNOWLUMO/raw/refs/heads/arena/da8b0093-knowlumo/output/episode01/CSCA_Math_01_Sets_Full_With_Outro.mp4)
- [Обложка PNG](https://github.com/nedilshod/KNOWLUMO/blob/arena/da8b0093-knowlumo/output/episode01/CSCA_Math_01_Sets_Thumbnail_1280x720.png) · [JPG](https://github.com/nedilshod/KNOWLUMO/blob/arena/da8b0093-knowlumo/output/episode01/CSCA_Math_01_Sets_Thumbnail_1280x720.jpg)
- [Вертикальный Shorts/Reels — просмотр](https://github.com/nedilshod/KNOWLUMO/blob/arena/da8b0093-knowlumo/output/shorts/CSCA_Math_01_Sets_Shorts_1080x1920.mp4) · [прямой файл](https://github.com/nedilshod/KNOWLUMO/raw/refs/heads/arena/da8b0093-knowlumo/output/shorts/CSCA_Math_01_Sets_Shorts_1080x1920.mp4)
- [Метаданные длинного видео](https://github.com/nedilshod/KNOWLUMO/blob/arena/da8b0093-knowlumo/output/episode01/VIDEO_01_EN.txt) · [метаданные Shorts](https://github.com/nedilshod/KNOWLUMO/blob/arena/da8b0093-knowlumo/output/shorts/SHORTS_01_EN.txt) · [тайминги](https://github.com/nedilshod/KNOWLUMO/blob/arena/da8b0093-knowlumo/output/shorts/timeline.json)
- [Исходный урок без изменений](https://github.com/nedilshod/KNOWLUMO/blob/arena/da8b0093-knowlumo/sources/Youtube-arena-01b47ded-youtube/csca/episode01/output/CSCA_Math_01_Sets_Full.mp4) · [архив предыдущего проекта](https://github.com/nedilshod/KNOWLUMO/blob/arena/da8b0093-knowlumo/Youtube-arena-01b47ded-youtube.zip)
- [Локальная страница-превью](https://github.com/nedilshod/KNOWLUMO/blob/arena/da8b0093-knowlumo/output/index.html)

Это внутренние примечания на русском. Все публичные материалы канала — названия, описания, текст в видео, озвучка и субтитры — на английском.

## Что готово

1. **Обновлённый длинный урок**
   - `episode01/CSCA_Math_01_Sets_Full_With_Outro.mp4`
   - Исходный урок без изменений: `../sources/Youtube-arena-01b47ded-youtube/csca/episode01/output/CSCA_Math_01_Sets_Full.mp4`
   - Отдельно собранная заставка: `episode01/CSCA_Math_01_Sets_Outro.mp4`
   - Параметры финального файла: 1280 × 720, 30 FPS, H.264, AAC 44.1 kHz stereo, 5:42.65.
   - Исходный урок: 5:30.65. Заставка: 12.00 с. Существующее видео и звук не обрезаны.

2. **Новая обложка**
   - `episode01/CSCA_Math_01_Sets_Thumbnail_1280x720.png`
   - `episode01/CSCA_Math_01_Sets_Thumbnail_1280x720.jpg`
   - Проверочные уменьшенные копии: `thumbnail_preview_640x360.png`, `thumbnail_preview_320x180.png`.
   - Формат 1280 × 720, 16:9. Есть бренд Knowlumo, `CSCA MATH`, `EPISODE 01`, `PART 01`, тема `SETS MADE SIMPLE`.
   - Шаблон и переменные для следующих серий: `episode01/THUMBNAIL_TEMPLATE_EN.md`, `../build/build_thumbnail.py`.

3. **Вертикальный Shorts / Reels**
   - `shorts/CSCA_Math_01_Sets_Shorts_1080x1920.mp4`
   - 1080 × 1920, 9:16, 30 FPS, H.264, AAC 44.1 kHz stereo, 55.19 с.
   - Три вопроса: `A ∩ B`, `A ∪ B`, принадлежность `4` пересечению.
   - Паузы на обдумывание: 2.2 с, 2.2 с, 1.8 с. Ответы появляются только после каждой паузы.
   - Финальная карточка использует реальную новую обложку. Внутри MP4 нет выдуманного URL и нет утверждения, что карточка кликабельна.
   - Тайминги, слова, группы субтитров и проверки математики: `shorts/timeline.json`.

## Метаданные

- `episode01/VIDEO_01_EN.txt` — английские название, описание, таймкоды и примечания для длинного видео.
- `shorts/SHORTS_01_EN.txt` — английские название, описание и хэштеги для короткого видео.
- `index.html` — локальная страница-превью с видео и обложкой.

## Как собиралось

- Рендер графики и анимаций: Python + Pillow.
- Кодирование и сборка MP4: FFmpeg через `imageio-ffmpeg`.
- Английская озвучка: новый голос, выбранный на прослушивании в этой сессии (`voice-00`). **Это не утверждается как тот же голос, что был в предыдущем проекте.**
- Фон обложки: отдельная сгенерированная иллюстрация без текста; весь точный текст и логотип наложены кодом.
- Субтитры: слова привязаны к реально сгенерированным WAV-клипам через огибающую энергии и локальные «долины» между словами; длинные паузы исключены из распределения слов. Это **приблизительное энергетическое выравнивание, а не ASR forced alignment**. Перед публикацией желательно проверить короткие слова, паузы и концовки фраз визуально и на слух.
- Проекты OpenMontage, `darkzOGx/youtube-automation-agent`, Manim или 3Blue1Brown **не устанавливались и не использовались**.

## Что проверено автоматически

- Полное декодирование обоих финальных MP4 без ошибок.
- Наличие видео- и аудиодорожек, 30 FPS, заявленные разрешения и длительность.
- Длительность длинного видео больше 5 минут; заставка присутствует в конце; переход вокруг 330.65 с не обрывает звук.
- Математика: `A={1,2,3}`, `B={2,3,4}`, `A∩B={2,3}`, `A∪B={1,2,3,4}`, `4∉A∩B`.
- Субтитры: регрессионные проверки, что будущие слова не показываются раньше своей временной метки и последняя произнесённая группа удерживается на паузе.
- Обложка: 1280 × 720; дополнительно сохранены превью 640 × 360 и 320 × 180.
- Выбранные кадры длинного видео и Shorts просмотрены визуально.

## Важные ограничения и ручные проверки

- Канал на YouTube **не создан**, username `@Knowlumo` **не проверен**, видео **не опубликованы** на YouTube или Instagram.
- Нарисованная кнопка `SUBSCRIBE` — статичная графика, а не кликабельная функция YouTube. Настоящие конечные заставки настраиваются отдельно в YouTube Studio.
- Функция «Related Video» для Shorts не настроена. После публикации её доступность нужно проверить в YouTube Studio: официальная справка указывает, что она требует доступа к расширенным функциям и публичного/неопубликованного по ссылке связанного видео. Для Instagram Reels нужен реальный способ перехода, например актуальная ссылка в профиле.
- В карточке короткого ролика нет выдуманного адреса и нет обещания работающей ссылки внутри MP4.
- Баннер канала не переделывался; перед публикацией кадрирование нужно проверить в YouTube Studio на телефоне, компьютере и телевизоре.
- Официальный PDF `CSCA Mathematics Examination Syllabus (2025 Edition)` открывался по ссылке из предыдущего проекта; более новая официальная редакция не подтверждена. Сам PDF не копировался в репозиторий из-за указанного в нём ограничения на распространение. Канал независимый и не является официальным каналом CSCA. Требования экзамена и вузов могут меняться.
- Не придумывались даты публикаций, количество подписчиков, контактная почта, готовые курсы по другим предметам или официальная связь с CSCA.
- Никакие файлы не загружались на YouTube/Instagram и ничего не публиковалось без подтверждения владельца.
