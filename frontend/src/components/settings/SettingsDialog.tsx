import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { APISettings } from './APISettings'
import { ModelSettings } from './ModelSettings'
import { ThemeSettings } from './ThemeSettings'
import { KeyboardSettings } from './KeyboardSettings'
import { useUIStore } from '@/stores'
import { Settings, Brain, Palette, Keyboard } from 'lucide-react'

export function SettingsDialog() {
  const { settingsOpen, toggleSettings } = useUIStore()

  return (
    <Dialog open={settingsOpen} onOpenChange={toggleSettings}>
      <DialogContent className="max-w-2xl h-[80vh] flex flex-col p-0">
        <DialogHeader className="px-6 py-4 border-b">
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Settings
          </DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="general" className="flex-1 flex flex-col overflow-hidden">
          <TabsList className="grid grid-cols-4 mx-6 mt-2">
            <TabsTrigger value="general" className="gap-2">
              <Settings className="h-4 w-4" />
              <span className="hidden sm:inline">General</span>
            </TabsTrigger>
            <TabsTrigger value="models" className="gap-2">
              <Brain className="h-4 w-4" />
              <span className="hidden sm:inline">Models</span>
            </TabsTrigger>
            <TabsTrigger value="theme" className="gap-2">
              <Palette className="h-4 w-4" />
              <span className="hidden sm:inline">Theme</span>
            </TabsTrigger>
            <TabsTrigger value="shortcuts" className="gap-2">
              <Keyboard className="h-4 w-4" />
              <span className="hidden sm:inline">Shortcuts</span>
            </TabsTrigger>
          </TabsList>

          <ScrollArea className="flex-1 px-6 py-4">
            <TabsContent value="general" className="mt-0">
              <APISettings />
            </TabsContent>
            <TabsContent value="models" className="mt-0">
              <ModelSettings />
            </TabsContent>
            <TabsContent value="theme" className="mt-0">
              <ThemeSettings />
            </TabsContent>
            <TabsContent value="shortcuts" className="mt-0">
              <KeyboardSettings />
            </TabsContent>
          </ScrollArea>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
