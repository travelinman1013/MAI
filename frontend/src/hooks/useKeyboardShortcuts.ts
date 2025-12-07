import { useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUIStore, useSettingsStore, useChatStore } from '@/stores'

export function useKeyboardShortcuts() {
  const navigate = useNavigate()
  const { toggleSidebar, toggleCommandPalette, toggleSettings, toggleSplitView } = useUIStore()
  const { keyboardShortcuts, vimMode } = useSettingsStore()
  const createSession = useChatStore(state => state.createSession)

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    // Don't trigger shortcuts when typing in inputs
    const target = e.target as HTMLElement
    const isInput = target.tagName === 'INPUT' ||
                    target.tagName === 'TEXTAREA' ||
                    target.isContentEditable

    // Build key string
    const parts: string[] = []
    if (e.metaKey) parts.push('Cmd')
    if (e.ctrlKey && !e.metaKey) parts.push('Ctrl')
    if (e.altKey) parts.push('Alt')
    if (e.shiftKey) parts.push('Shift')

    const key = e.key.length === 1 ? e.key.toUpperCase() : e.key
    parts.push(key)
    const keyCombo = parts.join('+')

    // Check against stored shortcuts
    const actions: Record<string, () => void> = {
      newChat: () => {
        const newId = createSession()
        navigate(`/chat/${newId}`)
      },
      commandPalette: toggleCommandPalette,
      toggleSidebar: toggleSidebar,
      toggleSplitView: toggleSplitView,
      toggleSettings: toggleSettings,
    }

    for (const [action, shortcut] of Object.entries(keyboardShortcuts)) {
      if (keyCombo === shortcut && actions[action]) {
        // Allow command palette shortcut even in inputs
        if (action === 'commandPalette' || !isInput) {
          e.preventDefault()
          actions[action]()
          return
        }
      }
    }

    // Vim mode shortcuts (only when not in input)
    if (vimMode && !isInput) {
      handleVimShortcut(e)
    }
  }, [keyboardShortcuts, vimMode, navigate, createSession, toggleCommandPalette, toggleSidebar, toggleSplitView, toggleSettings])

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
}

function handleVimShortcut(e: KeyboardEvent) {
  switch (e.key) {
    case 'j':
      // Navigate to next session
      console.log('Vim: navigate down')
      break
    case 'k':
      // Navigate to previous session
      console.log('Vim: navigate up')
      break
    case 'i':
      // Focus input
      const input = document.querySelector('textarea') as HTMLTextAreaElement
      if (input) {
        input.focus()
      }
      break
    case '/':
      // Focus search
      const search = document.querySelector('[placeholder*="Search"]') as HTMLInputElement
      if (search) {
        e.preventDefault()
        search.focus()
      }
      break
  }
}
