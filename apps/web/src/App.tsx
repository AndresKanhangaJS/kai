import { useState } from 'react'
import './App.css'
import { LoginPage } from './LoginPage'
import { SessionsPage } from './SessionsPage'

function App() {
  const [loggedIn, setLoggedIn] = useState(false)

  if (!loggedIn) {
    return <LoginPage onLoggedIn={() => setLoggedIn(true)} />
  }

  return <SessionsPage onLoggedOut={() => setLoggedIn(false)} />
}

export default App
