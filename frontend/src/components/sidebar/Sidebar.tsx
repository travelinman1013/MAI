import { Plus, Settings, BarChart3, PanelLeftClose, PanelLeft } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { SessionSearch } from './SessionSearch'
import { SessionList } from './SessionList'
import { useSessions } from '@/hooks/useSessions'

interface SidebarProps {
  isOpen: boolean
  onToggle: () => void
}

export function Sidebar({ isOpen, onToggle }: SidebarProps) {
  const {
    groupedSessions,
    searchQuery,
    setSearchQuery,
    activeSessionId,
    createSession,
    deleteSession,
    renameSession,
    setActiveSession,
  } = useSessions()

  const handleNewChat = () => {
    createSession()
  }

  return (
    <>
      {/* Toggle button when closed */}
      {!isOpen && (
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggle}
          className="absolute top-4 left-4 z-10"
        >
          <PanelLeft className="h-5 w-5" />
          <span className="sr-only">Open sidebar</span>
        </Button>
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'bg-card border-r border-border flex flex-col transition-all duration-300 overflow-hidden',
          isOpen ? 'w-64' : 'w-0'
        )}
      >
        <div className="flex-1 flex flex-col min-w-[16rem]">
          {/* Header */}
          <div className="p-3 flex items-center justify-between border-b border-border">
            <h1 className="font-semibold text-lg">MAI</h1>
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggle}
              className="h-8 w-8"
            >
              <PanelLeftClose className="h-5 w-5" />
              <span className="sr-only">Close sidebar</span>
            </Button>
          </div>

          {/* New Chat Button */}
          <div className="p-3">
            <Button
              variant="outline"
              className="w-full justify-start gap-2"
              onClick={handleNewChat}
            >
              <Plus className="h-4 w-4" />
              New Chat
            </Button>
          </div>

          {/* Search */}
          <div className="px-3 pb-2">
            <SessionSearch
              value={searchQuery}
              onChange={setSearchQuery}
            />
          </div>

          <Separator />

          {/* Session List with Scroll Area */}
          <ScrollArea className="flex-1">
            <SessionList
              groups={groupedSessions}
              activeSessionId={activeSessionId}
              onSelectSession={setActiveSession}
              onRenameSession={renameSession}
              onDeleteSession={deleteSession}
            />
          </ScrollArea>

          {/* Footer Navigation */}
          <div className="border-t border-border p-2 space-y-1">
            <Button
              variant="ghost"
              className="w-full justify-start gap-2 h-9"
            >
              <BarChart3 className="h-4 w-4" />
              Analytics
            </Button>
            <Button
              variant="ghost"
              className="w-full justify-start gap-2 h-9"
            >
              <Settings className="h-4 w-4" />
              Settings
            </Button>
          </div>
        </div>
      </aside>
    </>
  )
}

export default Sidebar
