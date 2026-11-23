<?php

/*
 * M03 E3.2 (SPEC-004, AC-004-01): o AI Engine real, ligado ao RabbitMQ da stack
 * `kai-it`, está pronto e responde conforme o health.v1. Corre só com
 * scripts/ci/integration.sh. O 503 sem RabbitMQ é testado no pytest.
 */

use GuzzleHttp\Client;

function aiEngine(string $path): string
{
    return 'http://'.((string) (getenv('AI_ENGINE_HOST') ?: 'ai-engine')).':8000'.$path;
}

test('AC-004-01: o AI Engine real está vivo e pronto, com o RabbitMQ ligado', function () {
    $http = new Client(['timeout' => 5, 'http_errors' => false]);

    $live = $http->get(aiEngine('/health/live'));
    expect($live->getStatusCode())->toBe(200)
        ->and(json_decode((string) $live->getBody(), true))->toBe(['status' => 'ok']);

    $ready = $http->get(aiEngine('/health/ready'));
    expect($ready->getStatusCode())->toBe(200)
        ->and(json_decode((string) $ready->getBody(), true))->toBe(['status' => 'ok', 'checks' => ['rabbitmq' => 'ok']]);
});

test('AC-004-01 negativo: o AI Engine não expõe documentação nem OpenAPI', function (string $path) {
    $http = new Client(['timeout' => 5, 'http_errors' => false]);
    expect($http->get(aiEngine($path))->getStatusCode())->toBe(404);
})->with(['/docs', '/redoc', '/openapi.json']);
