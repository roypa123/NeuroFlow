import { lazy, Suspense } from 'react'
import { Textarea } from '@/components/ui/textarea'

// Dynamically imported -- docs/06-canvas-and-editor.md #6.12 rule 8. Monaco
// is a multi-hundred-KB dependency that most editor sessions never touch a
// code/expression field in.
const Editor = lazy(() => import('@monaco-editor/react'))

interface MonacoFieldProps {
  value: string
  onChange: (value: string) => void
  language?: string
  height?: number
}

export function MonacoField({ value, onChange, language = 'json', height = 160 }: MonacoFieldProps) {
  return (
    <Suspense
      fallback={
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={6}
          className="font-mono text-xs"
        />
      }
    >
      <div className="overflow-hidden rounded-md border border-input">
        <Editor
          height={height}
          language={language}
          value={value}
          onChange={(next) => onChange(next ?? '')}
          theme="vs-dark"
          options={{
            minimap: { enabled: false },
            fontSize: 12,
            scrollBeyondLastLine: false,
            lineNumbers: 'off',
            folding: false,
          }}
        />
      </div>
    </Suspense>
  )
}
