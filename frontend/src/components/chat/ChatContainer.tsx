import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import { ChatPanel } from './ChatPanel'
import { useUIStore, useChatStore } from '@/stores'

export function ChatContainer() {
  const { splitViewEnabled, secondarySessionId } = useUIStore()
  const { activeSessionId } = useChatStore()

  if (!activeSessionId) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        <p>No chat selected. Create a new chat to get started.</p>
      </div>
    )
  }

  return (
    <PanelGroup direction="horizontal" className="h-full">
      <Panel defaultSize={splitViewEnabled ? 50 : 100} minSize={30}>
        <ChatPanel sessionId={activeSessionId} isPrimary />
      </Panel>

      {splitViewEnabled && secondarySessionId && (
        <>
          <PanelResizeHandle className="w-1 bg-border hover:bg-primary/50 transition-colors" />
          <Panel defaultSize={50} minSize={30}>
            <ChatPanel sessionId={secondarySessionId} isPrimary={false} />
          </Panel>
        </>
      )}
    </PanelGroup>
  )
}
