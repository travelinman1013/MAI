import { MessageSquare, Plus, Settings, PanelLeftClose, PanelLeft } from 'lucide-react'

interface SidebarProps {
  isOpen: boolean
  onToggle: () => void
}

export default function Sidebar({ isOpen, onToggle }: SidebarProps) {
  return (
    <>
      {/* Toggle button when closed */}
      {!isOpen && (
        <button
          onClick={onToggle}
          className="absolute top-4 left-4 z-10 p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors"
        >
          <PanelLeft className="h-5 w-5" />
        </button>
      )}

      {/* Sidebar */}
      <aside
        className={`${
          isOpen ? 'w-64' : 'w-0'
        } bg-gray-950 border-r border-gray-800 flex flex-col transition-all duration-300 overflow-hidden`}
      >
        <div className="flex-1 flex flex-col min-w-[16rem]">
          {/* Header */}
          <div className="p-4 flex items-center justify-between border-b border-gray-800">
            <h1 className="font-semibold text-lg">MAI</h1>
            <button
              onClick={onToggle}
              className="p-1.5 rounded-lg hover:bg-gray-800 transition-colors"
            >
              <PanelLeftClose className="h-5 w-5" />
            </button>
          </div>

          {/* New Chat Button */}
          <div className="p-3">
            <button className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-700 hover:bg-gray-800 transition-colors text-sm">
              <Plus className="h-4 w-4" />
              New Chat
            </button>
          </div>

          {/* Chat History */}
          <div className="flex-1 overflow-y-auto px-3">
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-2 px-2">
              Recent
            </div>
            {/* Placeholder for chat history */}
            <div className="space-y-1">
              <button className="w-full flex items-center gap-2 px-2 py-2 rounded-lg hover:bg-gray-800 transition-colors text-sm text-left truncate">
                <MessageSquare className="h-4 w-4 flex-shrink-0" />
                <span className="truncate">New conversation</span>
              </button>
            </div>
          </div>

          {/* Footer */}
          <div className="p-3 border-t border-gray-800">
            <button className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-800 transition-colors text-sm">
              <Settings className="h-4 w-4" />
              Settings
            </button>
          </div>
        </div>
      </aside>
    </>
  )
}
