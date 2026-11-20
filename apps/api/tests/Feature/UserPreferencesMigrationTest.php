<?php

namespace Tests\Feature;

use App\Models\User;
use App\Models\UserPreference;
use Illuminate\Database\QueryException;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;
use Tests\TestCase;

class UserPreferencesMigrationTest extends TestCase
{
    use RefreshDatabase;

    public function test_sessions_table_has_last_authenticated_at_column(): void
    {
        $this->assertTrue(Schema::hasColumn('sessions', 'last_authenticated_at'));
    }

    public function test_a_user_has_at_most_one_preferences_row(): void
    {
        $user = User::factory()->create();
        UserPreference::factory()->create(['user_id' => $user->id]);

        $this->expectException(QueryException::class);

        UserPreference::factory()->create(['user_id' => $user->id]);
    }

    public function test_preferences_defaults_are_pt_and_dark(): void
    {
        $user = User::factory()->create();
        $preference = UserPreference::factory()->create([
            'user_id' => $user->id,
            'locale' => 'pt',
            'theme' => 'dark',
        ]);

        $this->assertSame('pt', $preference->locale);
        $this->assertSame('dark', $preference->theme);
        $this->assertTrue($user->preferences->is($preference));
    }

    public function test_deleting_a_user_cascades_to_preferences_and_sessions(): void
    {
        $user = User::factory()->create();
        UserPreference::factory()->create(['user_id' => $user->id]);
        DB::table('sessions')->insert([
            'id' => 'test-session-id',
            'user_id' => $user->id,
            'ip_address' => '127.0.0.1',
            'user_agent' => 'phpunit',
            'payload' => base64_encode('x'),
            'last_activity' => time(),
        ]);

        $user->delete();

        $this->assertDatabaseMissing('user_preferences', ['user_id' => $user->id]);
        $this->assertDatabaseMissing('sessions', ['user_id' => $user->id]);
    }
}
