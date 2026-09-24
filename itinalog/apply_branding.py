#!/usr/bin/env python3
"""
Накладывает брендирование «АйТиНалоги Remote» на исходники RustDesk.

    python3 itinalog/apply_branding.py <путь к исходникам rustdesk>

Скрипт идемпотентный: повторный запуск на уже обработанном дереве ничего не ломает.
Каждый патч ищет «якорь» в исходниках; если якорь не найден (upstream изменился),
скрипт завершится с ошибкой и подскажет, какой файл поправить.

Зависимости: Python 3.8+, Pillow (pip install pillow). Для SVG-логотипа — cairosvg (необязательно).
"""
import io
import json
import os
import re
import shutil
import sys
import urllib.request

KIT = os.path.dirname(os.path.abspath(__file__))
MARK = "ITINALOG"  # маркер наших вставок, по нему проверяется идемпотентность


def die(msg):
    print(f"[itinalog] ОШИБКА: {msg}", file=sys.stderr)
    sys.exit(1)


def log(msg):
    print(f"[itinalog] {msg}")


# ---------------------------------------------------------------- helpers
def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def patch(root, rel, anchor, replacement, *, marker, regex=False, count=1, optional=False):
    """Заменяет anchor на replacement в файле, если marker ещё не присутствует."""
    path = os.path.join(root, rel)
    if not os.path.exists(path):
        if optional:
            log(f"  пропуск (нет файла): {rel}")
            return
        die(f"нет файла {rel}")
    text = read(path)
    if marker and marker in text:
        return
    if regex:
        new, n = re.subn(anchor, replacement, text, count=count)
    else:
        n = text.count(anchor)
        new = text.replace(anchor, replacement, count if count else -1)
    if n == 0:
        if optional:
            log(f"  пропуск (якорь не найден): {rel}")
            return
        die(f"не найден якорь в {rel}:\n---\n{anchor}\n---\nВерсия RustDesk изменилась — поправьте apply_branding.py")
    write(path, new)
    log(f"  patched {rel}")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (itinalog-build)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


# ---------------------------------------------------------------- images
def load_images(brand):
    try:
        from PIL import Image
    except ImportError:
        die("нужен Pillow: pip install pillow")

    def open_bytes(data, url_or_path):
        if url_or_path.lower().endswith(".svg") or data.lstrip()[:5] in (b"<?xml", b"<svg "):
            # логотип сайта — SVG-обёртка над встроенной картинкой: достаём её напрямую
            import base64
            m = re.search(rb"data:image/(?:png|jpe?g|webp);base64,([A-Za-z0-9+/=\s]+)", data)
            if m:
                return Image.open(io.BytesIO(base64.b64decode(m.group(1)))).convert("RGBA")
            try:
                import cairosvg
            except ImportError:
                raise RuntimeError("для SVG нужен cairosvg (pip install cairosvg)")
            data = cairosvg.svg2png(bytestring=data, output_height=240)
        return Image.open(io.BytesIO(data)).convert("RGBA")

    def get(local_name, urls):
        local = os.path.join(KIT, "assets", local_name)
        if os.path.exists(local):
            log(f"  {local_name}: локальный файл")
            return Image.open(local).convert("RGBA")
        for u in urls:
            if not u:
                continue
            try:
                img = open_bytes(fetch(u), u)
                log(f"  {local_name}: скачан {u}")
                os.makedirs(os.path.join(KIT, "assets"), exist_ok=True)
                img.save(os.path.join(KIT, "assets", "downloaded_" + local_name))
                return img
            except Exception as e:  # noqa
                log(f"  {local_name}: не удалось {u}: {e}")
        return None

    icon = get("icon.png", [brand.get("icon_url")])
    if icon is None:
        die("нет значка: положите itinalog/assets/icon.png или укажите icon_url")
    logo = get("logo.png", [brand.get("logo_url"), brand.get("logo_fallback_url")])
    return icon, logo


