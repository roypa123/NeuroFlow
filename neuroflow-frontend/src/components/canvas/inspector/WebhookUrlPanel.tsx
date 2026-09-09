import { useState } from 'react'
import { Copy, Check, Radio } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Field, FieldLabel, FieldDescription } from '@/components/ui/field'
import { useWorkflowWebhooks, useListenForTestWebhook } from '@/endpoints/webhooks'

// Webhook Trigger is the one node type genuinely allowed bespoke inspector
// UI (docs/06-canvas-and-editor.md #6.9's "no bespoke node UI" rule covers
// *parameters*, which stay fully descriptor-driven below this panel) --
// the registered URL is derived server state, not a parameter, and has no
// generic property-type representation.
export function WebhookUrlPanel({
  workflowId,
  nodeId,
  isActive,
}: {
  workflowId: string
  nodeId: string
  isActive: boolean
}) {
  const { data: registrations } = useWorkflowWebhooks(workflowId, isActive)
  const listenForTest = useListenForTestWebhook(workflowId)
  const [copied, setCopied] = useState(false)

  const registration = registrations?.find((r) => r.nodeId === nodeId)
  const testResult = listenForTest.data

  const copy = async (url: string) => {
    await navigator.clipboard.writeText(url)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  if (!isActive && !testResult) {
    return (
      <Field>
        <FieldLabel>Webhook URL</FieldLabel>
        <FieldDescription>Activate the workflow to get a production URL,</FieldDescription>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => listenForTest.mutate(nodeId)}
          disabled={listenForTest.isPending}
        >
          <Radio className="size-4" />
          {listenForTest.isPending ? 'Listening...' : 'Listen for test event (120s)'}
        </Button>
      </Field>
    )
  }

  const url = testResult?.url ?? registration?.url
  if (!url) return null

  return (
    <Field>
      <FieldLabel>{testResult ? 'Test webhook URL (expires in 120s)' : 'Webhook URL'}</FieldLabel>
      <div className="flex items-center gap-1.5">
        <Input readOnly value={url} className="font-mono text-xs" />
        <Button type="button" size="icon-sm" variant="outline" onClick={() => copy(url)}>
          {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
        </Button>
      </div>
    </Field>
  )
}
