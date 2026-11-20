<?php

namespace Tests\Feature\Auth;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Laravel\Fortify\Fortify;
use PragmaRX\Google2FA\Google2FA;
use Tests\TestCase;

class TotpLoginTest extends TestCase
{
    use RefreshDatabase;

    private function userWithTotp(): array
    {
        $secret = app(Google2FA::class)->generateSecretKey();

        $user = User::factory()->create([
            'two_factor_secret' => Fortify::currentEncrypter()->encrypt($secret),
            'two_factor_recovery_codes' => Fortify::currentEncrypter()->encrypt(json_encode(['abc-123-def'])),
            'two_factor_confirmed_at' => now(),
        ]);

        return [$user, $secret];
    }

    public function test_logs_in_with_a_valid_totp_code(): void
    {
        [$user, $secret] = $this->userWithTotp();
        $code = app(Google2FA::class)->getCurrentOtp($secret);

        $response = $this->postJson('/login/totp', ['email' => $user->email, 'code' => $code]);

        $response->assertSuccessful();
        $this->assertAuthenticatedAs($user);
    }

    public function test_logs_in_with_a_valid_recovery_code_and_consumes_it(): void
    {
        [$user] = $this->userWithTotp();

        $response = $this->postJson('/login/totp', ['email' => $user->email, 'recovery_code' => 'abc-123-def']);

        $response->assertSuccessful();
        $this->assertAuthenticatedAs($user);
        $this->assertNotContains('abc-123-def', $user->fresh()->recoveryCodes());
    }

    public function test_rejects_an_invalid_code_without_creating_a_session(): void
    {
        [$user, $secret] = $this->userWithTotp();

        $response = $this->postJson('/login/totp', ['email' => $user->email, 'code' => '000000']);

        $response->assertStatus(422);
        $this->assertGuest();
    }

    public function test_gives_the_same_generic_error_for_an_unknown_email_as_for_a_wrong_code(): void
    {
        // threat-model-identity-access.md T-01: a resposta não pode revelar
        // se o email existe.
        [$user] = $this->userWithTotp();

        $unknown = $this->postJson('/login/totp', ['email' => 'nobody@example.test', 'code' => '000000']);
        $wrongCode = $this->postJson('/login/totp', ['email' => $user->email, 'code' => '000000']);

        $this->assertSame($unknown->status(), $wrongCode->status());
        $this->assertSame($unknown->json(), $wrongCode->json());
    }

    public function test_two_factor_secret_and_recovery_codes_are_not_stored_in_plain_text(): void
    {
        // threat-model-identity-access.md T-06.
        [$user, $secret] = $this->userWithTotp();

        $raw = DB::table('users')->where('id', $user->id)->first();

        $this->assertStringNotContainsString($secret, (string) $raw->two_factor_secret);
        $this->assertStringNotContainsString('abc-123-def', (string) $raw->two_factor_recovery_codes);
    }

    public function test_a_failed_attempt_is_logged(): void
    {
        // threat-model-identity-access.md T-10.
        Log::spy();

        [$user] = $this->userWithTotp();
        $this->postJson('/login/totp', ['email' => $user->email, 'code' => '000000']);

        Log::shouldHaveReceived('warning')->with('auth.login.failed', \Mockery::type('array'))->once();
    }

    public function test_login_rate_limit_blocks_after_repeated_failures(): void
    {
        // threat-model-identity-access.md T-04.
        [$user] = $this->userWithTotp();

        for ($i = 0; $i < 5; $i++) {
            $this->postJson('/login/totp', ['email' => $user->email, 'code' => '000000'])->assertStatus(422);
        }

        $this->postJson('/login/totp', ['email' => $user->email, 'code' => '000000'])
            ->assertStatus(429);
    }
}
