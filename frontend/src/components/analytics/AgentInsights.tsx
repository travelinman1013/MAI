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
