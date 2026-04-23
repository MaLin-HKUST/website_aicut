import { SmartCutWorkspace } from "@/components/smart-cut/workspace";

export default async function SmartCutTaskPage({
  params,
}: {
  params: Promise<{ taskId: string }>;
}) {
  const resolved = await params;
  return <SmartCutWorkspace taskId={resolved.taskId} />;
}
