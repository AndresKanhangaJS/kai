<?php

namespace Tests\Feature\Auth;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Laravel\Fortify\Fortify;
use PragmaRX\Google2FA\Google2FA;
use Tests\TestCase;

class SessionManagementTest extends TestCase
{
    use RefreshDatabase;

    /**
     * As rotas api/* só arrancam a sessão (StartSession) para pedidos que o
     * Sanctum reconhece como vindos do SPA (Origin/Referer em
     * SANCTUM_STATEFUL_DOMAINS) — ver EnsureFrontendRequestsAreStateful.
     */
    private function fromFrontend(): self
    {
        // SANCTUM_STATEFUL_DOMAINS substitui por completo a lista por omissão
        // do Sanctum (que incluiria app.url) — tem de ser a origem do SPA,
        // não a da própria API.
        $this->withHeader('Referer', 'http://'.config('sanctum.stateful.0', 'localhost:5173'));

        return $this;
    }

    private function loginViaTotp(): User
    {
        $secret = app(Google2FA::class)->generateSecretKey();
        $user = User::factory()->create([
            'two_factor_secret' => Fortify::currentEncrypter()->encrypt($secret),
            'two_factor_recovery_codes' => Fortify::currentEncrypter()->encrypt(json_encode(['x'])),
            'two_factor_confirmed_at' => now(),
        ]);

        $code = app(Google2FA::class)->getCurrentOtp($secret);
        $this->postJson('/login/totp', ['email' => $user->email, 'code' => $code])->assertSuccessful();

        return $user;
    }

    public function test_login_updates_last_authenticated_at_and_is_logged(): void
    {
        // threat-model-identity-access.md T-10 e SPEC-002 §4 (last_authenticated_at).
        // O driver de sessão de teste é "array" (rápido, não persiste); este
        // teste precisa mesmo da tabela sessions.
        config(['session.driver' => 'database']);
        $log = Log::spy();

        $user = $this->loginViaTotp();

        $session = DB::table('sessions')->where('user_id', $user->id)->sole();
        $this->assertNotNull($session->last_authenticated_at);

        $log->shouldHaveReceived('info')->with('auth.login.succeeded', \Mockery::type('array'))->once();
    }

    public function test_lists_only_the_authenticated_users_sessions(): void
    {
        $user = $this->loginViaTotp();
        $other = User::factory()->create();
        DB::table('sessions')->insert([
            'id' => 'other-session', 'user_id' => $other->id, 'ip_address' => '127.0.0.1',
            'user_agent' => 'x', 'payload' => 'x', 'last_activity' => time(),
        ]);

        $response = $this->fromFrontend()->getJson('/api/sessions');

        $response->assertSuccessful();
        /** @var list<array{id: string}> $data */
        $data = $response->json('data');
        $ids = array_column($data, 'id');
        $this->assertNotContains('other-session', $ids);
    }

    public function test_revoking_a_session_removes_it_and_it_stops_authenticating(): void
    {
        $user = $this->loginViaTotp();
        DB::table('sessions')->insert([
            'id' => 'device-b', 'user_id' => $user->id, 'ip_address' => '127.0.0.1',
            'user_agent' => 'device B', 'payload' => 'x', 'last_activity' => time(),
        ]);

        $this->fromFrontend()->deleteJson('/api/sessions/device-b')->assertNoContent();

        $this->assertDatabaseMissing('sessions', ['id' => 'device-b']);
    }

    public function test_cannot_revoke_another_users_session(): void
    {
        // threat-model-identity-access.md T-08 (IDOR).
        $this->loginViaTotp();
        $other = User::factory()->create();
        DB::table('sessions')->insert([
            'id' => 'victim-session', 'user_id' => $other->id, 'ip_address' => '127.0.0.1',
            'user_agent' => 'x', 'payload' => 'x', 'last_activity' => time(),
        ]);

        $this->fromFrontend()->deleteJson('/api/sessions/victim-session')->assertNotFound();

        $this->assertDatabaseHas('sessions', ['id' => 'victim-session']);
    }

    public function test_sessions_endpoints_require_authentication(): void
    {
        $this->getJson('/api/sessions')->assertUnauthorized();
        $this->deleteJson('/api/sessions/whatever')->assertUnauthorized();
    }
}
