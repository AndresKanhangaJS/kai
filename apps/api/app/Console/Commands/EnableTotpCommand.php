<?php

namespace App\Console\Commands;

use App\Models\User;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Laravel\Fortify\Actions\EnableTwoFactorAuthentication;

/**
 * SPEC-002 / E4.6b: o owner é criado por CLI sem credencial (D-05); este
 * comando activa o TOTP. Quem tem acesso à CLI é o operador de confiança
 * (mesmo nível que kai:create-owner), por isso o TOTP fica já confirmado.
 *
 * O segredo e os códigos de recuperação são mostrados uma única vez no
 * terminal e nunca vão para logs (security.md). A activação fica auditada
 * (LogCredentialChange, via TwoFactorAuthenticationEnabled do Fortify).
 *
 * --force é a resposta a um incidente (threat-model T-12): roda o segredo e
 * revoga todas as sessões do utilizador; --revoke-passkeys remove também as
 * passkeys registadas (uma delas pode ser do atacante).
 */
class EnableTotpCommand extends Command
{
    protected $signature = 'kai:enable-totp {email}
        {--force : Roda um segredo TOTP já activo (o anterior deixa de funcionar) e revoga todas as sessões do utilizador}
        {--revoke-passkeys : Com --force, remove também todas as passkeys do utilizador}';

    protected $description = 'Activa o TOTP do owner e mostra o segredo e os códigos de recuperação uma única vez';

    public function handle(EnableTwoFactorAuthentication $enable): int
    {
        $user = User::query()->where('email', $this->argument('email'))->first();

        if ($user === null) {
            $this->error('Utilizador não encontrado.');

            return self::FAILURE;
        }

        $rotating = $user->two_factor_secret !== null;

        if ($rotating && ! $this->option('force')) {
            $this->error('O TOTP já está activo para este utilizador. Usa --force para gerar um segredo novo (o anterior deixa de funcionar e todas as sessões são revogadas).');

            return self::FAILURE;
        }

        if ($this->option('revoke-passkeys') && ! $this->option('force')) {
            $this->error('--revoke-passkeys só se usa com --force.');

            return self::FAILURE;
        }

        DB::transaction(function () use ($enable, $user) {
            $enable($user, force: true);
            $user->forceFill(['two_factor_confirmed_at' => now()])->save();

            if ($this->option('force')) {
                $sessions = DB::table('sessions')->where('user_id', $user->getKey())->delete();
                $this->info("Sessões revogadas: {$sessions}.");
                // Deletes em massa não disparam eventos: audita explicitamente
                // (parte forense da resposta a incidente, T-12).
                Log::info('auth.credential.sessions_revoked', [
                    'actor_id' => $user->getKey(), 'source' => 'cli', 'count' => $sessions,
                ]);
            }

            if ($this->option('revoke-passkeys')) {
                $passkeys = $user->passkeys()->delete();
                $this->info("Passkeys removidas: {$passkeys}.");
                Log::info('auth.credential.passkeys_revoked', [
                    'actor_id' => $user->getKey(), 'source' => 'cli', 'count' => $passkeys,
                ]);
            }
        });

        $this->warn('Guarda isto agora: não volta a ser mostrado.');
        $this->newLine();
        $this->line('URI para a app autenticadora:');
        $this->line($user->twoFactorQrCodeUrl());
        $this->newLine();
        $this->line('Códigos de recuperação (uso único):');
        foreach ($user->recoveryCodes() as $code) {
            $this->line("  {$code}");
        }

        return self::SUCCESS;
    }
}
