#!/usr/bin/env bash
# Готовит брендированные исходники АйТиНалоги Remote.
#
#   bash itinalog/prepare.sh [версия RustDesk] [git-URL вашего репозитория]
#
# 1) скачивает RustDesk нужной версии (по умолчанию 1.4.9);
# 2) накладывает брендирование (apply_branding.py);
# 3) делает один коммит в ветке build-<версия>;
# 4) если указан URL репозитория — отправляет туда эту ветку (git push -f).
set -euo pipefail

UPSTREAM_REF="${1:-1.4.9}"
PUSH_URL="${2:-}"
KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-$KIT_ROOT/_build/rustdesk}"
BRANCH="build-${UPSTREAM_REF}"

echo "== RustDesk ${UPSTREAM_REF} -> ${WORK}"
rm -rf "$WORK"
git clone --depth 1 --branch "$UPSTREAM_REF" --recurse-submodules --shallow-submodules \
  https://github.com/rustdesk/rustdesk.git "$WORK"

# Встраиваем hbb_common как обычную папку (без submodule) и начинаем чистую историю:
# так ветку можно отправить в любой репозиторий.
rm -rf "$WORK/.git" "$WORK/libs/hbb_common/.git" "$WORK/.gitmodules"

echo "== Брендирование"
rm -rf "$WORK/itinalog"
cp -R "$KIT_ROOT/itinalog" "$WORK/itinalog"
rm -rf "$WORK/itinalog/_build"
mkdir -p "$WORK/.github/workflows"
cp "$KIT_ROOT/.github/workflows/itinalog-build.yml" "$WORK/.github/workflows/"
python3 "$WORK/itinalog/apply_branding.py" "$WORK"

echo "== Коммит в ветку ${BRANCH}"
cd "$WORK"
git init -q -b "$BRANCH"
git add -A
git -c user.name="${GIT_AUTHOR_NAME:-itinalog-build}" \
    -c user.email="${GIT_AUTHOR_EMAIL:-build@itinalog.ru}" \
    commit -q -m "АйТиНалоги Remote на базе RustDesk ${UPSTREAM_REF}"

if [ -n "$PUSH_URL" ]; then
  echo "== git push -> ${BRANCH}"
  git push -f "$PUSH_URL" "HEAD:refs/heads/${BRANCH}"
fi
echo "Готово: ${WORK} (ветка ${BRANCH})"
