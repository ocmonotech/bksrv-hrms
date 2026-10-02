#!/usr/bin/env bash
# Creates a clean backend zip for remote server upload (no venv, cache, or dev uploads).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"
NAME="ocmono-hrms-backend"
STAGING="$DIST/$NAME"
ZIP="$DIST/$NAME.zip"

rm -rf "$STAGING" "$ZIP"
mkdir -p "$STAGING/storage/uploads"
mkdir -p "$DIST"

copy_tree() {
  local src="$1"
  local dest="$2"
  if [[ -d "$src" ]]; then
    mkdir -p "$dest"
    rsync -a \
      --exclude='__pycache__' \
      --exclude='*.pyc' \
      --exclude='.pytest_cache' \
      "$src/" "$dest/"
  fi
}

copy_tree "$ROOT/app" "$STAGING/app"
copy_tree "$ROOT/alembic" "$STAGING/alembic"
copy_tree "$ROOT/scripts" "$STAGING/scripts"

cp "$ROOT/main.py" "$STAGING/"
cp "$ROOT/requirements.txt" "$STAGING/"
cp "$ROOT/alembic.ini" "$STAGING/"
cp "$ROOT/.env.example" "$STAGING/"
cp "$ROOT/README.md" "$STAGING/"
cp "$ROOT/DEPLOY.md" "$STAGING/"

# Empty upload dir placeholder
touch "$STAGING/storage/uploads/.gitkeep"

cd "$DIST"
zip -r "$NAME.zip" "$NAME" -x "*.DS_Store"
rm -rf "$STAGING"

echo "Created: $ZIP"
echo "Upload this zip to your server and follow DEPLOY.md"
