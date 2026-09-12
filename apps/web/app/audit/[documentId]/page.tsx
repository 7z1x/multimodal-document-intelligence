import { AuditHistory } from "@/features/documents/audit-history";

export default async function AuditPage({
  params,
}: {
  params: Promise<{ documentId: string }>;
}) {
  const { documentId } = await params;
  return <AuditHistory documentId={documentId} />;
}
