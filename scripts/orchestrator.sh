#!/bin/bash
#
# Kimi Print 接力开发 Orchestrator
# 每个任务：生成 prompt → 切分支 → kimi print 执行 → 三层验证 → commit → merge
#
# 用法:
#   bash scripts/orchestrator.sh [task_id]   # 执行单个任务
#   bash scripts/orchestrator.sh --all       # 执行所有 pending 任务（谨慎使用）
#   bash scripts/orchestrator.sh --dry-run   # 只打印要执行的任务，不执行
#

set -euo pipefail

PROJECT_DIR="/Users/malin13/Documents/trae_projects/website_aicut"
FEATURE_BRANCH="feature/smart-cut-taskcard-refactor"
TASK_JSON="$PROJECT_DIR/new_book_rel-0418/20_real_data_chain_2026-04-19/70_smart_cut_task_card_refactor_2026-04-23/task.json"
BUILDER="python3 $PROJECT_DIR/scripts/task_prompt_builder.py"

cd "$PROJECT_DIR"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    echo "Usage: $0 [task_id | --all | --dry-run | --list]"
    echo ""
    echo "  task_id     执行指定任务（如 S801）"
    echo "  --all       执行所有 pending 任务（谨慎！）"
    echo "  --dry-run   只列出将要执行的任务"
    echo "  --list      列出所有 pending 任务"
    echo ""
    echo "示例:"
    echo "  $0 S801"
    echo "  $0 --list"
    echo "  $0 --dry-run"
    exit 1
}

