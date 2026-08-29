import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts'
import { donutSegments, roundScore } from '@/lib/score'
import type { ReadinessResponse } from '@/lib/types'

/**
 * Hero readiness donut (FE-1). Shows the 0–100 headline score in the center
 * and a satisfied/partial/missing ring around it. Segment counts come straight
 * from the engine; the headline score is the engine's weighted value.
 */
export function ScoreDonut({ data }: { data: ReadinessResponse }) {
  const segments = donutSegments(data)
  const score = roundScore(data.readiness_score)

  return (
    <div className="relative h-52 w-52">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={segments}
            dataKey="value"
            innerRadius={70}
            outerRadius={96}
            paddingAngle={2}
            stroke="none"
            startAngle={90}
            endAngle={-270}
          >
            {segments.map((s) => (
              <Cell key={s.name} fill={s.color} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono text-[48px] font-bold leading-none tabular-nums text-foreground">
          {score}
        </span>
        <span className="mt-1 text-[11px] uppercase tracking-wide text-muted-foreground">
          readiness
        </span>
      </div>
    </div>
  )
}
