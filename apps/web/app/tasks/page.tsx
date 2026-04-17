import { Suspense } from "react";

import { UserTasksShell } from "@/components/task-center/user-tasks-shell";

export default function TasksPage() {
  return (
    <Suspense fallback={null}>
      <UserTasksShell />
    </Suspense>
  );
}
