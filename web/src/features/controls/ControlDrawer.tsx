import { useControlDetail } from '@/lib/api'
import { useControlStore } from '@/store/ui'
import { Sheet } from '@/components/ui/Sheet'
import { StatusChip } from '@/components/ui/StatusChip'
import { ErrorState, LoadingState } from '@/components/ui/Spinner'
import { ReviewCounselBadge } from './ReviewCounselBadge'
import { ExternalLink } from 'lucide-react'
import type { ControlDetail } from '@/lib/types'

/** Per-control detail drawer (FE-3). */
export function ControlDrawer() {
  const selectedId = useControlStore((s) => s.selectedControlId)
  const close = useControlStore((s) => s.closeControl)
  const { data, isLoading, isError, error, refetch } = useControlDetail(selectedId)

  // Keep the sheet mounted while a control is selected (controlled by store).
  const open = Boolean(selectedId)

  return (
    <Sheet
      open={open}
      onClose={close}
      title={
        selectedId ? (
          <div className="flex items-center gap-2">
            <span className="font-mono text-[13px] font-semibold">{selectedId}</span>
            <StatusChip status={data?.status ?? 'missing'} />
          </div>
        ) : null
      }
    >
      {isLoading && <LoadingState label="Loading control…" />}
      {isError && (
        <ErrorState message={error instanceof Error ? error.message : 'Failed'} onRetry={() => refetch()} />
      )}
      {data && <ControlDetailBody data={data} />}
    </Sheet>
  )
}

function ControlDetailBody({ data }: { data: ControlDetail }) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-base font-semibold">{data.control_name}</h2>
        {data.owner && (
          <p className="mt-0.5 text-[13px] text-muted-foreground">Owner: {data.owner}</p>
        )}
      </div>

      {data.review_counsel && <ReviewCounselBadge />}

      <Section title="Obligation mapping">
        {data.obligations.length ? (
          <div className="flex flex-wrap gap-1.5">
            {data.obligations.map((o) => (
              <a
                key={o.id}
                href={o.source_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 rounded-chip border border-border bg-muted/40 px-2 py-1 text-[12px] hover:bg-muted"
              >
                <span className="font-mono font-medium">Art. {o.article}</span>
                <span className="text-muted-foreground">{o.title}</span>
                <ExternalLink className="h-3 w-3 text-muted-foreground" />
              </a>
            ))}
          </div>
        ) : (
          <p className="text-[13px] text-muted-foreground">No obligations mapped.</p>
        )}
      </Section>

      <Section title="Remediation hint">
        {data.remediation_hint ? (
          <pre className="whitespace-pre-wrap rounded-card border border-border bg-muted/40 p-3 text-[13px]">
            {data.remediation_hint}
          </pre>
        ) : (
          <p className="text-[13px] text-status-satisfied">
            Satisfied — no remediation needed.
          </p>
        )}
      </Section>

      <Section title="Freshness">
        <FreshnessMeter
          ageDays={data.freshness.age_days}
          staleInDays={data.freshness.stale_in_days}
          collectedAt={data.freshness.collected_at}
        />
      </Section>

      <Section title={`Linked evidence (${data.linked_evidence.length})`}>
        {data.linked_evidence.length ? (
          <ul className="space-y-1.5">
            {data.linked_evidence.map((e) => (
              <li
                key={e.id}
                className="flex items-center justify-between rounded-card border border-border px-3 py-2 text-[13px]"
              >
                <span className="font-mono text-[12px]">{e.type}</span>
                <span className="truncate text-muted-foreground">{e.source}</span>
                <span className="font-mono text-[12px] text-muted-foreground">
                  {e.collected_at.slice(0, 10)}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[13px] text-muted-foreground">No linked evidence yet.</p>
        )}
      </Section>

      {data.history.length > 0 && (
        <Section title="History">
          <ul className="space-y-1 text-[12px] text-muted-foreground">
            {data.history.map((h, i) => (
              <li key={i} className="flex items-center justify-between">
                <StatusChip status={h.status as ControlDetail['status']} />
                <span className="font-mono">{h.changed_at.slice(0, 10)}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <button
        type="button"
        onClick={close}
        className="text-[13px] text-muted-foreground hover:underline"
      >
        Close
      </button>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="section-title mb-2">{title}</h3>
      {children}
    </div>
  )
}

/** 180-day freshness clock (FE-3). */
function FreshnessMeter({
  ageDays,
  staleInDays,
  collectedAt,
}: {
  ageDays: number | null
  staleInDays: number | null
  collectedAt: string | null
}) {
  if (collectedAt == null) {
    return <p className="text-[13px] text-muted-foreground">No evidence collected.</p>
  }
  const age = ageDays ?? 0
  const staleIn = staleInDays ?? 0
  const remaining = Math.max(0, staleIn)
  return (
    <div className="text-[13px]">
      <p>
        Collected <span className="font-mono">{age}</span> days ago
        {remaining > 0 ? (
          <span className="text-status-partial"> · stale in {remaining} days</span>
        ) : (
          <span className="text-status-missing"> · beyond the freshness window</span>
        )}
      </p>
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full"
          style={{
            width: `${Math.min(100, (age / 180) * 100)}%`,
            backgroundColor:
              remaining > 30 ? 'hsl(var(--status-satisfied))' : 'hsl(var(--status-partial))',
          }}
        />
      </div>
    </div>
  )
}
