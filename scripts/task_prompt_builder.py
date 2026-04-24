#!/usr/bin/env python3
"""
从 task.json + 09_ 文档生成子代理 prompt。
每个 prompt 包含：任务描述 + 实现步骤 + 三层验证（代码审查→测试→E2E）。

用法:
  python3 task_prompt_builder.py --list-pending task.json
  python3 task_prompt_builder.py --generate task.json S801
  python3 task_prompt_builder.py --mark-done task.json S801
  python3 task_prompt_builder.py --validate task.json S801   # 运行 E2E 验证
"""
import json
import sys
import argparse
import re
import subprocess
from pathlib import Path


# ============ 任务到文档 section 的映射 ============
_TASK_SECTION_MAP = {
    "S801": "B4-1", "S802": "B4-2", "S803": "B4-3",
    "S203": "B1-1", "S205": "B1-2",
    "S601": "B2-1", "S602": "B2-2", "S603": "B2-3", "S604": "B2-4",
    "S701": "B3-1", "S702": "B3-2", "S703": "B3-3",
    "S704": "B3-4", "S705": "B3-5", "S706": "B3-6",
}

# ============ 每个任务的 E2E 验证定义 ============
# 验证分三层：L1 代码审查、L2 测试运行、L3 端到端验证
_TASK_VALIDATION = {
    "S801": {
        "l1_files_must_modify": ["apps/api/routes/tasks.py"],
        "l1_files_must_not_modify": ["apps/web/", "apps/models/"],
        "l2_pytest_args": ["tests/test_rel0415_api.py", "-k", "draft", "-v"],
        "l3_commands": [
            # 启动 API（如果未运行）
            # "cd /Users/malin13/Documents/trae_projects/website_aicut && nohup python3 -m uvicorn apps.api.main:app --port 18002 &",
            # 验证接口返回 410
            "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18002/api/smart-cut/tasks/draft/current || echo 'API not running - manual verification required'",
            "curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:18002/api/smart-cut/tasks/draft/current/ensure || echo 'API not running - manual verification required'",
        ],
        "l3_expected": ["410", "410"],
    },
    "S802": {
        "l1_files_must_modify": ["apps/models/task.py", "apps/api/routes/task_center.py"],
        "l1_files_must_not_modify": ["apps/web/"],
        "l2_pytest_args": ["tests/test_rel0415_api.py", "-v"],
        "l3_commands": [
            # 验证任务列表查询不依赖 visible_in_task_center
            "python3 -c \"import sys; sys.path.insert(0, '.'); from apps.api.routes.task_center import *; print('Import OK')\" || echo 'Import check'",
        ],
        "l3_expected": ["Import OK"],
    },
    "S803": {
        "l1_files_must_modify": [],
        "l1_files_must_not_modify": ["apps/api/", "apps/models/", "apps/web/components/", "apps/web/app/"],
        "l2_pytest_args": [],
        "l3_commands": [
            "test -d apps/web/quarantine && echo 'quarantine exists' || echo 'quarantine already removed'",
        ],
        "l3_expected": [],
    },
    "S203": {
        "l1_files_must_modify": ["apps/api/routes/stages.py", "apps/models/task_run.py"],
        "l1_files_must_not_modify": [],
        "l2_pytest_args": ["tests/test_task_card_schema.py", "-v"],
        "l3_commands": [
            # 需要有一个带 preview 的任务来验证 source_edit_id
            "echo 'Manual E2E required: create a task with preview loop and verify source_edit_id in task_runs'",
        ],
        "l3_expected": [],
    },
    "S205": {
        "l1_files_must_modify": [],  # 可能新建文件
        "l1_files_must_not_modify": [],
        "l2_pytest_args": [],
        "l3_commands": [
            "echo 'Manual E2E required: create abandoned task, set abandoned_at to 7 days ago, run cleanup, verify runs/edits deleted'",
        ],
        "l3_expected": [],
    },
    "S601": {
        "l1_files_must_modify": [],  # 新建脚本
        "l1_files_must_not_modify": ["apps/"],
        "l2_pytest_args": [],
        "l3_commands": [
            "echo 'Manual E2E required: run cleanup script in dry-run mode, verify counts before/after'",
        ],
        "l3_expected": [],
    },
    "S602": {
        "l1_files_must_modify": [],  # 新建脚本
        "l1_files_must_not_modify": ["apps/"],
        "l2_pytest_args": [],
        "l3_commands": [
            "bash -n deploy/release_smartcut_refactor.sh && echo 'Syntax OK' || echo 'Syntax error'",
            "bash -n deploy/rollback_smartcut_refactor.sh && echo 'Syntax OK' || echo 'Syntax error'",
        ],
        "l3_expected": ["Syntax OK", "Syntax OK"],
    },
    "S603": {
        "l1_files_must_modify": [],
        "l1_files_must_not_modify": ["apps/api/", "apps/models/"],
        "l2_pytest_args": [],
        "l3_commands": [
            "echo 'Checklist verification: verify all E2E items in checklist are marked complete'",
        ],
        "l3_expected": [],
    },
    "S604": {
        "l1_files_must_modify": [],
        "l1_files_must_not_modify": [],
        "l2_pytest_args": [],
        "l3_commands": [
            "echo 'Manual E2E required: simulate failure, run rollback, verify old model works, restore new model'",
        ],
        "l3_expected": [],
    },
    "S701": {
        "l1_files_must_modify": [],
        "l1_files_must_not_modify": [],
        "l2_pytest_args": ["tests/test_rel0415_api.py", "-v"],
        "l3_commands": [
            "echo 'Manual E2E required: login -> Smart Cut -> start task -> upload -> verify auto-analyze -> check script + audio_a -> verify task list'",
        ],
        "l3_expected": [],
    },
    "S702": {
        "l1_files_must_modify": [],
        "l1_files_must_not_modify": [],
        "l2_pytest_args": [],
        "l3_commands": [
            "echo 'Manual E2E required: after E2E-01, click finalize without preview -> verify final_video on TOS'",
        ],
        "l3_expected": [],
    },
    "S703": {
        "l1_files_must_modify": [],
        "l1_files_must_not_modify": [],
        "l2_pytest_args": [],
        "l3_commands": [
            "echo 'Manual E2E required: preview loop 2-3 times -> finalize -> verify video content matches last edit'",
        ],
        "l3_expected": [],
    },
    "S704": {
        "l1_files_must_modify": [],
        "l1_files_must_not_modify": [],
        "l2_pytest_args": [],
        "l3_commands": [
            "echo 'Manual E2E required: edit completed task -> verify same task_id, new edit version, old video still accessible'",
        ],
        "l3_expected": [],
    },
    "S705": {
        "l1_files_must_modify": [],
        "l1_files_must_not_modify": [],
        "l2_pytest_args": [],
        "l3_commands": [
            "echo 'Manual E2E required: start task -> abandon -> verify status=abandoned, abandoned_at set, no auto-recovery'",
        ],
        "l3_expected": [],
    },
    "S706": {
        "l1_files_must_modify": [],
        "l1_files_must_not_modify": [],
        "l2_pytest_args": [],
        "l3_commands": [
            "echo 'Manual E2E required: company A creates task -> company B sees it -> company C does not see it -> direct access returns 403'",
        ],
        "l3_expected": [],
    },
}


