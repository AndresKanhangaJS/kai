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

        Log::info('auth.login.succeeded', [
            'actor_id' => $user->getKey(),
            'trace_id' => request()->header('traceparent'),
        ]);

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
}
