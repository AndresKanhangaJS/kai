<?php

/*
 * M03 E2.2 (ADR-0017): o otel-lgtm recebe spans por OTLP/HTTP e o Tempo
 * devolve-os. Corre só com scripts/ci/integration.sh (stack `kai-it`). O span
 * é sintético: só IDs e nomes, nunca conteúdo (observability.md).
 */

use GuzzleHttp\Client;

function lgtm(int $port): string
{
    return 'http://'.((string) (getenv('OTEL_LGTM_HOST') ?: 'otel-lgtm')).':'.$port;
}

test('E2.2: um span de teste enviado por OTLP/HTTP aparece no Tempo', function () {
    $traceId = bin2hex(random_bytes(16));
    $spanId = bin2hex(random_bytes(8));
    $now = (int) (microtime(true) * 1e9);

    $http = new Client(['timeout' => 5, 'http_errors' => false]);
    $sent = $http->post(lgtm(4318).'/v1/traces', ['json' => [
        'resourceSpans' => [[
            'resource' => ['attributes' => [['key' => 'service.name', 'value' => ['stringValue' => 'kai-it']]]],
            'scopeSpans' => [[
                'scope' => ['name' => 'kai.e2.2'],
                'spans' => [[
                    'traceId' => $traceId, 'spanId' => $spanId, 'name' => 'e2.2 span de teste', 'kind' => 1,
                    'startTimeUnixNano' => (string) ($now - 1_000_000), 'endTimeUnixNano' => (string) $now,
                ]],
            ]],
        ]],
    ]]);
    expect($sent->getStatusCode())->toBe(200);

    $found = null;
    $deadline = microtime(true) + 30;
    do {
        // O Tempo responde 200 com um trace vazio enquanto ainda não ingeriu o span.
        $res = $http->get(lgtm(3200).'/api/v2/traces/'.$traceId);
        $body = (string) $res->getBody();
        if ($res->getStatusCode() === 200 && str_contains($body, 'e2.2 span de teste')) {
            $found = $body;
            break;
        }
        usleep(500_000);
    } while (microtime(true) < $deadline);

    expect($found)->not->toBeNull()
        ->and($found)->toContain('e2.2 span de teste')
        ->and($found)->toContain('kai-it');
});

test('E2.2 negativo: o Grafana não aceita pedidos anónimos nem a password por omissão', function (?array $auth) {
    $http = new Client(['timeout' => 5, 'http_errors' => false]);
    $res = $http->get(lgtm(3000).'/api/org', $auth === null ? [] : ['auth' => $auth]);
    expect($res->getStatusCode())->toBe(401);
})->with([
    'anónimo' => [null],
    'admin/admin' => [['admin', 'admin']],
]);

test('E2.2: o Grafana aceita o admin com a password do ambiente', function () {
    $http = new Client(['timeout' => 5, 'http_errors' => false]);
    $res = $http->get(lgtm(3000).'/api/org', ['auth' => ['admin', (string) getenv('KAI_GRAFANA_ADMIN_PASSWORD')]]);
    expect($res->getStatusCode())->toBe(200);
});

test('E2.2 negativo: o Grafana não descarrega plugins, não envia estatísticas nem aceita outras formas de autenticação (configuração efectiva)', function () {
    // O preinstall do Grafana é assíncrono: verificar o directório de plugins
    // dependeria do tempo da descarga. Verifica-se a configuração efectiva.
    $http = new Client(['timeout' => 5, 'http_errors' => false]);
    $res = $http->get(lgtm(3000).'/api/admin/settings', ['auth' => ['admin', (string) getenv('KAI_GRAFANA_ADMIN_PASSWORD')]]);
    expect($res->getStatusCode())->toBe(200);

    /** @var array<string, array<string, string>> $settings */
    $settings = json_decode((string) $res->getBody(), true);
    expect($settings['plugins']['preinstall_disabled'] ?? null)->toBe('true')
        ->and($settings['auth.anonymous']['enabled'] ?? null)->toBe('false')
        ->and($settings['analytics']['reporting_enabled'] ?? null)->toBe('false')
        ->and($settings['analytics']['check_for_updates'] ?? null)->toBe('false')
        ->and($settings['snapshots']['external_enabled'] ?? null)->toBe('false')
        ->and($settings['security']['disable_gravatar'] ?? null)->toBe('true')
        ->and($settings['auth.proxy']['enabled'] ?? null)->toBe('false')
        ->and($settings['auth.jwt']['enabled'] ?? null)->toBe('false');
});

test('E2.2 negativo: o Loki, o Tempo e o Pyroscope não enviam estatísticas de uso (configuração efectiva)', function (int $port, string $path, string $section) {
    $http = new Client(['timeout' => 5, 'http_errors' => false]);
    $res = $http->get(lgtm($port).$path);
    expect($res->getStatusCode())->toBe(200)
        ->and((string) $res->getBody())->toMatch('/^'.$section.':\R\s+reporting_enabled: false$/m');
})->with([
    'Loki' => [3100, '/config', 'analytics'],
    'Tempo' => [3200, '/status/config', 'usage_report'],
    'Pyroscope' => [4040, '/api/v1/status/config', 'analytics'],
]);
