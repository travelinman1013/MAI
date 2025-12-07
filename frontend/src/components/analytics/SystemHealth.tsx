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
