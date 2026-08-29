import { useState } from 'react'
import { fetchReport, fetchReportJson } from '@/lib/api'
import { downloadFile } from '@/lib/download'
import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/Card'
import { LoadingState, ErrorState } from '@/components/ui/Spinner'
import { FileText, FileJson, FileDown, AlertTriangle } from 'lucide-react'

type Format = 'markdown' | 'json' | 'pdf'

/**
 * Audit / Export view (RPT-2). Markdown + JSON download ship in v0.2; the PDF
 * button calls the backend endpoint (deferred UI per frontend-plan H4 / product
 * scope split) and degrades gracefully if the endpoint isn't live yet.
 */
export function ExportPage() {
  const [pending, setPending] = useState<Format | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<{ format: Format; content: string } | null>(null)

  async function handleDownload(format: Format) {
    setPending(format)
    setError(null)
    try {
      if (format === 'json') {
        const json = await fetchReportJson()
        const text = JSON.stringify(json, null, 2)
        downloadFile('actready-report.json', text, 'application/json')
        setPreview({ format, content: text })
      } else if (format === 'markdown') {
        const md = await fetchReport('markdown')
        downloadFile('actready-report.md', md, 'text/markdown')
        setPreview({ format, content: md })
      } else {
        // PDF — backend capability exists in v0.2; best-effort fetch.
        const pdf = await fetchReport('pdf')
        downloadFile('actready-report.pdf', pdf, 'application/pdf')
        setPreview(null)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Export failed')
      setPreview(null)
    } finally {
      setPending(null)
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Audit / Export</h1>
        <p className="text-[13px] text-muted-foreground">
          Download an auditor-traceable report. Markdown + JSON are generated live; PDF uses the
          backend renderer.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
        <div className="space-y-3">
          <ExportButton
            icon={<FileText className="h-4 w-4" />}
            label="Download Markdown"
            loading={pending === 'markdown'}
            onClick={() => handleDownload('markdown')}
          />
          <ExportButton
            icon={<FileJson className="h-4 w-4" />}
            label="Download JSON"
            loading={pending === 'json'}
            onClick={() => handleDownload('json')}
          />
          <ExportButton
            icon={<FileDown className="h-4 w-4" />}
            label="Download PDF"
            loading={pending === 'pdf'}
            onClick={() => handleDownload('pdf')}
            hint="Rendered by backend WeasyPrint"
          />
          {error && <ErrorState message={error} />}
        </div>

        <Card className="min-h-[400px]">
          <CardHeader>
            <CardTitle>Preview</CardTitle>
          </CardHeader>
          <CardBody>
            {pending ? (
              <LoadingState label="Generating report…" />
            ) : preview ? (
              <pre className="max-h-[520px] overflow-auto whitespace-pre-wrap text-[12px]">
                {preview.content}
              </pre>
            ) : (
              <div className="flex flex-col items-center justify-center gap-2 py-12 text-center text-muted-foreground">
                <AlertTriangle className="h-5 w-5" />
                <p className="text-[13px]">Pick a format to preview your readiness report.</p>
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  )
}

function ExportButton({
  icon,
  label,
  loading,
  onClick,
  hint,
}: {
  icon: React.ReactNode
  label: string
  loading: boolean
  onClick: () => void
  hint?: string
}) {
  return (
    <div className="rounded-card border border-border bg-white p-3">
      <Button variant="outline" className="w-full justify-start" onClick={onClick} disabled={loading}>
        {loading ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" /> : icon}
        {label}
      </Button>
      {hint && <p className="mt-1.5 text-[12px] text-muted-foreground">{hint}</p>}
    </div>
  )
}
