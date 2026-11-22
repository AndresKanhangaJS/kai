<?php

namespace Tests\Feature\Auth;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Laravel\Fortify\Fortify;
use Laravel\Passkeys\Events\PasskeyDeleted;
use Laravel\Passkeys\Events\PasskeyRegistered;
use Laravel\Passkeys\Passkey;
use Mockery;
use PragmaRX\Google2FA\Google2FA;
use Tests\TestCase;

/**
 * threat-model-identity-access.md T-10 e T-12 (revisão de segurança da E4.6b):
 * cada login regista o método, e cada alteração de credenciais fica auditada
 * (origem cli/http), sempre sem segredos.
 */
class CredentialAuditTest extends TestCase
{
    use RefreshDatabase;

    /** @return array{0: User, 1: string} */
    private function userWithTotp(): array
    {
        $secret = app(Google2FA::class)->generateSecretKey();
        $user = User::factory()->create([
            'password' => null,
            'two_factor_secret' => Fortify::currentEncrypter()->encrypt($secret),
            'two_factor_recovery_codes' => Fortify::currentEncrypter()->encrypt(json_encode(['abc-123-def'])),
            'two_factor_confirmed_at' => now(),
        ]);

        return [$user, $secret];
    }

    private function passkeyFor(User $user): Passkey
    {
        $id = DB::table('passkeys')->insertGetId([
            'user_id' => $user->id, 'name' => 'Teste', 'credential_id' => 'cred-'.uniqid(),
            'credential' => '{}', 'created_at' => now(), 'updated_at' => now(),
        ]);

        return Passkey::query()->findOrFail($id);
    }

    public function test_a_totp_login_logs_the_method(): void
    {
        $log = Log::spy();
        [$user, $secret] = $this->userWithTotp();

        $this->postJson('/login/totp', [
            'email' => $user->email,
            'code' => app(Google2FA::class)->getCurrentOtp($secret),
        ])->assertSuccessful();

        $log->shouldHaveReceived('info')->with('auth.login.succeeded', Mockery::on(
            fn (array $context) => $context['method'] === 'totp' && $context['actor_id'] === $user->id
        ))->once();
    }

    public function test_a_recovery_code_login_logs_the_method_without_the_code(): void
    {
        $log = Log::spy();
        [$user] = $this->userWithTotp();

        $this->postJson('/login/totp', ['email' => $user->email, 'recovery_code' => 'abc-123-def'])->assertSuccessful();

        $log->shouldHaveReceived('info')->with('auth.login.succeeded', Mockery::on(
            fn (array $context) => $context['method'] === 'recovery_code'
                && ! str_contains(json_encode($context), 'abc-123-def')
        ))->once();
    }

    public function test_passkey_registration_and_deletion_are_audited(): void
    {
        $log = Log::spy();
        [$user] = $this->userWithTotp();
        $passkey = $this->passkeyFor($user);

        PasskeyRegistered::dispatch($user, $passkey);
        PasskeyDeleted::dispatch($user, $passkey);

        $log->shouldHaveReceived('info')->with('auth.credential.passkey_registered', Mockery::on(
            fn (array $context) => $context['actor_id'] === $user->id && $context['passkey_id'] === $passkey->id
        ))->once();
        $log->shouldHaveReceived('info')->with('auth.credential.passkey_deleted', Mockery::type('array'))->once();
    }

    public function test_enabling_totp_from_the_cli_is_audited_without_the_secret(): void
    {
        $log = Log::spy();
        $user = User::factory()->create(['email' => 'owner@example.test', 'password' => null]);

        Artisan::call('kai:enable-totp', ['email' => 'owner@example.test']);
        $output = Artisan::output();
        preg_match('/secret=([A-Z2-7]+)/', $output, $matches);

        $log->shouldHaveReceived('info')->with('auth.credential.totp_enabled', Mockery::on(
            fn (array $context) => $context['actor_id'] === $user->id
                && $context['source'] === 'cli'
                && ! str_contains(json_encode($context), $matches[1])
        ))->once();
    }

    public function test_incident_rotation_from_the_cli_audits_the_revocations(): void
    {
        // Revisão de segurança N1: deletes em massa não disparam eventos.
        $log = Log::spy();
        [$user] = $this->userWithTotp();
        $this->passkeyFor($user);
        DB::table('sessions')->insert([
            'id' => 's-1', 'user_id' => $user->id, 'ip_address' => '127.0.0.1',
            'user_agent' => 'x', 'payload' => 'x', 'last_activity' => time(),
        ]);

        $this->artisan('kai:enable-totp', [
            'email' => $user->email, '--force' => true, '--revoke-passkeys' => true,
        ])->assertSuccessful();

        $log->shouldHaveReceived('info')->with('auth.credential.sessions_revoked', Mockery::on(
            fn (array $context) => $context['actor_id'] === $user->id && $context['count'] === 1 && $context['source'] === 'cli'
        ))->once();
        $log->shouldHaveReceived('info')->with('auth.credential.passkeys_revoked', Mockery::on(
            fn (array $context) => $context['actor_id'] === $user->id && $context['count'] === 1
        ))->once();
    }

    public function test_disabling_totp_over_http_is_audited(): void
    {
        $log = Log::spy();
        [$user, $secret] = $this->userWithTotp();
        $this->postJson('/login/totp', [
            'email' => $user->email,
            'code' => app(Google2FA::class)->getCurrentOtp($secret),
        ])->assertSuccessful();

        $this->deleteJson('/user/two-factor-authentication')->assertSuccessful();

        $log->shouldHaveReceived('info')->with('auth.credential.totp_disabled', Mockery::on(
            fn (array $context) => $context['actor_id'] === $user->id && $context['source'] === 'http'
        ))->once();
    }
}
