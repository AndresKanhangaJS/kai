<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\DB;
use Laravel\Fortify\Fortify;
use PragmaRX\Google2FA\Google2FA;
use Tests\TestCase;

/**
 * SPEC-002 / E4.6b: o owner criado por CLI (sem credencial) activa o TOTP
 * pela CLI; o segredo é mostrado uma única vez, nunca guardado em claro.
 */
class EnableTotpCommandTest extends TestCase
{
    use RefreshDatabase;

    private function secretFromOutput(string $output): string
    {
        $this->assertMatchesRegularExpression('/otpauth:\/\/totp\/[^\s]*secret=([A-Z2-7]+)/', $output);
        preg_match('/secret=([A-Z2-7]+)/', $output, $matches);

        return $matches[1];
    }

    public function test_enables_totp_and_shows_the_secret_and_recovery_codes_once(): void
    {
        $owner = User::factory()->create(['email' => 'owner@example.test', 'password' => null]);

        $exitCode = Artisan::call('kai:enable-totp', ['email' => 'owner@example.test']);
        $output = Artisan::output();

        $this->assertSame(0, $exitCode);
        $secret = $this->secretFromOutput($output);

        $owner->refresh();
        $this->assertNotNull($owner->two_factor_confirmed_at);
        $this->assertSame($secret, Fortify::currentEncrypter()->decrypt($owner->two_factor_secret));
        $this->assertCount(8, $owner->recoveryCodes());
        foreach ($owner->recoveryCodes() as $recoveryCode) {
            $this->assertStringContainsString($recoveryCode, $output);
        }
    }

    public function test_the_secret_is_not_stored_in_plain_text(): void
    {
        User::factory()->create(['email' => 'owner@example.test', 'password' => null]);

        Artisan::call('kai:enable-totp', ['email' => 'owner@example.test']);
        $secret = $this->secretFromOutput(Artisan::output());

        $raw = DB::table('users')->where('email', 'owner@example.test')->sole();
        $this->assertStringNotContainsString($secret, (string) $raw->two_factor_secret);
    }

    public function test_a_code_from_the_shown_secret_logs_in(): void
    {
        $owner = User::factory()->create(['email' => 'owner@example.test', 'password' => null]);

        Artisan::call('kai:enable-totp', ['email' => 'owner@example.test']);
        $secret = $this->secretFromOutput(Artisan::output());

        $response = $this->postJson('/login/totp', [
            'email' => 'owner@example.test',
            'code' => app(Google2FA::class)->getCurrentOtp($secret),
        ]);

        $response->assertSuccessful();
        $this->assertAuthenticatedAs($owner);
    }

    public function test_fails_for_an_unknown_email_without_revealing_anything(): void
    {
        $this->artisan('kai:enable-totp', ['email' => 'nobody@example.test'])
            ->doesntExpectOutputToContain('otpauth://')
            ->assertFailed();
    }

    public function test_refuses_to_rotate_an_active_secret_without_force(): void
    {
        $owner = User::factory()->create([
            'email' => 'owner@example.test',
            'password' => null,
            'two_factor_secret' => Fortify::currentEncrypter()->encrypt('JBSWY3DPEHPK3PXP'),
            'two_factor_confirmed_at' => now(),
        ]);
        $before = $owner->two_factor_secret;

        $this->artisan('kai:enable-totp', ['email' => 'owner@example.test'])
            ->doesntExpectOutputToContain('otpauth://')
            ->assertFailed();

        $this->assertSame($before, $owner->fresh()->two_factor_secret);
    }

    public function test_rotates_an_active_secret_with_force(): void
    {
        $owner = User::factory()->create([
            'email' => 'owner@example.test',
            'password' => null,
            'two_factor_secret' => Fortify::currentEncrypter()->encrypt('JBSWY3DPEHPK3PXP'),
            'two_factor_confirmed_at' => now(),
        ]);

        $exitCode = Artisan::call('kai:enable-totp', ['email' => 'owner@example.test', '--force' => true]);
        $secret = $this->secretFromOutput(Artisan::output());

        $this->assertSame(0, $exitCode);
        $this->assertNotSame('JBSWY3DPEHPK3PXP', $secret);
        $this->assertSame($secret, Fortify::currentEncrypter()->decrypt($owner->fresh()->two_factor_secret));
    }

    private function ownerWithSessionsAndPasskey(): User
    {
        $owner = User::factory()->create([
            'email' => 'owner@example.test',
            'password' => null,
            'two_factor_secret' => Fortify::currentEncrypter()->encrypt('JBSWY3DPEHPK3PXP'),
            'two_factor_confirmed_at' => now(),
        ]);
        $other = User::factory()->create();

        foreach ([[$owner, 's-owner-1'], [$owner, 's-owner-2'], [$other, 's-other']] as [$user, $id]) {
            DB::table('sessions')->insert([
                'id' => $id, 'user_id' => $user->id, 'ip_address' => '127.0.0.1',
                'user_agent' => 'x', 'payload' => 'x', 'last_activity' => time(),
            ]);
        }
        DB::table('passkeys')->insert([
            'user_id' => $owner->id, 'name' => 'Teste', 'credential_id' => 'cred-owner',
            'credential' => '{}', 'created_at' => now(), 'updated_at' => now(),
        ]);

        return $owner;
    }

    public function test_rotation_with_force_revokes_only_the_owners_sessions(): void
    {
        // Revisão de segurança da E4.6b: rodar o segredo sem revogar as
        // sessões dava uma falsa sensação de contenção de um incidente.
        $owner = $this->ownerWithSessionsAndPasskey();

        $this->artisan('kai:enable-totp', ['email' => 'owner@example.test', '--force' => true])->assertSuccessful();

        $this->assertSame(0, DB::table('sessions')->where('user_id', $owner->id)->count());
        $this->assertSame(1, DB::table('sessions')->where('id', 's-other')->count());
        // Sem --revoke-passkeys, as passkeys ficam.
        $this->assertSame(1, DB::table('passkeys')->where('user_id', $owner->id)->count());
    }

    public function test_rotation_with_revoke_passkeys_also_removes_the_owners_passkeys(): void
    {
        $owner = $this->ownerWithSessionsAndPasskey();

        $this->artisan('kai:enable-totp', [
            'email' => 'owner@example.test', '--force' => true, '--revoke-passkeys' => true,
        ])->assertSuccessful();

        $this->assertSame(0, DB::table('passkeys')->where('user_id', $owner->id)->count());
    }
}
