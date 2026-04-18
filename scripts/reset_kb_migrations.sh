#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env.dev"

# ── 读取数据库连接信息 ────────────────────────────────────────────────
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found" >&2
  exit 1
fi

_get_env() {
  grep -E "^${1}=" "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '\r'
}

DB_HOST="$(_get_env NEKRO_POSTGRES_HOST)"
DB_PORT="$(_get_env NEKRO_POSTGRES_PORT)"
DB_USER="$(_get_env NEKRO_POSTGRES_USER)"
DB_PASS="$(_get_env NEKRO_POSTGRES_PASSWORD)"
DB_NAME="$(_get_env NEKRO_POSTGRES_DATABASE)"

if [[ -z "$DB_HOST" || -z "$DB_PORT" || -z "$DB_USER" || -z "$DB_NAME" ]]; then
  echo "ERROR: 数据库连接信息不完整，请检查 $ENV_FILE" >&2
  exit 1
fi

export PGPASSWORD="$DB_PASS"
PSQL="psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"

echo "==> 连接目标: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
echo ""

# ── 确认 ─────────────────────────────────────────────────────────────
echo "此操作将："
echo "  1. 删除所有知识库相关表"
echo "  2. 清理 aerich 中所有 KB 迁移记录（8_kb、9_kb、10_ 等）"
echo "  3. 删除对应迁移文件，保留非 KB 的 8_ 和 9_ 文件"
echo ""
read -rp "确认继续？[y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "已取消。"
  exit 0
fi

# ── 删除知识库业务表 ──────────────────────────────────────────────────
echo ""
echo "==> 删除知识库业务表..."
$PSQL <<'SQL'
DROP TABLE IF EXISTS kb_asset_reference CASCADE;
DROP TABLE IF EXISTS kb_document_reference CASCADE;
DROP TABLE IF EXISTS kb_asset_chunk CASCADE;
DROP TABLE IF EXISTS kb_asset_binding CASCADE;
DROP TABLE IF EXISTS kb_asset CASCADE;
DROP TABLE IF EXISTS kb_chunk CASCADE;
DROP TABLE IF EXISTS kb_document CASCADE;
SQL
echo "    完成"

# ── 清理 aerich 版本记录 ──────────────────────────────────────────────
echo ""
echo "==> 清理 aerich 迁移版本记录..."
$PSQL <<'SQL'
DELETE FROM aerich
WHERE app = 'models'
  AND (
    version LIKE '%kb%'
    OR version LIKE '10\_%' ESCAPE '\'
  );
SQL
echo "    当前 aerich 版本表："
$PSQL -c "SELECT id, version FROM aerich WHERE app = 'models' ORDER BY id;"

# ── 删除 KB 迁移文件 ──────────────────────────────────────────────────
echo ""
echo "==> 删除 KB 迁移文件..."
KB_FILES=(
  "8_20260409124603_kb_rebuildable_search_index.py"
  "9_20260410125635_add_kb_library.py"
)
for name in "${KB_FILES[@]}"; do
  f="$PROJECT_ROOT/migrations/models/$name"
  if [[ -f "$f" ]]; then
    rm "$f"
    echo "    已删除: $name"
  fi
done
# 删除所有 10_ 及以上的文件
for f in "$PROJECT_ROOT"/migrations/models/10_*.py \
         "$PROJECT_ROOT"/migrations/models/11_*.py; do
  if [[ -f "$f" ]]; then
    rm "$f"
    echo "    已删除: $(basename "$f")"
  fi
done

# ── 提示下一步 ────────────────────────────────────────────────────────
echo ""
echo "==> 清理完成。执行以下命令重建："
echo "      poe db-revision add_kb_tables   # 生成统一 KB 迁移文件"
echo "      poe db-migrate                  # 应用到数据库"
