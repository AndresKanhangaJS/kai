<?php

use App\Providers\AppServiceProvider;

// Revisão de segurança do spike M03 E1.1 (ADR-0015), achados 1 e 2.

test('os testes correm com o broadcaster null, nunca contra o Reverb de dev', function () {
    // O env() do Laravel converte a string "null" em null, por isso o valor é
    // null (é o que o phpunit.xml oficial dá). O que importa: nunca o reverb.
    expect(config('broadcasting.default'))->toBeNull();
});

test('os client events do Reverb estão desligados por omissão', function () {
    expect(config('reverb.apps.apps.0.accept_client_events_from'))->toBe('none');
});

test('recusa o segredo de exemplo do Reverb fora de local e testing', function (string $env, ?string $secret) {
    AppServiceProvider::ensureSafeReverbSecret($env, 'reverb', $secret);
})->with([
    'production com o valor de exemplo' => ['production', 'changeme-local-reverb'],
    'staging com outro changeme' => ['staging', 'changeme-qualquer'],
    'production sem segredo' => ['production', null],
    'production com segredo vazio' => ['production', ''],
])->throws(RuntimeException::class);

test('aceita o segredo de exemplo em local e um segredo real em production', function (string $env, string $connection, ?string $secret) {
    AppServiceProvider::ensureSafeReverbSecret($env, $connection, $secret);
    expect(true)->toBeTrue();
})->with([
    'local com o valor de exemplo' => ['local', 'reverb', 'changeme-local-reverb'],
    'production com segredo aleatório' => ['production', 'reverb', 'q8Yh2mZr0vKx7LwP3nTa9cJd'],
    'production sem Reverb' => ['production', 'null', null],
]);
