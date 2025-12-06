import { useState } from 'react'
import Chat from './components/Chat'
import Sidebar from './components/Sidebar'

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <div className="flex h-screen bg-gray-900">
      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <Chat />
      </main>
    </div>
  )
}

export default App
