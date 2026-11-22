<?php

namespace Tests\Feature\Auth;

use App\Models\User;
use Illuminate\Auth\Events\Login;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Laravel\Fortify\Fortify;
use PragmaRX\Google2FA\Google2FA;
use Tests\TestCase;

/**
 * threat-model-identity-access.md T-12 (achado da revisão de segurança da
 * E4.6b): gerir credenciais exige uma autenticação recente (≤ 10 min, D-05).
 * Um cookie de sessão roubado não chega para registar uma passkey nem ler
 * ou trocar os segredos TOTP — senão, revogar a sessão já não expulsaria o
 * atacante.
 */
class RecentAuthenticationTest extends TestCase
{
    use RefreshDatabase;

    /** Rotas de gestão de credenciais protegidas pelo step-up. */
    private const PROTECTED_ROUTES = [
        ['GET', '/user/passkeys/options'],
        ['POST', '/user/passkeys'],
        ['GET', '/user/two-factor-secret-key'],
        ['GET', '/user/two-factor-qr-code'],
        ['GET', '/user/two-factor-recovery-codes'],
        ['POST', '/user/two-factor-recovery-codes'],
        ['POST', '/user/two-factor-authentication'],
        ['DELETE', '/user/two-factor-authentication'],
        ['POST', '/user/confirmed-two-factor-authentication'],
        ['DELETE', '/user/passkeys/1'],
    ];

    private function loginViaTotp(): User
    {
        $secret = app(Google2FA::class)->generateSecretKey();
        $user = User::factory()->create([
            'password' => null,
            'two_factor_secret' => Fortify::currentEncrypter()->encrypt($secret),
            'two_factor_recovery_codes' => Fortify::currentEncrypter()->encrypt(json_encode(['abc-123-def'])),
            'two_factor_confirmed_at' => now(),
        ]);

        $code = app(Google2FA::class)->getCurrentOtp($secret);
        $this->postJson('/login/totp', ['email' => $user->email, 'code' => $code])->assertSuccessful();

        return $user;
    }

    public function test_credential_management_is_allowed_right_after_login(): void
    {
        $this->loginViaTotp();

        $this->getJson('/user/passkeys/options')->assertSuccessful();
        $this->getJson('/user/two-factor-recovery-codes')->assertSuccessful();
    }

    public function test_credential_management_is_refused_when_the_authentication_is_older_than_10_minutes(): void
    {
        $user = $this->loginViaTotp();
        $secretBefore = $user->fresh()->two_factor_secret;
        // Uma passkey real do utilizador, para o DELETE /user/passkeys/1 não
        // falhar por 404 antes do middleware.
        DB::table('passkeys')->insert([
            'id' => 1, 'user_id' => $user->id, 'name' => 'Teste', 'credential_id' => 'cred-1',
            'credential' => '{}', 'created_at' => now(), 'updated_at' => now(),
        ]);

        $this->travel(11)->minutes();

        foreach (self::PROTECTED_ROUTES as [$method, $uri]) {
            $this->json($method, $uri)->assertStatus(423);
        }

        // Nada mudou: o TOTP continua activo, com o mesmo segredo, e a passkey existe.
        $this->assertSame($secretBefore, $user->fresh()->two_factor_secret);
        $this->assertSame(1, DB::table('passkeys')->where('id', 1)->count());
    }

    public function test_a_remember_me_relogin_does_not_count_as_a_recent_authentication(): void
    {
        // Revisão de segurança N2: só uma autenticação real confirma a sessão.
        $user = User::factory()->create(['password' => null]);
        $request = request();
        $request->setLaravelSession(app('session.store'));

        event(new Login('web', $user, remember: true));

        $this->assertFalse($request->session()->has('auth.password_confirmed_at'));

        event(new Login('web', $user, remember: false));

        $this->assertTrue($request->session()->has('auth.password_confirmed_at'));
    }

    public function test_an_old_session_is_still_valid_for_non_sensitive_requests(): void
    {
        $this->loginViaTotp();

        $this->travel(11)->minutes();

        // api/* só é stateful (Sanctum) com o Referer do SPA, como em
        // SessionManagementTest::fromFrontend().
        $this->withHeader('Referer', 'http://'.config('sanctum.stateful.0', 'localhost:5173'))
            ->getJson('/api/sessions')
            ->assertSuccessful();
    }

    public function test_credential_management_requires_authentication(): void
    {
        foreach (self::PROTECTED_ROUTES as [$method, $uri]) {
            $this->json($method, $uri)->assertUnauthorized();
        }
    }
}
