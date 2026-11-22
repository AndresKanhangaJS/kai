<?php

namespace App\Listeners;

use Illuminate\Contracts\Auth\Authenticatable;
use Illuminate\Support\Facades\Log;
use Laravel\Fortify\Events\RecoveryCodesGenerated;
use Laravel\Fortify\Events\TwoFactorAuthenticationConfirmed;
use Laravel\Fortify\Events\TwoFactorAuthenticationDisabled;
use Laravel\Fortify\Events\TwoFactorAuthenticationEnabled;
use Laravel\Passkeys\Events\PasskeyDeleted;
use Laravel\Passkeys\Events\PasskeyRegistered;

/**
 * threat-model-identity-access.md T-12 (revisão de segurança da E4.6b): toda
 * a alteração de credenciais fica auditada, com a origem (cli/http). Sem
 * segredos: nunca o segredo TOTP, os códigos de recuperação nem a credencial
 * WebAuthn — só IDs.
 */
class LogCredentialChange
{
    public function handlePasskeyRegistered(PasskeyRegistered $event): void
    {
        $this->log('auth.credential.passkey_registered', $event->user, ['passkey_id' => $event->passkey->getKey()]);
    }

    public function handlePasskeyDeleted(PasskeyDeleted $event): void
    {
        $this->log('auth.credential.passkey_deleted', $event->user, ['passkey_id' => $event->passkey->getKey()]);
    }

    public function handleTotpEnabled(TwoFactorAuthenticationEnabled $event): void
    {
        $this->log('auth.credential.totp_enabled', $event->user);
    }

    public function handleTotpConfirmed(TwoFactorAuthenticationConfirmed $event): void
    {
        $this->log('auth.credential.totp_confirmed', $event->user);
    }

    public function handleTotpDisabled(TwoFactorAuthenticationDisabled $event): void
    {
        $this->log('auth.credential.totp_disabled', $event->user);
    }

    public function handleRecoveryCodesGenerated(RecoveryCodesGenerated $event): void
    {
        $this->log('auth.credential.recovery_codes_generated', $event->user);
    }

    /**
     * @param  array<string, mixed>  $extra
     */
    private function log(string $event, Authenticatable $user, array $extra = []): void
    {
        $request = request();

        Log::info($event, [
            'actor_id' => $user->getAuthIdentifier(),
            // Sem rota resolvida, a alteração veio da CLI (ex.: kai:enable-totp).
            'source' => $request->route() === null ? 'cli' : 'http',
            'trace_id' => $request->header('traceparent'),
            ...$extra,
        ]);
    }
}
