<?php

namespace Tests;

use Illuminate\Foundation\Testing\TestCase as BaseTestCase;
use RuntimeException;

abstract class TestCase extends BaseTestCase
{
    /**
     * Guarda contra o bug da E4.4 (revisão de segurança da E2): o ambiente do
     * contentor (DB_CONNECTION=mysql) sobrepõe-se ao phpunit.xml, e o
     * RefreshDatabase faria migrate:fresh no MySQL real, apagando os dados de
     * dev. Corre antes dos traits (RefreshDatabase incluído): sem SQLite em
     * memória, nenhum teste toca na base de dados. Usa scripts/ci/api.sh.
     *
     * @return array<class-string, class-string>
     */
    protected function setUpTraits()
    {
        static::ensureIsolatedTestDatabase(
            (string) config('database.default'),
            (string) config('database.connections.sqlite.database'),
        );

        return parent::setUpTraits();
    }

    public static function ensureIsolatedTestDatabase(string $connection, string $sqliteDatabase): void
    {
        if ($connection !== 'sqlite' || $sqliteDatabase !== ':memory:') {
            throw new RuntimeException(
                "Os testes só correm em SQLite em memória (ligação actual: {$connection}). "
                .'Usa scripts/ci/api.sh: correr o Pest com o ambiente do Docker Compose '
                .'apagaria a base de dados de desenvolvimento.'
            );
        }
    }
}
