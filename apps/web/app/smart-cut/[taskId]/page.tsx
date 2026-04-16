import { SmartCutWorkspace } from "@/components/smart-cut/workspace";

export default async function SmartCutTaskPage({
  params,
}: {
  params: Promise<{ taskId: string }>;
}) {
  const { taskId } = await params;
  return <SmartCutWorkspace taskId={taskId} />;
}
