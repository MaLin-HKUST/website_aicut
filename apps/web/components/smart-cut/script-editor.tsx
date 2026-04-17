"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { applyRangesToScript, DeleteRange, mergeRanges, parseBraceScript, rangeContainsIndex } from "@/lib/smart-cut";

type Selection = { start: number; end: number } | null;

function normalizeSelection(selection: Selection): Selection {
  if (!selection) return null;
  const start = Math.min(selection.start, selection.end);
  const end = Math.max(selection.start, selection.end) + 1;
  if (end <= start) return null;
  return { start, end };
}

function addRange(ranges: DeleteRange[], selection: Selection): DeleteRange[] {
  if (!selection) return ranges;
  const normalized = normalizeSelection(selection);
  if (!normalized) return ranges;
  return mergeRanges([...ranges, normalized]);
}

function removeRange(ranges: DeleteRange[], selection: Selection): DeleteRange[] {
  const normalized = normalizeSelection(selection);
  if (!normalized) return ranges;

  const next: DeleteRange[] = [];
  for (const range of ranges) {
    if (normalized.end <= range.start || normalized.start >= range.end) {
      next.push(range);
      continue;
    }
    if (normalized.start > range.start) {
      next.push({ start: range.start, end: normalized.start });
    }
    if (normalized.end < range.end) {
      next.push({ start: normalized.end, end: range.end });
    }
  }
  return mergeRanges(next);
}

export function SmartCutScriptEditor({
  script,
  disabled = false,
  onScriptChange,
}: {
  script: string;
  disabled?: boolean;
  onScriptChange: (nextScript: string) => void;
}) {
  const [{ visibleText, ranges }, setEditorState] = useState(() => parseBraceScript(script));
  const [dragging, setDragging] = useState(false);
  const [selection, setSelection] = useState<Selection>(null);

  useEffect(() => {
    setEditorState(parseBraceScript(script));
    setSelection(null);
    setDragging(false);
  }, [script]);

  const normalizedSelection = useMemo(() => normalizeSelection(selection), [selection]);

  function commit(nextRanges: DeleteRange[]) {
    const merged = mergeRanges(nextRanges);
    setEditorState({ visibleText, ranges: merged });
    onScriptChange(applyRangesToScript(visibleText, merged));
    setSelection(null);
    setDragging(false);
  }

  function beginSelection(index: number) {
    if (disabled) return;
    setSelection({ start: index, end: index });
    setDragging(true);
  }

  function extendSelection(index: number) {
    if (!dragging || disabled) return;
    setSelection((current) => (current ? { ...current, end: index } : current));
  }

  function finishSelection() {
    if (disabled) return;
    setDragging(false);
  }

  const selectedCount = normalizedSelection ? normalizedSelection.end - normalizedSelection.start : 0;

  return (
    <Card className="rounded-[30px] border-[#e8dbca] bg-[linear-gradient(180deg,_rgba(255,255,255,0.96),_rgba(255,250,243,0.96))] p-5 shadow-sm lg:p-6">
      <div className="flex flex-col gap-4 border-b border-dashed border-[#eadfce] pb-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs tracking-[0.24em] text-stone-500">删除线调稿台</p>
          <h3 className="mt-2 text-2xl font-semibold text-[#231815]">删除线脚本调整</h3>
          <p className="mt-2 text-sm leading-7 text-stone-600">
            只调整删除范围，不改写正文。先拖选文字，再点下方按钮把它标为删除或恢复保留。
          </p>
        </div>
        <div className="rounded-[22px] border border-[#eadfce] bg-white px-4 py-3 text-sm text-stone-500">
          {selectedCount > 0 ? `当前选中 ${selectedCount} 个字` : "未选中内容"}
        </div>
      </div>

      <div className="mt-5 rounded-[26px] border border-[#eadfce] bg-white p-4 lg:p-5">
        <div
          className="min-h-[260px] cursor-text select-none rounded-[22px] bg-[#fffdf9] p-3 text-[17px] leading-9 text-[#2d211d]"
          onMouseLeave={finishSelection}
          onMouseUp={finishSelection}
          role="presentation"
        >
          {visibleText.split("").map((char, index) => {
            const deleted = rangeContainsIndex(ranges, index);
            const selected =
              normalizedSelection !== null &&
              index >= normalizedSelection.start &&
              index < normalizedSelection.end;

            return (
              <span
                key={`${char}-${index}`}
                className={[
                  "inline-block rounded px-[1px] transition",
                  deleted ? "text-stone-400 line-through decoration-2" : "",
                  selected ? "bg-[#fde6c9] text-[#8b3a1d]" : "",
                  !deleted && !selected ? "hover:bg-[#f7efe2]" : "",
                ].join(" ")}
                data-index={index}
                onMouseDown={() => beginSelection(index)}
                onMouseEnter={() => extendSelection(index)}
                onMouseUp={finishSelection}
              >
                {char === " " ? "\u00A0" : char}
              </span>
            );
          })}
        </div>

        <div className="mt-4 flex flex-wrap gap-3">
          <Button
            className="h-11 px-5"
            disabled={disabled || !normalizedSelection}
            onClick={() => commit(addRange(ranges, normalizedSelection))}
            type="button"
          >
            标记删除
          </Button>
          <Button
            className="h-11 px-5"
            disabled={disabled || !normalizedSelection}
            onClick={() => commit(removeRange(ranges, normalizedSelection))}
            type="button"
            variant="secondary"
          >
            恢复保留
          </Button>
          <Button
            className="h-11 px-5"
            disabled={disabled || ranges.length === 0}
            onClick={() => commit([])}
            type="button"
            variant="ghost"
          >
            清空删除标记
          </Button>
        </div>
      </div>
    </Card>
  );
}
