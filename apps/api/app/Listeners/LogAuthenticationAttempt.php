<?php

namespace App\Listeners;

use App\Models\User;
use Illuminate\Auth\Events\Login;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Laravel\Fortify\Events\TwoFactorAuthenticationFailed;

/**
 * threat-model-identity-access.md T-10: cada tentativa de login (sucesso ou
 * falha) fica auditada. audit_logs (tabela dedicada, append-only) fica para
 * o M05 (Agent Framework); por agora, logs estruturados sem dados sensíveis
 * (nunca o código TOTP, a assertion WebAuthn, nem o código de recuperação).
 */
class LogAuthenticationAttempt
{
    public function handleLogin(Login $event): void
    {
        /** @var User $user */
        $user = $event->user;
        $request = request();

        Log::info('auth.login.succeeded', [
            'actor_id' => $user->getKey(),
            'method' => $this->method(),
            'trace_id' => $request->header('traceparent'),
        ]);

        // T-12: o login conta como "confirmação" recente para o middleware
        // password.confirm (gestão de credenciais, ≤ auth.password_timeout).
        // Sobrevive ao regenerate() que vem a seguir (migra os dados).
        // Um re-login por cookie de "remember me" ($event->remember) não é uma
        // autenticação recente: nunca conta como confirmação.
        if ($request->hasSession() && ! $event->remember) {
            $request->session()->passwordConfirmed();
        }

        // O login regenera o ID de sessão (T-07) depois deste evento, e o
        // driver "database" só persiste a linha no fim do pedido. Adia para
        // app()->terminating(), já com o ID final e a linha escrita.
        app()->terminating(function () {
            DB::table('sessions')
                ->where('id', session()->getId())
                ->update(['last_authenticated_at' => now()]);
        });
    }

    public function handleTwoFactorFailed(TwoFactorAuthenticationFailed $event): void
    {
        Log::warning('auth.login.failed', [
            'actor_id' => $event->user->getKey(),
            'method' => 'totp',
            'trace_id' => request()->header('traceparent'),
        ]);
    }

    /**
     * SPEC-002 §5: method ∈ passkey | totp | recovery_code. Deriva da rota
     * que autenticou, nunca de input do cliente sem validação.
     */
    private function method(): string
    {
        $request = request();

        return match (true) {
            $request->routeIs('passkey.login') => 'passkey',
            $request->routeIs('login.totp') => $request->filled('recovery_code') ? 'recovery_code' : 'totp',
            default => 'other',
        };
    }
}
