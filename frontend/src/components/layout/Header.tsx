import { PanelLeft, Command, Sun, Moon, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ModelSelector, LLMStatusBadge } from '@/components/chat'
import { useUIStore, useSettingsStore } from '@/stores'

export function Header() {
  const { toggleSidebar, toggleCommandPalette, toggleSettings } = useUIStore()
  const { theme, setTheme } = useSettingsStore()

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark')
  }

  return (
    <header className="h-14 border-b border-border flex items-center px-4 gap-2 bg-background">
      {/* Sidebar Toggle */}
      <Button variant="ghost" size="icon" onClick={toggleSidebar}>
        <PanelLeft className="h-5 w-5" />
      </Button>

      {/* Model Selector */}
      <ModelSelector />

      {/* LLM Status */}
      <LLMStatusBadge />

      {/* Spacer */}
      <div className="flex-1" />

      {/* Command Palette Button */}
      <Button
        variant="outline"
        size="sm"
        className="gap-2 text-muted-foreground"
        onClick={toggleCommandPalette}
      >
        <Command className="h-4 w-4" />
        <span className="hidden sm:inline">Command</span>
        <kbd className="hidden sm:inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium">
          <span className="text-xs">Cmd</span>K
        </kbd>
      </Button>

      {/* Theme Toggle */}
      <Button variant="ghost" size="icon" onClick={toggleTheme}>
        {theme === 'dark' ? (
          <Sun className="h-5 w-5" />
        ) : (
          <Moon className="h-5 w-5" />
        )}
      </Button>

      {/* Settings */}
      <Button variant="ghost" size="icon" onClick={toggleSettings}>
        <Settings className="h-5 w-5" />
      </Button>
    </header>
  )
}