# 解析参数
MODE="single"
TARGET_TASK=""
if [ $# -eq 0 ]; then
    usage
fi

if [ "$1" == "--all" ]; then
    MODE="all"
elif [ "$1" == "--dry-run" ]; then
    MODE="dry-run"
elif [ "$1" == "--list" ]; then
    MODE="list"
else
    TARGET_TASK="$1"
fi

# 列出任务
if [ "$MODE" == "list" ]; then
    echo "Pending tasks:"
    $BUILDER "$TASK_JSON" list-pending | while IFS=: read -r id title; do
        echo "  $id: $title"
    done
    exit 0
fi

# dry-run
if [ "$MODE" == "dry-run" ]; then
    echo "=== DRY RUN ==="
    echo "将要执行的任务:"
    $BUILDER "$TASK_JSON" list-pending | while IFS=: read -r id title; do
        echo "  - $id: $title"
    done
    echo ""
    echo "执行流程（每个任务）:"
    echo "  1. git checkout -b $FEATURE_BRANCH-<task_id>"
    echo "  2. 生成 task_prompts/<task_id>.md"
    echo "  3. kimi --print -p ... --work-dir . -y"
    echo "  4. 运行 validate（三层验证）"
    echo "  5. git commit -m '[<task_id>] <title>'"
    echo "  6. git merge --no-ff"
    echo "  7. 更新 task.json"
    exit 0
fi

# 确保在主分支
echo "Ensuring we are on $FEATURE_BRANCH..."
if ! git rev-parse --verify "$FEATURE_BRANCH" >/dev/null 2>&1; then
    echo -e "${RED}ERROR: Branch $FEATURE_BRANCH does not exist${NC}"
    exit 1
fi
git checkout "$FEATURE_BRANCH"

# 确定要执行的任务列表
if [ "$MODE" == "single" ]; then
    TASKS="$TARGET_TASK"
    # 验证任务存在且 pending
    if ! $BUILDER "$TASK_JSON" list-pending | grep -q "^$TARGET_TASK:"; then
        echo -e "${YELLOW}WARNING: $TARGET_TASK is not in pending list. Checking if already completed...${NC}"
        $BUILDER "$TASK_JSON" list-pending
        exit 1
    fi
else
    # --all 模式
    echo -e "${YELLOW}WARNING: --all will execute ALL pending tasks automatically.${NC}"
    echo "This is risky. Press Ctrl+C to cancel, or wait 3 seconds to continue..."
    sleep 3
    TASKS=$($BUILDER "$TASK_JSON" list-pending | cut -d':' -f1 | tr '\n' ' ')
fi

# 遍历执行任务
for task_id in $TASKS; do
    # 获取任务标题
    task_title=$($BUILDER "$TASK_JSON" list-pending | grep "^$task_id:" | cut -d':' -f2- || echo "")
    if [ -z "$task_title" ]; then
        echo -e "${YELLOW}Skipping $task_id (not found in pending list)${NC}"
        continue
    fi

    echo ""
    echo "========================================"
    echo -e "  Starting: ${GREEN}$task_id${NC} — $task_title"
    echo "========================================"

    # 1. 确保工作目录干净
    if ! git diff --quiet HEAD || ! git diff --cached --quiet; then
        echo -e "${YELLOW}WARNING: Working directory not clean. Stashing changes...${NC}"
        git stash push -m "orchestrator-stash-before-$task_id"
    fi

    # 2. 生成 prompt
    echo "[1/6] Generating prompt..."
    prompt_file="task_prompts/${task_id}.md"
    $BUILDER "$TASK_JSON" generate "$task_id" > "$prompt_file"
    echo "      → $prompt_file ($(wc -l < "$prompt_file") lines)"

    # 3. 创建任务分支
    echo "[2/6] Creating branch..."
    branch_name="${FEATURE_BRANCH}-${task_id}"
    git checkout -b "$branch_name" "$FEATURE_BRANCH"

    # 4. 运行 kimi print
    echo "[3/6] Running kimi --print (this may take a while)..."
    log_file="task_run_logs/${task_id}.log"

    set +e
    kimi --print \
        -p "$(cat "$prompt_file")" \
        --work-dir "$PROJECT_DIR" \
        -y \
        > "$log_file" 2>&1
    kimi_exit=$?
    set -e

    echo "      → kimi exit code: $kimi_exit"
    echo "      → log: $log_file"

    # 5. 运行验证（无论 kimi 是否成功都运行，以便了解当前状态）
    echo "[4/6] Running validation..."
    set +e
    $BUILDER "$TASK_JSON" validate "$task_id" > "task_run_logs/${task_id}.validate.log" 2>&1
    validate_exit=$?
    set -e

    if [ $validate_exit -eq 0 ]; then
        echo -e "      → ${GREEN}Validation PASSED${NC}"
    else
        echo -e "      → ${RED}Validation FAILED (see task_run_logs/${task_id}.validate.log)${NC}"
    fi

    # 6. 检查 git 状态，决定如何处理
    echo "[5/6] Checking git status..."
    modified_files=$(git diff --name-only HEAD | wc -l | tr -d ' ')
    staged_files=$(git diff --cached --name-only | wc -l | tr -d ' ')

    echo "      → Modified files: $modified_files"
    echo "      → Staged files: $staged_files"

    if [ $staged_files -gt 0 ]; then
        # 子代理已经 commit 了
        echo "      → Sub-agent already committed."
    elif [ $modified_files -gt 0 ]; then
        # 有修改但没 commit，询问是否 commit
        echo -e "      → ${YELLOW}Modified but not committed.${NC}"
        echo "        Modified files:"
        git diff --name-only HEAD | sed 's/^/          /'

        if [ "$MODE" == "all" ]; then
            # 全自动模式：自动 commit
            echo "        Auto-committing (all mode)..."
            git add -A
            git commit -m "[$task_id] $task_title" || true
        else
            # 半自动模式：询问用户
            read -p "        Commit these changes? [y/N] " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                git add -A
                git commit -m "[$task_id] $task_title"
            else
                echo "        Skipping commit. Changes remain in branch $branch_name"
            fi
        fi
    else
        echo "      → No code changes detected."
    fi

    # 7. 如果验证通过且已有 commit，merge 回主分支
    echo "[6/6] Merging back to $FEATURE_BRANCH..."
    if [ $validate_exit -eq 0 ] && git rev-parse HEAD >/dev/null 2>&1; then
        git checkout "$FEATURE_BRANCH"
        if git merge --no-ff "$branch_name" -m "Merge $task_id: $task_title" 2>/dev/null; then
            echo -e "      → ${GREEN}Merge successful${NC}"
            # 更新 task.json
            $BUILDER "$TASK_JSON" mark-done "$task_id"
            echo "      → Task marked as completed"
        else
            echo -e "      → ${RED}Merge conflict! Please resolve manually.${NC}"
            echo "        Branch: $branch_name"
            exit 1
        fi
    else
        if [ $validate_exit -ne 0 ]; then
            echo -e "      → ${YELLOW}Validation failed, keeping branch for manual fix.${NC}"
        else
            echo -e "      → ${YELLOW}No commit found, not merging.${NC}"
        fi
        # 切回主分支但不删除工作分支
        git checkout "$FEATURE_BRANCH"
    fi

    echo "========================================"
    echo -e "  ${GREEN}Task $task_id finished${NC}"
    echo "  Log: $log_file"
    echo "  Validate log: task_run_logs/${task_id}.validate.log"
    echo "========================================"
done

echo ""
echo "========================================"
echo -e "  ${GREEN}All tasks completed!${NC}"
echo "========================================"

# 显示最终状态
echo ""
echo "Remaining pending tasks:"
$BUILDER "$TASK_JSON" list-pending || echo "  None"
