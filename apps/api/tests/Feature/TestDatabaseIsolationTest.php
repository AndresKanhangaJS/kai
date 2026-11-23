<?php

use Tests\TestCase;

// Guarda do bug da E4.4 (revisão de segurança da E2): os testes recusam
// correr fora do SQLite em memória, antes de o RefreshDatabase migrar.

it('recusa correr contra o MySQL', function () {
    TestCase::ensureIsolatedTestDatabase('mysql', 'kai');
})->throws(RuntimeException::class, 'SQLite em memória');

it('recusa um SQLite em ficheiro (persistente)', function () {
    TestCase::ensureIsolatedTestDatabase('sqlite', '/app/database/database.sqlite');
})->throws(RuntimeException::class);

it('aceita o SQLite em memória', function () {
    TestCase::ensureIsolatedTestDatabase('sqlite', ':memory:');
    expect(true)->toBeTrue();
});

it('esta própria corrida está isolada', function () {
    expect(config('database.default'))->toBe('sqlite')
        ->and(config('database.connections.sqlite.database'))->toBe(':memory:');
});
