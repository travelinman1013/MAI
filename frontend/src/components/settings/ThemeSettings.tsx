import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { useSettingsStore } from '@/stores'
import { Sun, Moon, Monitor } from 'lucide-react'
import { cn } from '@/lib/utils'

const THEMES = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
] as const

export function ThemeSettings() {
  const { theme, setTheme, fontSize, setFontSize } = useSettingsStore()

  return (
    <div className="space-y-6">
      {/* Theme Selection */}
      <div className="space-y-2">
        <Label>Theme</Label>
        <p className="text-sm text-muted-foreground">
          Choose your preferred color scheme
        </p>
        <div className="grid grid-cols-3 gap-2 mt-2">
          {THEMES.map(t => {
            const Icon = t.icon
            const isActive = theme === t.value

            return (
              <Button
                key={t.value}
                variant={isActive ? 'default' : 'outline'}
                className={cn(
                  'flex flex-col items-center gap-2 h-auto py-4',
                  isActive && 'border-primary'
                )}
                onClick={() => setTheme(t.value)}
              >
                <Icon className="h-5 w-5" />
                <span className="text-xs">{t.label}</span>
              </Button>
            )
          })}
        </div>
      </div>

      {/* Font Size */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>Font Size</Label>
          <span className="text-sm text-muted-foreground">{fontSize}px</span>
        </div>
        <p className="text-sm text-muted-foreground">
          Adjust the base font size for the interface
        </p>
        <Slider
          value={[fontSize]}
          onValueChange={([value]) => setFontSize(value)}
          min={12}
          max={20}
          step={1}
          className="mt-4"
        />
        <div className="flex justify-between text-xs text-muted-foreground mt-1">
          <span>Small</span>
          <span>Large</span>
        </div>
      </div>

      {/* Preview */}
      <div className="space-y-2">
        <Label>Preview</Label>
        <div
          className="p-4 border rounded-lg bg-muted"
          style={{ fontSize: `${fontSize}px` }}
        >
          <p>This is how text will appear in the chat.</p>
          <p className="text-muted-foreground text-sm mt-1">
            Secondary text uses a smaller size.
          </p>
        </div>
      </div>
    </div>
  )
}
