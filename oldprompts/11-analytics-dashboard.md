# Task: Analytics Dashboard with Chart.js

**Project**: MAI React Frontend (`/Users/maxwell/Projects/MAI`)
**Goal**: Install Chart.js + react-chartjs-2, create AnalyticsDashboard with UsageStats, AgentInsights, and SystemHealth components
**Sequence**: 11 of 14
**Depends On**: 10-command-palette.md completed

---

## Archon Task Management (REQUIRED)

### Task Info
- **Task ID**: `1bb2200c-3195-4b40-ac07-f2dbb19a3b56`
- **Project ID**: `17384994-d1d6-4286-992b-bf82d7485830`

### Update Status
```bash
curl -X PUT "http://localhost:8181/api/tasks/1bb2200c-3195-4b40-ac07-f2dbb19a3b56" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

curl -X PUT "http://localhost:8181/api/tasks/1bb2200c-3195-4b40-ac07-f2dbb19a3b56" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The Analytics page currently shows a placeholder. This task builds a comprehensive dashboard with:

- **Usage Statistics**: Line chart showing messages/tokens over time
- **Agent Insights**: Doughnut chart showing agent usage distribution
- **System Health**: Status cards for Redis, PostgreSQL, Qdrant, LLM
- **Model Usage**: Bar chart showing model distribution

For this task, we'll use **mock data** since the backend APIs (prompts 12-14) haven't been built yet. The components will be ready to connect to real APIs once available.

---

## Requirements

### 1. Install Chart.js Dependencies

```bash
cd /Users/maxwell/Projects/MAI/frontend
npm install chart.js react-chartjs-2
```

### 2. Register Chart.js Components

Create `frontend/src/lib/chart.ts`:

```tsx
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

// Default chart options for dark theme
export const defaultChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: {
        color: 'hsl(var(--foreground))',
      },
    },
  },
  scales: {
    x: {
      ticks: {
        color: 'hsl(var(--muted-foreground))',
      },
      grid: {
        color: 'hsl(var(--border))',
      },
    },
    y: {
      ticks: {
        color: 'hsl(var(--muted-foreground))',
      },
      grid: {
        color: 'hsl(var(--border))',
      },
    },
  },
}

export { ChartJS }
```

### 3. Create useAnalytics Hook with Mock Data

Create `frontend/src/hooks/useAnalytics.ts`:

```tsx
import { useState, useEffect } from 'react'

export interface UsageDataPoint {
  date: string
  messages: number
  tokens: number
}

export interface AgentUsageData {
  name: string
  usageCount: number
  avgResponseTime: number
  errorRate: number
}

export interface ModelUsageData {
  name: string
  usageCount: number
  tokens: number
}

export interface AnalyticsData {
  totalMessages: number
  totalSessions: number
  totalTokens: number
  avgResponseTime: number
  usage: UsageDataPoint[]
  agents: AgentUsageData[]
  models: ModelUsageData[]
}

// Mock data for development
const generateMockData = (): AnalyticsData => {
  const today = new Date()
  const usage: UsageDataPoint[] = []

  for (let i = 13; i >= 0; i--) {
    const date = new Date(today)
    date.setDate(date.getDate() - i)
    usage.push({
      date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      messages: Math.floor(Math.random() * 100) + 20,
      tokens: Math.floor(Math.random() * 50000) + 10000,
    })
  }

  return {
    totalMessages: usage.reduce((sum, d) => sum + d.messages, 0),
    totalSessions: Math.floor(Math.random() * 50) + 20,
    totalTokens: usage.reduce((sum, d) => sum + d.tokens, 0),
    avgResponseTime: Math.floor(Math.random() * 500) + 200,
    usage,
    agents: [
      { name: 'Chat', usageCount: 450, avgResponseTime: 320, errorRate: 0.5 },
      { name: 'Coder', usageCount: 230, avgResponseTime: 450, errorRate: 1.2 },
      { name: 'Researcher', usageCount: 120, avgResponseTime: 680, errorRate: 2.1 },
    ],
    models: [
      { name: 'Llama 3.1 8B', usageCount: 520, tokens: 450000 },
      { name: 'Mistral 7B', usageCount: 280, tokens: 230000 },
    ],
  }
}

export function useAnalytics() {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    // Simulate API call
    const fetchData = async () => {
      try {
        setIsLoading(true)
        // TODO: Replace with actual API call when backend is ready
        // const response = await fetch('/api/v1/analytics/usage')
        // const data = await response.json()
        await new Promise(resolve => setTimeout(resolve, 500))
        setData(generateMockData())
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to fetch analytics'))
      } finally {
        setIsLoading(false)
      }
    }

    fetchData()
  }, [])

  return { data, isLoading, error }
}
```

### 4. Create useHealth Hook

Create `frontend/src/hooks/useHealth.ts`:

```tsx
import { useState, useEffect, useCallback } from 'react'

