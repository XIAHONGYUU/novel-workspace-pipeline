#!/usr/bin/env bash
# ============================================================
# 小说工作区批量重构脚本
# 用 DeepSeek 全自动重建 7 本测试小说的主角百科层
#
# 用法：
#   source .env && bash batch_rebuild_protagonist.sh
#
# 注意：
#   - 需要先设置 DEEPSEEK_API_KEY（在 .env 中）
#   - 每本小说耗时 1-6 小时，总计约 25 小时
#   - 建议在 tmux/screen 中运行
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
INIT_SCRIPT="$PROJECT_ROOT/novel-protagonist-encyclopedia-skill/scripts/init_workspace.py"
LOG_DIR="$PROJECT_ROOT/logs"

mkdir -p "$LOG_DIR"

# 7本小说的配置：名称、源文件、编码
NOVELS=(
  "巫师世界:巫师世界/source/WUSHISHIJIE.txt:gb18030"
  "序列大明:序列大明/source/XULIEDAMING.txt:utf-8"
  "刀笼:刀笼/source/DAOLONG.txt:utf-8"
  "我的诡异人生:我的诡异人生/source/WODEGUIYIRENSHENG.txt:utf-8"
  "永恒剑主:永恒剑主/source/YONGHENGJIANZHU.txt:utf-8"
  "玄浑道章:玄浑道章/source/XUANHUNDAOZHANG.txt:utf-8"
)

echo "========================================"
echo "小说工作区批量重构 - DeepSeek 主角百科层"
echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "共 ${#NOVELS[@]} 本小说"
echo "========================================"
echo ""

total=${#NOVELS[@]}
current=0

for entry in "${NOVELS[@]}"; do
  IFS=':' read -r name source enc <<< "$entry"
  current=$((current + 1))
  
  log_file="$LOG_DIR/${name}_$(date '+%Y%m%d_%H%M%S').log"
  
  echo "[$current/$total] 开始处理《$name》..."
  echo "  源文件: $source"
  echo "  编码: $enc"
  echo "  日志: $log_file"
  echo "  开始: $(date '+%H:%M:%S')"
  
  # 复制源文件到 /tmp 避免 SameFileError
  src_basename=$(basename "$source")
  tmp_src="/tmp/${src_basename}"
  cp "$PROJECT_ROOT/$source" "$tmp_src"
  
  # 运行 init
  if python3 "$INIT_SCRIPT" \
    --novel-name "$name" \
    --source "$tmp_src" \
    --project-root "$PROJECT_ROOT" \
    --extractor deepseek \
    --model deepseek-chat \
    --encoding "$enc" \
    >> "$log_file" 2>&1; then
    
    echo "  ✅ 完成: $(date '+%H:%M:%S')"
  else
    echo "  ❌ 失败（详见日志: $log_file）"
  fi
  
  # 清理临时文件
  rm -f "$tmp_src"
  
  # 刷新 workspace 状态
  python3 "$PROJECT_ROOT/novel-workspace-orchestrator-skill/scripts/refresh_workspace_status.py" \
    --workspace "$PROJECT_ROOT/$name" \
    --json > /dev/null 2>&1 || true
  
  echo ""
done

echo "========================================"
echo "全部完成！"
echo "结束时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "日志目录: $LOG_DIR"
echo "========================================"