def load_task_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_09_doc(base_dir):
    doc_path = Path(base_dir) / "new_book_rel-0418/20_real_data_chain_2026-04-19/70_smart_cut_task_card_refactor_2026-04-23/09_方案B完整收官计划.md"
    if doc_path.exists():
        return doc_path.read_text(encoding="utf-8")
    return ""


def extract_task_detail(doc_text, small_task_id):
    section = _TASK_SECTION_MAP.get(small_task_id)
    if not section:
        return ""
    pattern = rf"### [^#\n]*{section}[^#\n]*\n\n(.*?)(?=\n### |\n## |\Z)"
    match = re.search(pattern, doc_text, re.DOTALL)
    if match:
        detail = match.group(1).strip()
        lines = detail.split('\n')
        return '\n'.join(lines[:50])
    return ""


def get_pending_tasks(data):
    pending = []
    for lt in data.get("large_tasks", []):
        for st in lt.get("small_tasks", []):
            if st["status"] == "pending":
                pending.append({
                    "large_id": lt["id"],
                    "id": st["id"],
                    "title": st["title"],
                    "large_title": lt["title"]
                })
    return pending


def get_task_info(data, small_task_id):
    for lt in data["large_tasks"]:
        for st in lt["small_tasks"]:
            if st["id"] == small_task_id:
                return {**st, "large_id": lt["id"], "large_title": lt["title"], "large_status": lt["status"]}
    return None