export interface ServiceHealth {
  ok: boolean
  latency_ms?: number
  error?: string
}

export interface DetailedHealth {
  status: 'healthy' | 'degraded' | 'unhealthy'
  services: {
    redis: ServiceHealth
    postgres: ServiceHealth
    qdrant: ServiceHealth
    llm: ServiceHealth
  }
  total_latency_ms: number
}

// Mock health data for development
const generateMockHealth = (): DetailedHealth => ({
  status: 'healthy',
  services: {
    redis: { ok: true, latency_ms: 2 },
    postgres: { ok: true, latency_ms: 5 },
    qdrant: { ok: Math.random() > 0.2, latency_ms: 15 },
    llm: { ok: Math.random() > 0.3, latency_ms: 50 },
  },
  total_latency_ms: 72,
})

export function useHealth(pollInterval = 30000) {
  const [health, setHealth] = useState<DetailedHealth | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchHealth = useCallback(async () => {
    try {
      // TODO: Replace with actual API call when backend is ready
      // const response = await fetch('/health/detailed')
      // const data = await response.json()
      setHealth(generateMockHealth())
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch health'))
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchHealth()
    const interval = setInterval(fetchHealth, pollInterval)
    return () => clearInterval(interval)
  }, [fetchHealth, pollInterval])

  return { health, isLoading, error, refresh: fetchHealth }
}
```

### 5. Create StatCard Component

Create `frontend/src/components/analytics/StatCard.tsx`:

```tsx
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface StatCardProps {
  title: string
  value: string | number
  description?: string
  icon?: React.ReactNode
  trend?: {
    value: number
    isPositive: boolean
  }
  className?: string
}

export function StatCard({ title, value, description, icon, trend, className }: StatCardProps) {
  return (
    <Card className={cn('', className)}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          {icon && <div className="text-muted-foreground">{icon}</div>}
        </div>
        <div className="mt-2">
          <p className="text-2xl font-bold">{value}</p>
          {description && (
            <p className="text-xs text-muted-foreground mt-1">{description}</p>
          )}
          {trend && (
            <p className={cn(
              'text-xs mt-1',
              trend.isPositive ? 'text-green-500' : 'text-red-500'
            )}>
              {trend.isPositive ? '↑' : '↓'} {Math.abs(trend.value)}% from last period
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
```

### 6. Create UsageChart Component

Create `frontend/src/components/analytics/UsageChart.tsx`:

```tsx
import { Line } from 'react-chartjs-2'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import type { UsageDataPoint } from '@/hooks/useAnalytics'
import '@/lib/chart' // Register Chart.js components

interface UsageChartProps {
  data: UsageDataPoint[]
}

export function UsageChart({ data }: UsageChartProps) {
  const chartData = {
    labels: data.map(d => d.date),
    datasets: [
      {
        label: 'Messages',
        data: data.map(d => d.messages),
        borderColor: 'hsl(199, 89%, 48%)', // primary color
        backgroundColor: 'hsla(199, 89%, 48%, 0.1)',
        fill: true,
        tension: 0.4,
        yAxisID: 'y',
      },
      {
        label: 'Tokens (K)',
        data: data.map(d => Math.round(d.tokens / 1000)),
        borderColor: 'hsl(142, 71%, 45%)', // green
        backgroundColor: 'transparent',
        tension: 0.4,
        yAxisID: 'y1',
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          usePointStyle: true,
          padding: 20,
        },
      },
    },
    scales: {
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        title: {
          display: true,
          text: 'Messages',
        },
      },
      y1: {
        type: 'linear' as const,
        display: true,
        position: 'right' as const,
        grid: {
          drawOnChartArea: false,
        },
        title: {
          display: true,
          text: 'Tokens (K)',
        },
      },
    },
  }

  return (
    <Card className="col-span-2">
      <CardHeader>
        <CardTitle>Usage Over Time</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <Line data={chartData} options={options} />
        </div>
      </CardContent>
    </Card>
  )
}
```

### 7. Create AgentInsights Component

Create `frontend/src/components/analytics/AgentInsights.tsx`:

```tsx
import { Doughnut } from 'react-chartjs-2'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import type { AgentUsageData } from '@/hooks/useAnalytics'
import '@/lib/chart'

interface AgentInsightsProps {
  data: AgentUsageData[]
}

export function AgentInsights({ data }: AgentInsightsProps) {
  const chartData = {
    labels: data.map(d => d.name),
    datasets: [
      {
        data: data.map(d => d.usageCount),
        backgroundColor: [
          'hsl(199, 89%, 48%)', // primary
          'hsl(142, 71%, 45%)', // green
          'hsl(262, 83%, 58%)', // purple
          'hsl(31, 97%, 72%)',  // orange
        ],
        borderWidth: 0,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: {
          usePointStyle: true,
          padding: 20,
        },
      },
    },
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent Usage</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[200px]">
          <Doughnut data={chartData} options={options} />
        </div>

        {/* Agent Stats */}
        <div className="mt-4 space-y-2">
          {data.map(agent => (
            <div key={agent.name} className="flex items-center justify-between text-sm">
              <span>{agent.name}</span>
              <div className="flex items-center gap-4 text-muted-foreground">
                <span>{agent.usageCount} calls</span>
                <span>{agent.avgResponseTime}ms avg</span>
                <span className={agent.errorRate > 1 ? 'text-destructive' : ''}>
                  {agent.errorRate}% errors
                </span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
```

### 8. Create SystemHealth Component

Create `frontend/src/components/analytics/SystemHealth.tsx`:

```tsx
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useHealth } from '@/hooks/useHealth'
import { Database, Cpu, Brain, RefreshCw, Server } from 'lucide-react'

const SERVICE_INFO = {
  redis: { name: 'Redis', icon: Database, description: 'Cache & queue' },
  postgres: { name: 'PostgreSQL', icon: Database, description: 'Database' },
  qdrant: { name: 'Qdrant', icon: Cpu, description: 'Vector store' },
  llm: { name: 'LM Studio', icon: Brain, description: 'LLM server' },
}

export function SystemHealth() {
  const { health, isLoading, refresh } = useHealth(10000) // Poll every 10s

  if (isLoading && !health) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>System Health</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="flex items-center gap-2">
          <Server className="h-5 w-5" />
          System Health
        </CardTitle>
        <Button variant="ghost" size="icon" onClick={refresh}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {health && Object.entries(health.services).map(([key, service]) => {
          const info = SERVICE_INFO[key as keyof typeof SERVICE_INFO]
          const Icon = info.icon

          return (
            <div
              key={key}
              className="flex items-center justify-between p-2 rounded-lg bg-muted/50"
            >
              <div className="flex items-center gap-3">
                <Icon className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">{info.name}</p>
                  <p className="text-xs text-muted-foreground">{info.description}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {service.latency_ms && (
                  <span className="text-xs text-muted-foreground">
                    {service.latency_ms}ms
                  </span>
                )}
                <Badge variant={service.ok ? 'default' : 'destructive'}>
                  {service.ok ? 'Healthy' : 'Down'}
                </Badge>
              </div>
            </div>
          )
        })}

        {/* Overall Status */}
        {health && (
          <div className="pt-2 border-t">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Total Latency</span>
              <span className="text-sm font-medium">{health.total_latency_ms}ms</span>
            </div>
            <div className="flex items-center justify-between mt-1">
              <span className="text-sm text-muted-foreground">Status</span>
              <Badge
                variant={
                  health.status === 'healthy'
                    ? 'default'
                    : health.status === 'degraded'
                    ? 'secondary'
                    : 'destructive'
                }
              >
                {health.status.charAt(0).toUpperCase() + health.status.slice(1)}
              </Badge>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
```

### 9. Create AnalyticsDashboard Component

Create `frontend/src/components/analytics/AnalyticsDashboard.tsx`:

```tsx
import { StatCard } from './StatCard'
import { UsageChart } from './UsageChart'
import { AgentInsights } from './AgentInsights'
import { SystemHealth } from './SystemHealth'
import { Skeleton } from '@/components/ui/skeleton'
import { useAnalytics } from '@/hooks/useAnalytics'
import { MessageSquare, MessagesSquare, Coins, Timer } from 'lucide-react'

function formatNumber(num: number): string {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
  return num.toString()
}

export function AnalyticsDashboard() {
  const { data, isLoading, error } = useAnalytics()

  if (error) {
    return (
      <div className="p-6">
        <div className="text-center text-destructive">
          <p>Failed to load analytics</p>
          <p className="text-sm text-muted-foreground">{error.message}</p>
        </div>
      </div>
    )
  }

  if (isLoading || !data) {
    return (
      <div className="p-6 space-y-6">
        <h1 className="text-2xl font-bold">Analytics</h1>
        <div className="grid grid-cols-4 gap-4">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
        <div className="grid grid-cols-3 gap-6">
          <Skeleton className="h-[400px] col-span-2" />
          <Skeleton className="h-[400px]" />
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6 overflow-auto h-full">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Analytics</h1>
        <p className="text-sm text-muted-foreground">
          Last 14 days
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="Total Messages"
          value={formatNumber(data.totalMessages)}
          icon={<MessageSquare className="h-4 w-4" />}
        />
        <StatCard
          title="Active Sessions"
          value={data.totalSessions}
          icon={<MessagesSquare className="h-4 w-4" />}
        />
        <StatCard
          title="Tokens Used"
          value={formatNumber(data.totalTokens)}
          icon={<Coins className="h-4 w-4" />}
        />
        <StatCard
          title="Avg Response Time"
          value={`${data.avgResponseTime}ms`}
          icon={<Timer className="h-4 w-4" />}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-3 gap-6">
        <UsageChart data={data.usage} />
        <AgentInsights data={data.agents} />
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-3 gap-6">
        <SystemHealth />
        {/* Future: ModelUsage, RecentErrors components */}
      </div>
    </div>
  )
}
```

### 10. Create Analytics Components Index

Create `frontend/src/components/analytics/index.ts`:

```tsx
export { AnalyticsDashboard } from './AnalyticsDashboard'
export { StatCard } from './StatCard'
export { UsageChart } from './UsageChart'
export { AgentInsights } from './AgentInsights'
export { SystemHealth } from './SystemHealth'
```

### 11. Update AnalyticsPage

Update `frontend/src/pages/AnalyticsPage.tsx`:

```tsx
import { AnalyticsDashboard } from '@/components/analytics'

export function AnalyticsPage() {
  return <AnalyticsDashboard />
}
```

### 12. Update Hooks Index

Update `frontend/src/hooks/index.ts`:

```tsx
export { useModels } from './useModels'
export type { Model } from './useModels'
export { useAgents } from './useAgents'
export type { Agent } from './useAgents'
export { useLLMStatus } from './useLLMStatus'
export type { LLMStatus } from './useLLMStatus'
export { useSessions } from './useSessions'
export type { GroupedSessions } from './useSessions'
export { useKeyboardShortcuts } from './useKeyboardShortcuts'
export { useAnalytics } from './useAnalytics'
export type { AnalyticsData, UsageDataPoint, AgentUsageData, ModelUsageData } from './useAnalytics'
export { useHealth } from './useHealth'
export type { DetailedHealth, ServiceHealth } from './useHealth'
```

---

## Files to Create

- `frontend/src/lib/chart.ts` - Chart.js registration
- `frontend/src/hooks/useAnalytics.ts` - Analytics data hook
- `frontend/src/hooks/useHealth.ts` - Health status hook
- `frontend/src/components/analytics/StatCard.tsx` - Stat display card
- `frontend/src/components/analytics/UsageChart.tsx` - Line chart
- `frontend/src/components/analytics/AgentInsights.tsx` - Doughnut chart
- `frontend/src/components/analytics/SystemHealth.tsx` - Health status
- `frontend/src/components/analytics/AnalyticsDashboard.tsx` - Main dashboard
- `frontend/src/components/analytics/index.ts` - Exports

## Files to Modify

- `frontend/src/pages/AnalyticsPage.tsx` - Use AnalyticsDashboard
- `frontend/src/hooks/index.ts` - Export new hooks
- `frontend/package.json` - Add chart.js (via npm install)

---

## Success Criteria

```bash
# Verify chart.js installed
cd /Users/maxwell/Projects/MAI/frontend
cat package.json | grep -E "(chart.js|react-chartjs-2)"
# Expected: Both packages listed

# Verify analytics components
ls /Users/maxwell/Projects/MAI/frontend/src/components/analytics/
# Expected: StatCard.tsx, UsageChart.tsx, AgentInsights.tsx, SystemHealth.tsx, AnalyticsDashboard.tsx, index.ts

# Verify TypeScript compiles
npm run build 2>&1 | grep -i error
# Expected: No errors

# Verify dev server runs
timeout 10 npm run dev 2>&1 || true
# Expected: Vite server starts
```

**Checklist:**
- [ ] chart.js and react-chartjs-2 installed
- [ ] Chart.js components registered in lib/chart.ts
- [ ] Analytics page shows 4 stat cards at top
- [ ] Usage chart shows line graph with messages and tokens
- [ ] Agent insights shows doughnut chart with usage breakdown
- [ ] System health shows service status with badges
- [ ] Loading state shows skeletons
- [ ] Health status polls and updates automatically
- [ ] Mock data generates reasonable values

---

## Technical Notes

- **Mock Data**: Data is mocked until backend APIs are built (prompts 12-14)
- **Chart Registration**: Must register Chart.js components before use
- **Responsive Charts**: maintainAspectRatio: false with explicit container height
- **Dual Y-Axis**: Usage chart has messages on left, tokens on right
- **Polling**: Health status polls every 10 seconds

---

## On Completion

1. Mark Archon task as `done`
2. Verify ALL success criteria pass
3. Next: 12-sessions-api-backend.md
