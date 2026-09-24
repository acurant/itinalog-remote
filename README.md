# АйТиНалоги Remote — своя сборка RustDesk

Набор для сборки RustDesk со стилем АйТиНалоги, вашим сервером по умолчанию и переключателем режима работы. Сборка идёт в GitHub Actions под Windows, macOS, Linux и Android.

## Что меняется в программе

| Что | Как |
|---|---|
| Сервер по умолчанию | `1c.itinalog.ru` (ID и relay), API `https://1c.itinalog.ru`, ключ из `InstallRustDesk.bat`. Всё задаётся в `itinalog/brand.json`. |
| Переключатель | Два режима: **«Сервер АйТиНалоги»** и **«Публичные серверы RustDesk»**. Он есть на главном экране под паролем, в *Настройки → Сеть* и в мобильных настройках. |
| Стиль сайта | Цвета взяты с itinalog.ru: красный `#E31E24` (кнопки, акценты, переключатели) и `#C4191F` (ID, наведение). Шрифт Golos Text, как на сайте, скачивается при сборке с Google Fonts. Кнопки скруглены, как на сайте. |
| Значки и логотип | Значок сайта ставится во все места: Windows (.ico), macOS (.icns), Linux, Android и Flutter. Логотип сайта выводится на главном экране. |
| Названия | «АйТиНалоги Remote»: подпись под значком на Android, пункт меню Linux, имя в macOS, заголовок окна (macOS и Linux), описание exe на Windows. |
| Обновления | Программа не предлагает обновиться до обычного RustDesk. |

Как работает переключатель: при первом запуске включается режим «Сервер АйТиНалоги». В этом режиме адреса сервера и ключ при каждом запуске возвращаются к значениям из `brand.json`. Если выбрать «Публичные серверы», поля ID/Relay/API/Key очищаются, и программа работает через бесплатные серверы RustDesk, как оригинал. Выбранный режим сохраняется. ID компьютера при переключении не меняется.

## Порядок сборки (GitHub Actions)

1. Создайте на GitHub **публичный** репозиторий, например `itinalog-remote`. Сборка macOS в приватном репозитории быстро расходует бесплатные минуты. Кроме того, RustDesk распространяется по лицензии AGPL-3.0, поэтому исходники изменённой версии всё равно нужно публиковать.
2. Загрузите туда содержимое этого архива: папку `itinalog/`, `.github/workflows/`, `README.md` и `.gitignore`.
3. Создайте токен: *GitHub → Settings → Developer settings → Fine-grained tokens*. Доступ только к этому репозиторию, права **Contents: Read and write** и **Workflows: Read and write**. Добавьте токен в репозиторий: *Settings → Secrets and variables → Actions → New secret* с именем `PUSH_TOKEN`.
4. Откройте *Actions → «ITINalog 1. Prepare» → Run workflow* (версия по умолчанию `1.4.9`). Этот шаг создаст ветку `build-1.4.9` и сам запустит сборку.
5. Сборка идёт около 1–2 часов. Готовые файлы появятся в *Releases* под тегом `itinalog-1.4.9`: `.exe`/`.msi` для Windows, `.dmg` для macOS, `.deb`/`.rpm`/AppImage для Linux и `.apk` для Android.

Сборку можно перезапустить вручную: *Actions → «ITINalog 2. Build»*, выбрав в «Use workflow from» ветку `build-…`.

### Подпись (желательно)

- **Android.** Без ключа APK не подписан и не установится. Создайте ключ командой `keytool -genkey -v -keystore itinalog.jks -alias itinalog -keyalg RSA -keysize 2048 -validity 10000`. Затем добавьте секреты `ANDROID_SIGNING_KEY` (содержимое `base64 -i itinalog.jks`), `ANDROID_ALIAS`, `ANDROID_KEY_STORE_PASSWORD` и `ANDROID_KEY_PASSWORD`.
- **macOS.** Без Apple Developer ID приложение не подписано. При первом запуске нужно открыть его через правый клик → «Открыть». Подпись настраивается секретами `MACOS_P12_BASE64`, `MACOS_P12_PASSWORD`, `MACOS_CODESIGN_IDENTITY` и `MACOS_NOTARIZE_JSON`.
- **Windows.** Без подписи SmartScreen покажет предупреждение. Это нормально для внутренних сборок.

## Сборка без GitHub Actions на своём компьютере

```bash
pip3 install pillow cairosvg fonttools
bash itinalog/prepare.sh 1.4.9                                    # исходники с брендом в _build/rustdesk
bash itinalog/prepare.sh 1.4.9 https://github.com/<вы>/itinalog-remote.git   # то же и сразу отправить ветку
```

Затем в *Actions* запустите «ITINalog 2. Build» на ветке `build-1.4.9`. Можно собрать и вручную по [инструкции RustDesk](https://rustdesk.com/docs/en/dev/build/).

## Настройка

Всё задаётся в `itinalog/brand.json`:

- `primary` и `primary_dark`: фирменные цвета, HEX или `"auto"` (взять из значка).
- `font_family`: шрифт с Google Fonts (пусто — оставить шрифт RustDesk). Свои файлы можно положить в `itinalog/assets/fonts/GolosText-400.ttf` и т.д.
- `button_radius`: скругление кнопок.
- `id_server`, `relay_server`, `api_server`, `key`: ваш сервер.
- `icon_url` и `logo_url`: откуда брать значок и логотип. Чтобы использовать свои файлы, положите `itinalog/assets/icon.png` (квадрат от 512×512) и `itinalog/assets/logo.png` (горизонтальный, с прозрачным фоном).
- `disable_jobs`: какие сборки пропускать.

Для перехода на новую версию RustDesk запустите Prepare с другим тегом, например `1.5.0`. Если RustDesk изменил код в местах, куда вносятся правки, `apply_branding.py` остановится и назовёт файл, который нужно поправить.

## Что осталось как в RustDesk (сознательно)

- Техническое имя приложения `RustDesk`: папка установки, имя службы, `RustDesk.app`, id пакета Android. Из-за этого сборку нельзя поставить рядом с обычным RustDesk, она его заменит. Полное переименование затрагивает установщики и службы всех платформ, поэтому это отдельная задача.
- Имена файлов в релизе: `rustdesk-1.4.9-x86_64.exe` и т.п.
- Заголовок главного окна на Windows: по нему программа находит уже запущенную копию.

## Установка на Windows с вашими настройками

Старый `InstallRustDesk.bat` больше не нужен для настройки сервера: сборка уже знает его. Но он по-прежнему скачивает обычный RustDesk 1.2.6. Если нужна тихая установка, замените в нём ссылку `curl` на `.exe` из ваших Releases, а строку `rustdesk.exe --config …` можно удалить. Пароль задаётся так же: `--password`.
