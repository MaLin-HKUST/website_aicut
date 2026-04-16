"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  FILTER_OPTIONS,
  formatUpdatedAt,
  getMockTaskCenterItems,
  getTaskSubtitle,
  getTimelineItems,
  STATUS_META,
  TaskCenterFilter,
  TaskCenterItem,
} from "@/lib/task-center";

function ProgressBar({ progress, className }: { progress: number; className: string }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-stone-200">
      <div className={`h-full rounded-full transition-all ${className}`} style={{ width: `${Math.max(8, progress)}%` }} />
    </div>
  );
}

export function TaskCenterShell() {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<TaskCenterFilter>("all");
  const [items] = useState<TaskCenterItem[]>(() => getMockTaskCenterItems());
  const [selectedId, setSelectedId] = useState<string>(() => getMockTaskCenterItems()[0]?.id ?? "");

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      const matchesFilter = filter === "all" ? true : item.status === filter;
      const keyword = search.trim().toLowerCase();
      const matchesSearch =
        keyword.length === 0 ||
        item.title.toLowerCase().includes(keyword) ||
        item.id.toLowerCase().includes(keyword) ||
        item.inputSummary.some((part) => part.toLowerCase().includes(keyword));
      return matchesFilter && matchesSearch;
    });
  }, [filter, items, search]);

  const selectedTask = filteredItems.find((item) => item.id === selectedId) ?? filteredItems[0] ?? null;

  return (
    <main className="min-h-screen bg-[#f6efe4] p-4 lg:p-8">
      <div className="mx-auto grid max-w-7xl gap-5 xl:grid-cols-[0.78fr_1.22fr]">
        <Card className="rounded-[32px] border-[#d8cfbf] bg-[#242a35] p-6 text-stone-100 shadow-panel">
          <p className="text-sm uppercase tracking-[0.3em] text-stone-300">Task Hub</p>
          <div className="mt-8 space-y-3">
            {["Dashboard", "Queue", "Artifacts", "Downloads", "Logs", "Settings"].map((item) => {
              const active = item === "Queue";
              return (
                <div
                  key={item}
                  className={`rounded-[18px] px-4 py-3 text-sm font-medium ${
                    active ? "bg-[#34415f] text-white" : "text-stone-300"
                  }`}
                >
                  {item}
                </div>
              );
            })}
          </div>
        </Card>

        <div className="space-y-5">
          <section className="rounded-[32px] border border-[#e1d7c7] bg-[#fdf9f2] p-6 shadow-panel">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.3em] text-stone-500">Task Center</p>
                <h1 className="mt-3 text-4xl font-semibold text-[#231815]">My Job Queue</h1>
                <p className="mt-3 text-sm leading-7 text-stone-600">
                  当前版本先承载 Smart Cut 任务，页面结构按未来统一任务队列设计。
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <Button type="button">Refresh</Button>
                <Button type="button" variant="secondary">
                  Export
                </Button>
              </div>
            </div>

            <div className="mt-6 grid gap-3 md:grid-cols-5">
              {FILTER_OPTIONS.map((option) => {
                const active = option.key === filter;
                return (
                  <button
                    key={option.key}
                    className={`rounded-[22px] border px-4 py-4 text-left transition ${
                      active ? "border-[#c4633d] bg-[#fff1e7]" : "border-[#e3d8c7] bg-white"
                    }`}
                    onClick={() => setFilter(option.key)}
                    type="button"
                  >
                    <p className="text-xs uppercase tracking-[0.2em] text-stone-500">Status</p>
                    <p className="mt-3 text-xl font-semibold text-[#231815]">{option.label}</p>
                    <p className="mt-2 text-sm text-stone-500">
                      {items.filter((item) => option.key === "all" || item.status === option.key).length} tasks
                    </p>
                  </button>
                );
              })}
            </div>

            <div className="mt-5 flex flex-col gap-3 rounded-[26px] border border-[#e3d8c7] bg-white p-4 lg:flex-row">
              <Input
                className="h-12 rounded-full border-[#ded3c2]"
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search task / task id / filename"
                value={search}
              />
              <div className="flex gap-3">
                <Button type="button" variant="secondary">
                  Type: Video
                </Button>
                <Button type="button" variant="secondary">
                  Sort: Latest
                </Button>
              </div>
            </div>
          </section>

          <section className="grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
            <Card className="rounded-[32px] border-[#e1d7c7] bg-[#fdf9f2] p-4 shadow-panel lg:p-5">
              <div className="space-y-3">
                {filteredItems.map((item) => {
                  const active = item.id === selectedTask?.id;
                  const statusMeta = STATUS_META[item.status];
                  return (
                    <button
                      key={item.id}
                      className={`block w-full rounded-[24px] border p-4 text-left transition ${
                        active ? "border-[#c4633d] bg-[#fff4ec]" : "border-[#e1d7c7] bg-white hover:bg-[#faf2e7]"
                      }`}
                      onClick={() => setSelectedId(item.id)}
                      type="button"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-lg font-semibold text-[#231815]">{item.title}</p>
                          <p className="mt-1 text-sm text-stone-500">{item.id}</p>
                        </div>
                        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusMeta.badgeClassName}`}>
                          {statusMeta.label}
                        </span>
                      </div>
                      <p className="mt-3 text-sm text-stone-600">{getTaskSubtitle(item)}</p>
                      <div className="mt-4">
                        <ProgressBar className={statusMeta.progressClassName} progress={item.progress} />
                      </div>
                      <div className="mt-4 flex items-center justify-between text-sm text-stone-500">
                        <span>{item.currentStage}</span>
                        <span>{formatUpdatedAt(item.updatedAt)}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </Card>

            <Card className="rounded-[32px] border-[#e1d7c7] bg-[#fdf9f2] p-6 shadow-panel lg:p-7">
              {!selectedTask ? (
                <div className="rounded-[26px] border border-dashed border-[#d7ccb9] bg-white p-8 text-sm text-stone-500">
                  当前筛选条件下没有任务。
                </div>
              ) : (
                <>
                  <div className="flex flex-col gap-4 border-b border-[#e3d8c7] pb-5 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <p className="text-xs uppercase tracking-[0.28em] text-stone-500">Task Detail</p>
                      <h2 className="mt-2 text-3xl font-semibold text-[#231815]">{selectedTask.title}</h2>
                      <p className="mt-2 text-sm text-stone-500">{selectedTask.id}</p>
                    </div>
                    <span
                      className={`inline-flex rounded-full px-4 py-2 text-sm font-semibold ${
                        STATUS_META[selectedTask.status].badgeClassName
                      }`}
                    >
                      {STATUS_META[selectedTask.status].label}
                    </span>
                  </div>

                  <div className="mt-5 grid gap-3 md:grid-cols-3">
                    <div className="rounded-[24px] border border-[#e1d7c7] bg-white p-4">
                      <p className="text-xs uppercase tracking-[0.2em] text-stone-500">Type</p>
                      <p className="mt-3 text-base font-semibold text-[#231815]">{selectedTask.taskType}</p>
                    </div>
                    <div className="rounded-[24px] border border-[#e1d7c7] bg-white p-4">
                      <p className="text-xs uppercase tracking-[0.2em] text-stone-500">Step</p>
                      <p className="mt-3 text-base font-semibold text-[#231815]">{selectedTask.currentStage}</p>
                    </div>
                    <div className="rounded-[24px] border border-[#e1d7c7] bg-white p-4">
                      <p className="text-xs uppercase tracking-[0.2em] text-stone-500">Updated</p>
                      <p className="mt-3 text-base font-semibold text-[#231815]">{formatUpdatedAt(selectedTask.updatedAt)}</p>
                    </div>
                  </div>

                  <div className="mt-6 rounded-[26px] border border-[#e1d7c7] bg-white p-5">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-stone-500">Progress</p>
                      <span className="text-sm font-semibold text-[#231815]">{selectedTask.progress}%</span>
                    </div>
                    <div className="mt-3">
                      <ProgressBar className={STATUS_META[selectedTask.status].progressClassName} progress={selectedTask.progress} />
                    </div>
                  </div>

                  <div className="mt-6 grid gap-5 lg:grid-cols-[0.98fr_1.02fr]">
                    <div className="rounded-[26px] border border-[#e1d7c7] bg-white p-5">
                      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-stone-500">Timeline</p>
                      <div className="mt-4 space-y-4">
                        {getTimelineItems(selectedTask).map((item, index) => (
                          <div key={item} className="flex items-start gap-3">
                            <div className="mt-1 h-3 w-3 rounded-full bg-[#c4633d]" />
                            <div>
                              <p className="text-sm font-semibold text-[#231815]">{item}</p>
                              <p className="mt-1 text-sm text-stone-500">
                                {index === getTimelineItems(selectedTask).length - 1 ? "Current focus" : "Completed or queued"}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="rounded-[26px] border border-[#e1d7c7] bg-white p-5">
                      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-stone-500">Input / Output Summary</p>
                      <div className="mt-4 grid gap-4 md:grid-cols-2">
                        <div>
                          <p className="text-xs uppercase tracking-[0.2em] text-stone-500">Inputs</p>
                          <div className="mt-2 space-y-2">
                            {selectedTask.inputSummary.map((item) => (
                              <div key={item} className="rounded-2xl bg-[#f7efe2] px-3 py-2 text-sm text-stone-700">
                                {item}
                              </div>
                            ))}
                          </div>
                        </div>
                        <div>
                          <p className="text-xs uppercase tracking-[0.2em] text-stone-500">Outputs</p>
                          <div className="mt-2 space-y-2">
                            {(selectedTask.outputSummary ?? ["Waiting for outputs"]).map((item) => (
                              <div key={item} className="rounded-2xl bg-[#f7efe2] px-3 py-2 text-sm text-stone-700">
                                {item}
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                      {selectedTask.errorMessage ? (
                        <div className="mt-4 rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{selectedTask.errorMessage}</div>
                      ) : null}
                      <div className="mt-5 flex flex-wrap gap-3">
                        <Button type="button">View</Button>
                        {selectedTask.downloadUrl ? (
                          <Button type="button" variant="secondary">
                            Download
                          </Button>
                        ) : (
                          <Button type="button" variant="secondary">
                            Continue
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                </>
              )}
            </Card>
          </section>
        </div>
      </div>
    </main>
  );
}
