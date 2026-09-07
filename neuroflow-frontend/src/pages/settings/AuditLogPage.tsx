import { ScrollText } from 'lucide-react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { ComingSoon } from '@/components/common/ComingSoon'
import { useAuditLogs } from '@/endpoints/audit'
import { useCurrentOrganization } from '@/hooks/useCurrentOrganization'

export default function AuditLogPage() {
  const currentOrganization = useCurrentOrganization()

  if (!currentOrganization) {
    return (
      <ComingSoon
        icon={ScrollText}
        title="Audit log"
        description="Join or create an organization first."
      />
    )
  }

  const canView =
    currentOrganization.role === 'owner' || currentOrganization.role === 'admin'

  if (!canView) {
    return (
      <ComingSoon
        icon={ScrollText}
        title="Audit log"
        description="Only owners and admins can view the audit log."
      />
    )
  }

  return <AuditLogPageContent organizationId={currentOrganization.id} />
}

function AuditLogPageContent({ organizationId }: { organizationId: string }) {
  const { data: logs, isLoading } = useAuditLogs(organizationId)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Audit log</CardTitle>
        <CardDescription>Recent changes to this organization.</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading...</p>
        ) : logs && logs.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Action</TableHead>
                <TableHead>Resource</TableHead>
                <TableHead>When</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logs.map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="font-mono text-xs">{log.action}</TableCell>
                  <TableCell className="text-muted-foreground">{log.resourceType}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(log.createdAt).toLocaleString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <p className="text-sm text-muted-foreground">Nothing recorded yet.</p>
        )}
      </CardContent>
    </Card>
  )
}
