import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Command } from 'cmdk'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { useChatStore, useUIStore, useSettingsStore } from '@/stores'
import { useSessions } from '@/hooks/useSessions'
import {
  Plus,
  MessageSquare,
  BarChart3,
  Settings,
  Sun,
  Moon,
  Monitor,
  PanelLeft,
  Columns,
  Search,
} from 'lucide-react'

export function CommandPalette() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')

  const { commandPaletteOpen, toggleCommandPalette, toggleSidebar, toggleSplitView, toggleSettings } = useUIStore()
  const { theme, setTheme } = useSettingsStore()
  const { sessions, createSession } = useSessions()
  const setActiveSession = useChatStore(state => state.setActiveSession)

  // Keyboard shortcut to open
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        toggleCommandPalette()
      }
    }
    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [toggleCommandPalette])

  const runCommand = useCallback((command: () => void) => {
    toggleCommandPalette()
    command()
  }, [toggleCommandPalette])

  const handleNewChat = () => {
    const newId = createSession()
    navigate(`/chat/${newId}`)
  }

  const handleOpenSession = (sessionId: string) => {
    setActiveSession(sessionId)
    navigate(`/chat/${sessionId}`)
  }

  // Reset search when closing
  useEffect(() => {
    if (!commandPaletteOpen) {
      setSearch('')
    }
  }, [commandPaletteOpen])

  return (
    <Dialog open={commandPaletteOpen} onOpenChange={toggleCommandPalette}>
      <DialogContent className="p-0 max-w-lg overflow-hidden">
        <Command className="rounded-lg border-0 shadow-none" loop>
          <div className="flex items-center border-b px-3">
            <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
            <Command.Input
              value={search}
              onValueChange={setSearch}
              placeholder="Type a command or search..."
              className="flex h-12 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>
          <Command.List className="max-h-[400px] overflow-y-auto p-2">
            <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
              No results found.
            </Command.Empty>

            {/* Actions Group */}
            <Command.Group heading="Actions">
              <CommandItem
                icon={Plus}
                onSelect={() => runCommand(handleNewChat)}
              >
                New Chat
              </CommandItem>
              <CommandItem
                icon={BarChart3}
                onSelect={() => runCommand(() => navigate('/analytics'))}
              >
                Analytics Dashboard
              </CommandItem>
              <CommandItem
                icon={Settings}
                onSelect={() => runCommand(toggleSettings)}
              >
                Settings
              </CommandItem>
              <CommandItem
                icon={PanelLeft}
                onSelect={() => runCommand(toggleSidebar)}
              >
                Toggle Sidebar
              </CommandItem>
              <CommandItem
                icon={Columns}
                onSelect={() => runCommand(toggleSplitView)}
              >
                Toggle Split View
              </CommandItem>
            </Command.Group>

            {/* Theme Group */}
            <Command.Group heading="Theme">
              <CommandItem
                icon={Sun}
                onSelect={() => runCommand(() => setTheme('light'))}
              >
                Light Mode
                {theme === 'light' && <span className="ml-auto text-xs text-primary">Active</span>}
              </CommandItem>
              <CommandItem
                icon={Moon}
                onSelect={() => runCommand(() => setTheme('dark'))}
              >
                Dark Mode
                {theme === 'dark' && <span className="ml-auto text-xs text-primary">Active</span>}
              </CommandItem>
              <CommandItem
                icon={Monitor}
                onSelect={() => runCommand(() => setTheme('system'))}
              >
                System Theme
                {theme === 'system' && <span className="ml-auto text-xs text-primary">Active</span>}
              </CommandItem>
            </Command.Group>

            {/* Recent Chats Group */}
            {sessions.length > 0 && (
              <Command.Group heading="Recent Chats">
                {sessions.slice(0, 5).map(session => (
                  <CommandItem
                    key={session.id}
                    icon={MessageSquare}
                    onSelect={() => runCommand(() => handleOpenSession(session.id))}
                  >
                    {session.title}
                  </CommandItem>
                ))}
              </Command.Group>
            )}

            {/* Keyboard Shortcuts */}
            <Command.Group heading="Keyboard Shortcuts">
              <div className="px-2 py-3 text-xs text-muted-foreground space-y-1">
                <div className="flex justify-between">
                  <span>New Chat</span>
                  <kbd className="px-1.5 py-0.5 bg-muted rounded">Ctrl+N</kbd>
                </div>
                <div className="flex justify-between">
                  <span>Toggle Sidebar</span>
                  <kbd className="px-1.5 py-0.5 bg-muted rounded">Cmd+B</kbd>
                </div>
                <div className="flex justify-between">
                  <span>Settings</span>
                  <kbd className="px-1.5 py-0.5 bg-muted rounded">Cmd+,</kbd>
                </div>
              </div>
            </Command.Group>
          </Command.List>
        </Command>
      </DialogContent>
    </Dialog>
  )
}

// Helper component for command items
interface CommandItemProps {
  icon: React.ComponentType<{ className?: string }>
  onSelect: () => void
  children: React.ReactNode
}

function CommandItem({ icon: Icon, onSelect, children }: CommandItemProps) {
  return (
    <Command.Item
      onSelect={onSelect}
      className="flex items-center gap-2 px-2 py-2 text-sm rounded-md cursor-pointer aria-selected:bg-accent aria-selected:text-accent-foreground"
    >
      <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
      <span className="flex-1">{children}</span>
    </Command.Item>
  )
}
