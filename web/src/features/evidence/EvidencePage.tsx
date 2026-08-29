import { useState } from 'react'
import { UploadDropzone } from './UploadDropzone'
import { EvidenceCard } from './EvidenceCard'
import { useEvidence } from '@/lib/api'
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/Spinner'

/**
 * Evidence Vault (INT-4). Minimal: drag-drop upload + type select, then poll the
 * just-uploaded artifact's ingest status. There is no contract list endpoint yet,
 * so uploaded artifacts are tracked client-side and their live status polled via
 * GET /api/evidence/:id (useEvidence auto-polls while `processing`).
 */
export function EvidencePage() {
  const [uploadedIds, setUploadedIds] = useState<string[]>([])

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Evidence Vault</h1>
        <p className="text-[13px] text-muted-foreground">
          Immutable, hash-chained artifacts — the audit wedge. Uploaded evidence re-runs the engine.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Upload artifact</CardTitle>
          </CardHeader>
          <CardBody>
            <UploadDropzone onUploaded={(id) => setUploadedIds((ids) => [id, ...ids])} />
          </CardBody>
        </Card>

        <div>
          <h2 className="section-title mb-3">Artifacts ({uploadedIds.length})</h2>
          {uploadedIds.length === 0 ? (
            <EmptyState
              title="No evidence yet"
              hint="Upload a model card, eval run, or incident log to start scoring."
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {uploadedIds.map((id) => (
                <PolledEvidence key={id} id={id} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/** Polls one artifact's ingest status and renders its card. */
function PolledEvidence({ id }: { id: string }) {
  const { data } = useEvidence(id)
  return <EvidenceCard artifact={data ?? undefined} />
}