def _file_hint(small_task_id):
    hints = {
        "S801": ["apps/api/routes/tasks.py (draft/current 接口)"],
        "S802": [
            "apps/models/task.py (visible_in_task_center, session_scope_id)",
            "apps/api/routes/task_center.py",
            "apps/api/routes/tasks.py",
        ],
        "S803": ["apps/web/quarantine/ (旧前端代码)"],
        "S203": [
            "apps/api/routes/stages.py (preview/finalize 逻辑)",
            "apps/models/task_run.py (source_edit_id)",
            "apps/models/edit.py",
        ],
        "S205": [
            "apps/models/task.py (abandoned_at)",
            "apps/models/task_run.py",
            "apps/scheduler/ (清理任务集成点)",
        ],
        "S601": ["scripts/cleanup_old_smartcut_data.py (新建)"],
        "S602": [
            "deploy/release_smartcut_refactor.sh (新建)",
            "deploy/rollback_smartcut_refactor.sh (新建)",
        ],
        "S603": ["apps/web/components/navigation/user-workspace-shell.tsx (导航入口)"],
        "S604": ["deploy/rollback_smartcut_refactor.sh"],
    }
    return hints.get(small_task_id, ["根据任务描述自行查找相关文件"])


def _validation_block(task_id, work_dir):
    """生成验证章节的 markdown。"""
    val = _TASK_VALIDATION.get(task_id, {})

    lines = ["## 三层验证（必须全部通过才能 commit）\n"]

    # L1: 代码审查
    lines.append("### L1 代码审查验证")
    must_mod = val.get("l1_files_must_modify", [])
    must_not = val.get("l1_files_must_not_modify", [])
    if must_mod:
        lines.append("修改完成后，确认以下文件**确实被修改了**：")
        for f in must_mod:
            lines.append(f"- [ ] `git diff` 显示 `{f}` 有变更")
    if must_not:
        lines.append("确认以下文件**没有被意外修改**：")
        for f in must_not:
            lines.append(f"- [ ] `git diff --name-only` 不包含 `{f}`")
    lines.append("")

    # L2: 测试运行
    lines.append("### L2 测试运行验证")
    pytest_args = val.get("l2_pytest_args", [])
    if pytest_args:
        cmd = " ".join(pytest_args)
        lines.append(f"运行测试命令：")
        lines.append(f"```bash")
        lines.append(f"cd {work_dir}")
        lines.append(f"pytest {cmd}")
        lines.append(f"```")
        lines.append(f"- [ ] 所有测试通过（exit code 0）")
    else:
        lines.append("此任务无自动化测试，跳过 L2。")
    lines.append("")

    # L3: 端到端验证（最重要的）
    lines.append("### L3 端到端验证（⚠️ 最重要的验证层）")
    l3_cmds = val.get("l3_commands", [])
    l3_exp = val.get("l3_expected", [])

    if l3_cmds:
        lines.append("运行以下端到端验证命令：\n")
        for i, cmd in enumerate(l3_cmds):
            exp = l3_exp[i] if i < len(l3_exp) else ""
            lines.append(f"**命令 {i+1}：**")
            lines.append(f"```bash")
            lines.append(cmd)
            lines.append(f"```")
            if exp:
                lines.append(f"- [ ] 输出包含 `{exp}`")
            lines.append("")
    else:
        lines.append("此任务的 E2E 验证需要人工操作（涉及真实上传、Worker 处理等）。")
        lines.append("请在实现完成后，按照任务描述中的'验证标准'人工验证。")
    lines.append("")

    # 验证未通过的处置
    lines.append("### 验证未通过的处置")
    lines.append("如果任何一层验证失败：")
    lines.append("1. **不要 commit**")
    lines.append("2. 修复问题")
    lines.append("3. 重新运行失败的验证")
    lines.append("4. 只有全部通过后才能 commit")
    lines.append("")

    return "\n".join(lines)


