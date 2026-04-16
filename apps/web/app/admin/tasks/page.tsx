import { Suspense } from "react";

import { TaskCenterShell } from "@/components/task-center/task-center-shell";

export default function AdminTasksPage() {
  return (
    <Suspense fallback={null}>
      <TaskCenterShell mode="admin" />
    </Suspense>
  );
}
