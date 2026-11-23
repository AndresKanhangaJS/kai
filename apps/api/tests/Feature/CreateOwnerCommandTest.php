<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class CreateOwnerCommandTest extends TestCase
{
    use RefreshDatabase;

    public function test_creates_the_owner_without_a_password_and_with_default_preferences(): void
    {
        $this->artisan('kai:create-owner', ['name' => 'André', 'email' => 'owner@example.test'])
            ->assertSuccessful();

        $owner = User::query()->where('email', 'owner@example.test')->sole();

        $this->assertNull($owner->password);
        $this->assertNotNull($owner->preferences);
        $this->assertSame('pt', $owner->preferences->locale);
        $this->assertSame('dark', $owner->preferences->theme);
    }

    public function test_rejects_an_invalid_email(): void
    {
        $this->artisan('kai:create-owner', ['name' => 'André', 'email' => 'not-an-email'])
            ->assertFailed();

        $this->assertDatabaseCount('users', 0);
    }

    public function test_rejects_a_second_owner_without_force(): void
    {
        User::factory()->create();

        $this->artisan('kai:create-owner', ['name' => 'Outro', 'email' => 'outro@example.test'])
            ->assertFailed();

        $this->assertDatabaseCount('users', 1);
    }

    public function test_allows_a_second_owner_with_force(): void
    {
        User::factory()->create();

        $this->artisan('kai:create-owner', ['name' => 'Outro', 'email' => 'outro@example.test', '--force' => true])
            ->assertSuccessful();

        $this->assertDatabaseCount('users', 2);
    }

    public function test_rejects_a_duplicate_email(): void
    {
        $existing = User::factory()->create();

        $this->artisan('kai:create-owner', ['name' => 'Duplicado', 'email' => $existing->email, '--force' => true])
            ->assertFailed();

        $this->assertDatabaseCount('users', 1);
    }
}
