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