def generate_prompt(task_json_path, small_task_id, work_dir="/Users/malin13/Documents/trae_projects/website_aicut"):
    data = load_task_json(task_json_path)
    task_info = get_task_info(data, small_task_id)
    if not task_info:
        print(f"Task {small_task_id} not found", file=sys.stderr)
        sys.exit(1)

    base_dir = Path(work_dir)
    doc_text = load_09_doc(base_dir)
    detail = extract_task_detail(doc_text, small_task_id)
    validation_md = _validation_block(small_task_id, work_dir)
    file_list = _file_hint(small_task_id)
    file_list_str = "\n".join(f"- {f}" for f in file_list)

    prompt = f"""# Task: {task_info['id']} — {task_info['title']}

## 你的角色
你是一个专注的软件开发代理。你的任务是完成下面描述的一个具体小任务，
并在完成后进行**严格的三层验证**（代码审查 → 测试 → 端到端）。

## ⚠️ 核心原则：验证优先
> **没有通过端到端验证的代码不得 commit。**
> 实现只占 30% 工作量，验证占 70%。

## 项目基本信息
- 这是一个 FastAPI + Next.js + SQLAlchemy 项目
- 工作目录: {work_dir}
- 当前分支: feature/smart-cut-taskcard-refactor-{task_info['id']}
- 主分支: feature/smart-cut-taskcard-refactor
- 大任务: {task_info['large_title']} ({task_info['large_id']})

## 任务描述
{task_info['title']}

{detail}

## 涉及的关键文件（你需要自己读取）
{file_list_str}

## 执行步骤
1. 读取上述关键文件，理解当前实现
2. 按照任务描述进行**最小化修改**
3. **运行三层验证**（见下方验证章节）
4. **只有全部验证通过后**才执行：
   ```bash
   git add 修改的文件
   git commit -m "[{task_info['id']}] {task_info['title']}"
   ```

{validation_md}

## 完成后
1. 在控制台输出执行摘要（2-3 句话）
2. 确保所有修改已 commit
3. 确保工作目录干净（`git status` 无未提交修改）

## 约束
- 只修改与当前任务直接相关的文件
- 不要修改 task.json、progress.md 等文档文件
- 不要修改其他 task 的代码
- 如果遇到困难，先尝试解决；如果确实无法完成，说明原因并尽可能完成部分工作
- 不要运行 git push
- **没有验证通过不要 commit**
"""
    return prompt


