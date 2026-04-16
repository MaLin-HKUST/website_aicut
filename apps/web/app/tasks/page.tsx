import { Suspense } from "react";

import { TaskCenterShell } from "@/components/task-center/task-center-shell";

export default function TasksPage() {
  return (
    <Suspense fallback={null}>
      <TaskCenterShell />
    </Suspense>
  );
}
