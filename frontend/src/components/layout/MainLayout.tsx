import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { Sidebar } from '@/components/sidebar'
import { SettingsDialog } from '@/components/settings'
import { CommandPalette } from '@/components/command'
import { useUIStore } from '@/stores'
import { useKeyboardShortcuts } from '@/hooks'

export function MainLayout() {
  const { sidebarOpen } = useUIStore()

  // Initialize global keyboard shortcuts
  useKeyboardShortcuts()

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} onToggle={() => {}} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>

      {/* Dialogs */}
      <SettingsDialog />
      <CommandPalette />
    </div>
  )
}
