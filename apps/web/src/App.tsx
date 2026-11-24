import { useState } from 'react'
import './App.css'
import { logout } from './api'
import { ChatPage } from './chat/ChatPage'
import { ErrorBoundary } from './ErrorBoundary'
import { LoginPage } from './LoginPage'
import { SessionsPage } from './SessionsPage'

type View = 'chat' | 'sessions'

function App() {
  const [loggedIn, setLoggedIn] = useState(false)
  const [view, setView] = useState<View>('chat')
  const [logoutError, setLogoutError] = useState<string | null>(null)
  // Muda a chave para remontar o chat depois de um erro de render.
  const [chatKey, setChatKey] = useState(0)

  if (!loggedIn) {
    return (
      <LoginPage
        onLoggedIn={() => {
          setView('chat')
          setLogoutError(null)
          setLoggedIn(true)
        }}
      />
    )
  }

  async function handleLogout() {
    setLogoutError(null)
    try {
      await logout()
    } catch {
      // A sessão pode continuar válida no servidor: nunca fingir que saiu (revisão do E5.0).
      setLogoutError('Não foi possível terminar a sessão. Tenta outra vez.')
      return
    }
    setLoggedIn(false)
  }

  return (
    <div className="app-shell">
      <nav className="app-nav" aria-label="Principal">
        <span className="app-brand">KAI</span>
        <button
          type="button"
          className="nav-item"
          aria-current={view === 'chat' ? 'page' : undefined}
          onClick={() => setView('chat')}
        >
          Conversa
        </button>
        <button
          type="button"
          className="nav-item"
          aria-current={view === 'sessions' ? 'page' : undefined}
          onClick={() => setView('sessions')}
        >
          Sessões
        </button>
        <button type="button" className="btn-link nav-logout" onClick={handleLogout}>
          Terminar sessão
        </button>
      </nav>
      {logoutError && (
        <p role="alert" className="auth-error app-alert">
          {logoutError}
        </p>
      )}
      {view === 'chat' ? (
        <ErrorBoundary key={chatKey} onReset={() => setChatKey((k) => k + 1)}>
          <ChatPage />
        </ErrorBoundary>
      ) : (
        <SessionsPage onLoggedOut={() => setLoggedIn(false)} />
      )}
    </div>
  )
}

export default App
