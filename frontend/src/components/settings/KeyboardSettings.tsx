import { useState } from 'react'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { useSettingsStore } from '@/stores'
import { RotateCcw } from 'lucide-react'

type ShortcutAction = 'newChat' | 'commandPalette' | 'toggleSidebar' | 'toggleSplitView' | 'toggleSettings' | 'focusInput' | 'sendMessage'

const SHORTCUT_ACTIONS: ShortcutAction[] = [
  'newChat',
  'commandPalette',
  'toggleSidebar',
  'toggleSplitView',
  'toggleSettings',
  'focusInput',
  'sendMessage',
]

const SHORTCUT_LABELS: Record<ShortcutAction, string> = {
  newChat: 'New Chat',
  commandPalette: 'Command Palette',
  toggleSidebar: 'Toggle Sidebar',
  toggleSplitView: 'Toggle Split View',
  toggleSettings: 'Open Settings',
  focusInput: 'Focus Input',
  sendMessage: 'Send Message',
}

export function KeyboardSettings() {
  const { vimMode, toggleVimMode, keyboardShortcuts, updateShortcut, resetToDefaults } = useSettingsStore()
  const [recording, setRecording] = useState<ShortcutAction | null>(null)

  const handleKeyDown = (action: ShortcutAction) => (e: React.KeyboardEvent) => {
    e.preventDefault()
    e.stopPropagation()

    const parts: string[] = []
    if (e.metaKey) parts.push('Cmd')
    if (e.ctrlKey) parts.push('Ctrl')
    if (e.altKey) parts.push('Alt')
    if (e.shiftKey) parts.push('Shift')

    // Add the actual key
    if (e.key !== 'Meta' && e.key !== 'Control' && e.key !== 'Alt' && e.key !== 'Shift') {
      const key = e.key.length === 1 ? e.key.toUpperCase() : e.key
      parts.push(key)
    }

    if (parts.length > 0 && parts[parts.length - 1] !== 'Cmd') {
      updateShortcut(action, parts.join('+'))
      setRecording(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* Vim Mode */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <Label>Vim Mode</Label>
          <p className="text-sm text-muted-foreground">
            Use j/k navigation, i for input mode, etc.
          </p>
        </div>
        <Switch checked={vimMode} onCheckedChange={toggleVimMode} />
      </div>

      <Separator />

      {/* Keyboard Shortcuts */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <Label>Keyboard Shortcuts</Label>
            <p className="text-sm text-muted-foreground">
              Click to customize a shortcut
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={resetToDefaults}>
            <RotateCcw className="h-4 w-4 mr-2" />
            Reset
          </Button>
        </div>

        <div className="space-y-2">
          {SHORTCUT_ACTIONS.map((action) => {
            const currentKey = keyboardShortcuts[action]
            const isRecording = recording === action

            return (
              <div
                key={action}
                className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-muted"
              >
                <span className="text-sm">{SHORTCUT_LABELS[action]}</span>
                <button
                  className={`px-3 py-1.5 rounded border text-sm font-mono min-w-[80px] text-center ${
                    isRecording
                      ? 'border-primary bg-primary/10 animate-pulse'
                      : 'border-border bg-muted hover:bg-background'
                  }`}
                  onClick={() => setRecording(isRecording ? null : action)}
                  onKeyDown={isRecording ? handleKeyDown(action) : undefined}
                  onBlur={() => setRecording(null)}
                >
                  {isRecording ? 'Press keys...' : currentKey}
                </button>
              </div>
            )
          })}
        </div>
      </div>

      {/* Vim Mode Help */}
      {vimMode && (
        <>
          <Separator />
          <div className="space-y-2">
            <Label>Vim Bindings</Label>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="flex justify-between p-2 rounded bg-muted">
                <span className="text-muted-foreground">Navigate down</span>
                <kbd className="font-mono">j</kbd>
              </div>
              <div className="flex justify-between p-2 rounded bg-muted">
                <span className="text-muted-foreground">Navigate up</span>
                <kbd className="font-mono">k</kbd>
              </div>
              <div className="flex justify-between p-2 rounded bg-muted">
                <span className="text-muted-foreground">Focus input</span>
                <kbd className="font-mono">i</kbd>
              </div>
              <div className="flex justify-between p-2 rounded bg-muted">
                <span className="text-muted-foreground">Search</span>
                <kbd className="font-mono">/</kbd>
              </div>
              <div className="flex justify-between p-2 rounded bg-muted">
                <span className="text-muted-foreground">Exit input</span>
                <kbd className="font-mono">Esc</kbd>
              </div>
              <div className="flex justify-between p-2 rounded bg-muted">
                <span className="text-muted-foreground">Go to top</span>
                <kbd className="font-mono">gg</kbd>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
