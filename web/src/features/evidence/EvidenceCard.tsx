import type { EvidenceArtifact, IngestStatus } from '@/lib/types'
import { cn } from '@/lib/utils'
import { CheckCircle2, Loader2, XCircle, Copy } from 'lucide-react'
import { useState } from 'react'

const INGEST_STYLES: Record<IngestStatus, string> = {
  processing: 'border-status-partial/40 bg-status-partial/5 text-status-partial',
  ingested: 'border-status-satisfied/40 bg-status-satisfied/5 text-status-satisfied',
  failed: 'border-status-missing/40 bg-status-missing/5 text-status-missing',
}

/** Provenance + ingest-status card (INT-4 / FOUND-3). Shows sha256 for tamper-evidence. */
export function EvidenceCard({ artifact }: { artifact?: EvidenceArtifact }) {
  const [copied, setCopied] = useState(false)
  const copyHash = async () => {
    try {
      await navigator.clipboard.writeText(artifact?.content_hash ?? '')
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard may be unavailable in tests */
    }
  }

  if (!artifact) {
    return <div className="h-28 animate-pulse rounded-card border border-border bg-muted/40" />
  }

  return (
    <div className="rounded-card border border-border bg-white p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate font-mono text-[13px] font-medium">{artifact.source}</p>
          <p className="text-[12px] uppercase tracking-wide text-muted-foreground">
            {artifact.evidence_type.replace('_', ' ')}
          </p>
        </div>
        <span
          className={cn(
            'inline-flex items-center gap-1 rounded-chip px-2 py-0.5 text-[11px] font-semibold uppercase',
            INGEST_STYLES[artifact.ingest_status],
          )}
        >
          {artifact.ingest_status === 'processing' && <Loader2 className="h-3 w-3 animate-spin" />}
          {artifact.ingest_status === 'ingested' && <CheckCircle2 className="h-3 w-3" />}
          {artifact.ingest_status === 'failed' && <XCircle className="h-3 w-3" />}
          {artifact.ingest_status}
        </span>
      </div>

      <div className="mt-2 flex items-center gap-1.5">
        <span className="font-mono text-[11px] text-muted-foreground">
          {artifact.content_hash.slice(0, 16)}…
        </span>
        <button
          type="button"
          onClick={copyHash}
          className="rounded-chip p-0.5 text-muted-foreground hover:bg-muted"
          title="Copy content hash"
        >
          <Copy className="h-3 w-3" />
        </button>
        {copied && <span className="text-[11px] text-status-satisfied">copied</span>}
      </div>

      <p className="mt-1 text-[11px] text-muted-foreground">
        collected {artifact.collected_at.slice(0, 10)}
      </p>
      {artifact.ingest_status === 'failed' && artifact.error && (
        <p className="mt-1 rounded-chip bg-status-missing/10 px-2 py-1 text-[12px] text-status-missing">
          {artifact.error}
        </p>
      )}
    </div>
  )
}
