import { Component, type ReactNode } from 'react'

// Um erro de render num ecrã não pode deixar a aplicação inteira em branco, sem navegação
// nem "Terminar sessão" (revisão de segurança do E5.0). Nunca mostra detalhes técnicos.

type Props = { children: ReactNode; onReset?: () => void }

export class ErrorBoundary extends Component<Props, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <main className="chat-page">
        <p role="alert" className="auth-error">
          Este ecrã encontrou um erro inesperado.
        </p>
        <button
          type="button"
          className="btn-secondary"
          onClick={() => {
            this.setState({ failed: false })
            this.props.onReset?.()
          }}
        >
          Recomeçar
        </button>
      </main>
    )
  }
}
