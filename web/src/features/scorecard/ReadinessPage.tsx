import { Link } from 'react-router-dom'
import { useReadiness, useGaps } from '@/lib/api'
import { useControlStore } from '@/store/ui'
import { ScoreDonut } from './ScoreDonut'
import { FrameworkCard } from './FrameworkCard'
import { FreshnessStrip } from './FreshnessStrip'
import { GapList } from './GapList'
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/Card'
import { ErrorState, LoadingState, EmptyState } from '@/components/ui/Spinner'
import { Button } from '@/components/ui/Button'
import { ArrowRight } from 'lucide-react'

export function ReadinessPage() {
  const { data, isLoading, isError, error, refetch } = useReadiness()
  const gaps = useGaps()
  const openControl = useControlStore((s) => s.openControl)

  if (isLoading) return <LoadingState label="Scoring your readiness…" />
  if (isError)
    return <ErrorState message={error instanceof Error ? error.message : 'Failed to load'} onRetry={() => refetch()} />

  if (!data)
    return (
      <EmptyState
        title="No readiness data yet"
        hint="Connect your first evidence source to get a score."
        action={
          <Link to="/evidence">
            <Button size="sm">Upload an evidence artifact</Button>
          </Link>
        }
      />
    )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Readiness Scorecard</h1>
        <p className="text-[13px] text-muted-foreground">
          As of {data.as_of}
          {data.last_assessed_at ? ` · last assessed ${data.last_assessed_at}` : ''}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[auto_1fr]">
        <Card className="flex items-center justify-center p-6">
          <ScoreDonut data={data} />
        </Card>

        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <FrameworkCard title="ISO 42001" breakdown={data.frameworks.iso42001} />
            <FrameworkCard title="EU AI Act" breakdown={data.frameworks.eu_ai_act} />
          </div>
          <FreshnessStrip staleWithin30d={data.stale_within_30d} />
        </div>
      </div>

      <Card>
        <CardHeader className="flex items-center justify-between">
          <CardTitle>Gaps needing attention</CardTitle>
          <span className="text-[12px] text-muted-foreground">
            {gaps.data?.length ?? 0} open
          </span>
        </CardHeader>
        <CardBody>
          {gaps.isLoading ? (
            <LoadingState label="Loading gaps…" />
          ) : gaps.data && gaps.data.length > 0 ? (
            <GapList items={gaps.data} onSelect={openControl} />
          ) : (
            <p className="py-4 text-center text-[13px] text-muted-foreground">
              No missing or partial controls — fully covered.
            </p>
          )}
          <Link
            to="/controls"
            className="mt-3 inline-flex items-center gap-1 text-[13px] font-medium text-primary hover:underline"
          >
            Open the control library <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </CardBody>
      </Card>
    </div>
  )
}