def run_validation(task_id, work_dir="/Users/malin13/Documents/trae_projects/website_aicut"):
    """运行指定任务的 E2E 验证。"""
    val = _TASK_VALIDATION.get(task_id)
    if not val:
        print(f"No validation defined for {task_id}")
        return 1

    print(f"\n{'='*60}")
    print(f"Running E2E validation for {task_id}")
    print(f"{'='*60}\n")

    passed = 0
    failed = 0

    # L1: 检查修改的文件
    print("[L1] Code review validation...")
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=work_dir, capture_output=True, text=True
        )
        modified = result.stdout.strip().split("\n") if result.stdout.strip() else []
        must_mod = val.get("l1_files_must_modify", [])
        must_not = val.get("l1_files_must_not_modify", [])

        for f in must_mod:
            if any(f in m for m in modified):
                print(f"  ✅ {f} modified")
                passed += 1
            else:
                print(f"  ❌ {f} NOT modified")
                failed += 1

        for f in must_not:
            if any(f in m for m in modified):
                print(f"  ❌ {f} unexpectedly modified")
                failed += 1
            else:
                print(f"  ✅ {f} not touched")
                passed += 1
    except Exception as e:
        print(f"  ⚠️ L1 check failed: {e}")

    # L2: 运行 pytest
    print("\n[L2] Test validation...")
    pytest_args = val.get("l2_pytest_args", [])
    if pytest_args:
        pytest_bin = "/Users/malin13/_MAL/_Projects_All/__AI_Agents/video_proc_pytools/virenv_aicut/bin/pytest"
        cmd = [pytest_bin] + pytest_args
        try:
            result = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                print(f"  ✅ pytest passed")
                passed += 1
            else:
                print(f"  ❌ pytest failed (exit {result.returncode})")
                print(f"  stderr: {result.stderr[:500]}")
                failed += 1
        except Exception as e:
            print(f"  ⚠️ pytest error: {e}")
    else:
        print("  ⏭️  No automated tests for this task")

    # L3: 端到端验证
    print("\n[L3] End-to-end validation...")
    l3_cmds = val.get("l3_commands", [])
    l3_exp = val.get("l3_expected", [])

    for i, cmd in enumerate(l3_cmds):
        exp = l3_exp[i] if i < len(l3_exp) else ""
        print(f"  Running: {cmd[:80]}...")
        try:
            result = subprocess.run(cmd, shell=True, cwd=work_dir, capture_output=True, text=True, timeout=30)
            output = result.stdout.strip()
            if exp:
                if exp in output:
                    print(f"    ✅ Output contains '{exp}'")
                    passed += 1
                else:
                    print(f"    ❌ Expected '{exp}' not found in output: {output[:200]}")
                    failed += 1
            else:
                print(f"    ℹ️  Output: {output[:200]}")
        except Exception as e:
            print(f"    ⚠️ Command failed: {e}")

    if not l3_cmds:
        print("  ⏭️  Manual E2E required (see task description)")

    print(f"\n{'='*60}")
    print(f"Validation result: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    return 0 if failed == 0 else 1


def mark_done(task_json_path, small_task_id):
    data = load_task_json(task_json_path)
    updated = False
    for lt in data["large_tasks"]:
        for st in lt["small_tasks"]:
            if st["id"] == small_task_id:
                st["status"] = "completed"
                updated = True
                break
        if all(s["status"] == "completed" for s in lt["small_tasks"]):
            lt["status"] = "completed"
    if not updated:
        print(f"Task {small_task_id} not found", file=sys.stderr)
        sys.exit(1)
    with open(task_json_path, 'w', encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Marked {small_task_id} as completed")


def main():
    parser = argparse.ArgumentParser(description="Kimi Print 接力开发工具")
    parser.add_argument("task_json", help="Path to task.json")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-pending", help="List all pending small tasks")

    gen = subparsers.add_parser("generate", help="Generate prompt for a task")
    gen.add_argument("task_id", help="Small task ID (e.g., S801)")
    gen.add_argument("--work-dir", default="/Users/malin13/Documents/trae_projects/website_aicut")

    done = subparsers.add_parser("mark-done", help="Mark a task as completed")
    done.add_argument("task_id", help="Small task ID")

    val = subparsers.add_parser("validate", help="Run E2E validation for a task")
    val.add_argument("task_id", help="Small task ID")
    val.add_argument("--work-dir", default="/Users/malin13/Documents/trae_projects/website_aicut")

    args = parser.parse_args()

    if args.command == "list-pending":
        tasks = get_pending_tasks(load_task_json(args.task_json))
        if not tasks:
            print("No pending tasks found.")
        for t in tasks:
            print(f"{t['id']}:{t['title']}")

    elif args.command == "generate":
        prompt = generate_prompt(args.task_json, args.task_id, args.work_dir)
        print(prompt)

    elif args.command == "mark-done":
        mark_done(args.task_json, args.task_id)

    elif args.command == "validate":
        sys.exit(run_validation(args.task_id, args.work_dir))


if __name__ == "__main__":
    main()