def square(img, size, pad=0.0, bg=None):
    from PIL import Image
    canvas = Image.new("RGBA", (size, size), bg or (0, 0, 0, 0))
    inner = int(size * (1 - 2 * pad))
    im = img.copy()
    im.thumbnail((inner, inner), Image.LANCZOS)
    canvas.alpha_composite(im, ((size - im.width) // 2, (size - im.height) // 2))
    return canvas


def trim(img):
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


def dominant_color(img):
    """Самый частый насыщенный цвет значка — фирменный цвет."""
    import colorsys
    small = img.copy()
    small.thumbnail((96, 96))
    buckets = {}
    raw = small.tobytes()
    for i in range(0, len(raw), 4):
        r, g, b, a = raw[i], raw[i + 1], raw[i + 2], raw[i + 3]
        if a < 200:
            continue
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if s < 0.35 or l < 0.15 or l > 0.85:
            continue
        key = (r // 16, g // 16, b // 16)
        acc = buckets.setdefault(key, [0, 0, 0, 0])
        acc[0] += r; acc[1] += g; acc[2] += b; acc[3] += 1
    if not buckets:
        return "C62828"
    r, g, b, n = max(buckets.values(), key=lambda v: v[3])
    return "%02X%02X%02X" % (r // n, g // n, b // n)


def darker(hexcolor, k=0.78):
    r, g, b = (int(hexcolor[i:i + 2], 16) for i in (0, 2, 4))
    return "%02X%02X%02X" % (int(r * k), int(g * k), int(b * k))


def write_icons(root, icon, logo):
    from PIL import Image
    ic = trim(icon)

    def save(rel, img, **kw):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        img.save(path, **kw)

    # res/
    save("res/icon.png", square(ic, 1024))
    save("res/mac-icon.png", square(ic, 1024, pad=0.1))
    for s, name in ((32, "32x32.png"), (64, "64x64.png"), (128, "128x128.png"), (256, "128x128@2x.png")):
        save(f"res/{name}", square(ic, s))
    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    save("res/icon.ico", square(ic, 256), sizes=ico_sizes)
    save("res/tray-icon.ico", square(ic, 256), sizes=ico_sizes[:5])
    save("flutter/windows/runner/resources/app_icon.ico", square(ic, 256), sizes=ico_sizes)
    # Linux scalable.svg и flutter/assets/icon.svg — SVG с встроенным PNG
    import base64
    buf = io.BytesIO(); square(ic, 512).save(buf, "PNG")
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
           'width="512" height="512" viewBox="0 0 512 512"><image width="512" height="512" '
           f'xlink:href="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"/></svg>')
    write(os.path.join(root, "res/scalable.svg"), svg)
    write(os.path.join(root, "flutter/assets/icon.svg"), svg)
    # macOS
    try:
        save("flutter/macos/Runner/AppIcon.icns", square(ic, 1024, pad=0.1))
    except Exception as e:  # noqa
        log(f"  предупреждение: не удалось записать AppIcon.icns: {e}")
    # Flutter assets
    save("flutter/assets/icon.png", square(ic, 256))
    if logo is not None:
        lg = trim(logo)
        lg.thumbnail((600, 120), Image.LANCZOS)  # отображается в рамке 300x60
        save("flutter/assets/logo.png", lg)
    # Android
    dens = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}
    for d, k in dens.items():
        base = f"flutter/android/app/src/main/res/mipmap-{d}"
        if not os.path.isdir(os.path.join(root, base)):
            continue
        white = (255, 255, 255, 255)
        save(f"{base}/ic_launcher.png", square(ic, int(48 * k), pad=0.08, bg=white))
        save(f"{base}/ic_launcher_round.png", square(ic, int(48 * k), pad=0.14, bg=white))
        # adaptive foreground: 108dp, безопасная зона 66dp
        save(f"{base}/ic_launcher_foreground.png", square(ic, int(108 * k), pad=0.22))
    log("  иконки записаны")


# ---------------------------------------------------------------- font
def install_font(root, family):
    """Скачивает шрифт с Google Fonts (TTF) и делает его основным шрифтом приложения."""
    key = family.replace(" ", "")
    fonts_dir = os.path.join(root, "flutter/assets/fonts")
    local_dir = os.path.join(KIT, "assets", "fonts")
    files = {}
    # свои файлы: itinalog/assets/fonts/<Family>-<вес>.ttf
    if os.path.isdir(local_dir):
        for fn in os.listdir(local_dir):
            m = re.match(rf"{key}-(\d+)\.ttf$", fn)
            if m:
                files[int(m.group(1))] = open(os.path.join(local_dir, fn), "rb").read()
    if not files:
        try:
            url = "https://fonts.googleapis.com/css2?family=" + family.replace(" ", "+") + ":wght@400;500;600;700"
            css = fetch_plain(url).decode()
            for w, u in re.findall(r"font-weight:\s*(\d+);.*?src:\s*url\((https://[^)]+\.ttf)\)", css, flags=re.S):
                files[int(w)] = fetch(u)
        except Exception as e:  # noqa
            log(f"  шрифт {family}: Google Fonts недоступен ({e}), пробую GitHub")
    if not files:
        # запасной путь: вариативный шрифт из репозитория google/fonts → статические веса (fontTools)
        try:
            folder = family.replace(" ", "").lower()
            var = fetch(f"https://github.com/google/fonts/raw/main/ofl/{folder}/{key}%5Bwght%5D.ttf")
            from fontTools.ttLib import TTFont
            from fontTools.varLib.instancer import instantiateVariableFont
            for w in (400, 500, 600, 700):
                inst = instantiateVariableFont(TTFont(io.BytesIO(var)), {"wght": w})
                buf = io.BytesIO(); inst.save(buf); files[w] = buf.getvalue()
        except Exception as e:  # noqa
            log(f"  шрифт {family}: не удалось получить ({e}) — остаётся шрифт RustDesk")
            return
    if not files:
        log(f"  шрифт {family}: файлы не найдены — остаётся шрифт RustDesk")
        return
    os.makedirs(fonts_dir, exist_ok=True)
    entries = ""
    for w in sorted(files):
        with open(os.path.join(fonts_dir, f"{key}-{w}.ttf"), "wb") as f:
            f.write(files[w])
        entries += f"        - asset: assets/fonts/{key}-{w}.ttf\n          weight: {w}\n"
    patch(root, "flutter/pubspec.yaml", "\n  fonts:\n",
          f"\n  fonts:\n    - family: {key} # ITINALOG\n      fonts:\n{entries}",
          marker=f"family: {key} # ITINALOG")
    patch(root, "flutter/lib/common.dart", r"(static ThemeData (?:light|dark)Theme = ThemeData\(\n)",
          rf"\1    fontFamily: '{key}', // ITINALOG\n",
          marker=f"fontFamily: '{key}', // ITINALOG", regex=True, count=0)
    log(f"  шрифт {family}: веса {sorted(files)}")


def fetch_plain(url):
    # без браузерного User-Agent Google Fonts отдаёт полные TTF (с кириллицей)
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


# ---------------------------------------------------------------- main
def main():
    if len(sys.argv) != 2:
        die("использование: apply_branding.py <путь к исходникам rustdesk>")
    root = os.path.abspath(sys.argv[1])
    if not os.path.exists(os.path.join(root, "src/common.rs")):
        die(f"{root} не похоже на исходники RustDesk")
    brand = json.loads(read(os.path.join(KIT, "brand.json")))

    log("1/6 изображения")
    icon, logo = load_images(brand)
    primary = brand["primary"]
    if primary == "auto":
        primary = dominant_color(icon)
        log(f"  фирменный цвет из значка: #{primary}")
    primary = primary.lstrip("#").upper()
    primary_dark = brand.get("primary_dark", "auto")
    primary_dark = darker(primary) if primary_dark == "auto" else primary_dark.lstrip("#").upper()
    write_icons(root, icon, logo)

    subs = {
        "@@DISPLAY_NAME@@": brand["display_name"],
        "@@COMPANY@@": brand["company"],
        "@@SITE@@": brand["site"],
        "@@PHONE@@": brand["phone"],
        "@@PRIMARY@@": primary,
        "@@PRIMARY_DARK@@": primary_dark,
        "@@ID_SERVER@@": brand["id_server"],
        "@@RELAY_SERVER@@": brand["relay_server"],
        "@@API_SERVER@@": brand["api_server"],
        "@@KEY@@": brand["key"],
    }

    log("2/6 новые файлы (overlay)")
    overlay = os.path.join(KIT, "overlay")
    for dp, _, files in os.walk(overlay):
        for fn in files:
            src = os.path.join(dp, fn)
            rel = os.path.relpath(src, overlay)
            text = read(src)
            for k, v in subs.items():
                text = text.replace(k, v)
            write(os.path.join(root, rel), text)
            log(f"  + {rel}")

    log("3/6 Rust")
    patch(root, "src/lib.rs", "pub mod common;\n",
          "pub mod common;\n// ITINALOG\npub mod itinalog;\n", marker="pub mod itinalog;")
    patch(root, "src/common.rs", "pub fn load_custom_client() {\n",
          "pub fn load_custom_client() {\n    // ITINALOG: сервер по умолчанию / переключатель режима\n"
          "    crate::itinalog::init();\n", marker="crate::itinalog::init();")
    if brand.get("disable_update_check", True):
        # иначе программа предложит «обновиться» до оригинального RustDesk
        patch(root, "src/common.rs", "pub fn check_software_update() {\n",
              "pub fn check_software_update() {\n    // ITINALOG: не предлагать обновление до оригинального RustDesk\n"
              "    if crate::itinalog::DISABLE_UPDATE_CHECK {\n        return;\n    }\n",
              marker="itinalog::DISABLE_UPDATE_CHECK {")
        rs = os.path.join(root, "src/itinalog.rs")
        t = read(rs)
        if "DISABLE_UPDATE_CHECK" not in t:
            write(rs, t + "\n/// Не проверять обновления оригинального RustDesk.\npub const DISABLE_UPDATE_CHECK: bool = true;\n")

    log("4/6 Flutter: цвета, переключатель, заголовки")
    lib = os.path.join(root, "flutter/lib")
    # фирменные цвета вместо синего RustDesk
    color_map = {"0071FF": primary, "2C8CFF": primary, "00B6F0": primary_dark}
    for dp, _, files in os.walk(lib):
        if "/itinalog" in dp.replace(os.sep, "/"):
            continue
        for fn in files:
            if not fn.endswith(".dart"):
                continue
            p = os.path.join(dp, fn)
            t = read(p)
            n = t
            for old, new in color_map.items():
                n = re.sub(r"(0x[0-9A-Fa-f]{2})" + old, lambda m, new=new: m.group(1) + new, n, flags=re.I)
            if n != t:
                write(p, n)
                log(f"  цвета: {os.path.relpath(p, root)}")
    patch(root, "flutter/lib/common.dart", "primary: Colors.blue,",
          f"primary: const Color(0xFF{primary}) /* ITINALOG */,",
          marker=f"primary: const Color(0xFF{primary}) /* ITINALOG */", count=0)

    imp = "import 'package:flutter_hbb/itinalog/server_mode.dart'; // ITINALOG\n"
    imp_brand = "import 'package:flutter_hbb/itinalog/brand.dart'; // ITINALOG\n"

    def add_import(rel, line):
        patch(root, rel, "import 'package:flutter/material.dart';\n",
              "import 'package:flutter/material.dart';\n" + line, marker=line.strip())

    # настройки desktop → вкладка «Сеть»
    add_import("flutter/lib/desktop/pages/desktop_setting_page.dart", imp)
    patch(root, "flutter/lib/desktop/pages/desktop_setting_page.dart",
          "        child: Column(children: [\n          network(context),\n",
          "        child: Column(children: [\n          ItinalogServerModeCard(enabled: !locked), // ITINALOG\n          network(context),\n",
          marker="ItinalogServerModeCard(")
    # главный экран desktop → под паролем
    add_import("flutter/lib/desktop/pages/desktop_home_page.dart", imp)
    patch(root, "flutter/lib/desktop/pages/desktop_home_page.dart",
          "      if (!isOutgoingOnly) buildPasswordBoard(context),\n",
          "      if (!isOutgoingOnly) buildPasswordBoard(context),\n"
          "      const ItinalogServerModeSwitch(compact: true) // ITINALOG\n"
          "          .marginOnly(left: 12, right: 8, top: 8),\n",
          marker="ItinalogServerModeSwitch(compact: true)")
    # мобильные настройки
    add_import("flutter/lib/mobile/pages/settings_page.dart", imp)
    patch(root, "flutter/lib/mobile/pages/settings_page.dart",
          "          if (!disabledSettings && !_hideNetwork && !_hideServer)\n            SettingsTile(\n                title: Text(translate('ID/Relay Server')),",
          "          if (!disabledSettings && !_hideNetwork && !_hideServer)\n"
          "            CustomSettingsTile( // ITINALOG\n"
          "                child: const ItinalogServerModeSwitch()\n"
          "                    .paddingSymmetric(horizontal: 16, vertical: 8)),\n"
          "          if (!disabledSettings && !_hideNetwork && !_hideServer)\n            SettingsTile(\n                title: Text(translate('ID/Relay Server')),",
          marker="CustomSettingsTile( // ITINALOG")
    # заголовок окна (на Windows не трогаем: по заголовку ищется уже запущенный экземпляр)
    add_import("flutter/lib/common.dart", imp_brand)
    patch(root, "flutter/lib/common.dart",
          "String getWindowName({WindowType? overrideType}) {\n  final name = bind.mainGetAppNameSync();",
          "String getWindowName({WindowType? overrideType}) {\n"
          "  final name = (isMacOS || isLinux) ? kBrandName /* ITINALOG */ : bind.mainGetAppNameSync();",
          marker="kBrandName /* ITINALOG */")
    add_import("flutter/lib/main.dart", imp_brand)
    patch(root, "flutter/lib/main.dart",
          "              : bind.mainGetAppNameSync(),",
          "              : kBrandName /* ITINALOG */,", marker="kBrandName /* ITINALOG */")

    font = (brand.get("font_family") or "").strip()
    if font:
        install_font(root, font)
    radius = brand.get("button_radius")
    if radius:
        path = os.path.join(root, "flutter/lib/common.dart")
        t = read(path)
        if "/* ITINALOG radius */" not in t:
            t2, n = re.subn(
                r"(ButtonThemeData\(\s*style: (?:Elevated|Outlined)Button\.styleFrom\(.*?BorderRadius\.circular\()8\.0\)",
                lambda m: m.group(1) + f"{float(radius)}) /* ITINALOG radius */", t, flags=re.S)
            if n:
                write(path, t2)
                log(f"  скругление кнопок {radius}px ({n} тем)")
            else:
                log("  скругление кнопок: якорь не найден — пропуск")

    log("5/6 названия в пакетах")
    dn, dna = brand["display_name"], brand["display_name_ascii"]
    patch(root, "flutter/android/app/src/main/AndroidManifest.xml",
          'android:label="RustDesk"', f'android:label="{dn}"', marker=f'android:label="{dn}"')
    patch(root, "flutter/windows/runner/Runner.rc",
          'VALUE "FileDescription", "RustDesk Remote Desktop"',
          f'VALUE "FileDescription", "{dna}"', marker=f'"FileDescription", "{dna}"')
    patch(root, "res/rustdesk.desktop", "\nName=RustDesk\n", f"\nName={dn}\n", marker=f"Name={dn}", optional=True)
    patch(root, "res/rustdesk.desktop", "[Desktop Entry]\nName=RustDesk\n", f"[Desktop Entry]\nName={dn}\n",
          marker=f"Name={dn}", optional=True)
    plist = "flutter/macos/Runner/Info.plist"
    patch(root, plist, "<dict>\n", f"<dict>\n\t<key>CFBundleDisplayName</key>\n\t<string>{dn}</string>\n",
          marker="CFBundleDisplayName", optional=True)

    log("6/6 GitHub Actions")
    wf = os.path.join(root, ".github/workflows")
    keep = {"flutter-build.yml", "bridge.yml", "third-party-RustDeskTempTopMostWindow.yml",
            "itinalog-build.yml", "itinalog-prepare.yml"}
    if os.path.isdir(wf):
        for fn in os.listdir(wf):
            if fn.endswith((".yml", ".yaml")) and fn not in keep:
                os.remove(os.path.join(wf, fn))
                log(f"  удалён {fn} (не нужен в сборочной ветке)")
        fb = os.path.join(wf, "flutter-build.yml")
        t = read(fb)
        lines = t.split("\n")
        for job in brand.get("disable_jobs", []):
            try:
                i = lines.index(f"  {job}:")
            except ValueError:
                log(f"  job {job} не найден — пропуск")
                continue
            if "# ITINALOG" in lines[i + 1]:
                continue
            # убрать собственный if: job'а (он всегда в первых строках заголовка)
            for j in range(i + 1, min(i + 8, len(lines))):
                if lines[j].startswith("    if:"):
                    del lines[j]
                    break
                if lines[j].startswith("    steps:") or lines[j].startswith("  ") and not lines[j].startswith("   "):
                    break
            lines.insert(i + 1, "    if: ${{ false }} # ITINALOG")
            log(f"  отключён job {job}")
        t = "\n".join(lines)
        write(fb, t)
    log(f"Готово. Цвет #{primary} / #{primary_dark}")


if __name__ == "__main__":
    main()
