<?php

/*
 * M03 E2.1 (ADR-0003, ADR-0016): a topologia do RabbitMQ contra o broker
 * real. Corre só com scripts/ci/integration.sh (stack descartável `kai-it`),
 * nunca no Pest normal (SQLite). As passwords chegam por ambiente e são
 * aleatórias em cada corrida. Inclui os negativos da revisão de segurança.
 */

use PhpAmqpLib\Channel\AMQPChannel;
use PhpAmqpLib\Connection\AMQPStreamConnection;
use PhpAmqpLib\Exception\AMQPProtocolChannelException;
use PhpAmqpLib\Message\AMQPMessage;
use PhpAmqpLib\Wire\AMQPTable;

const TURN_REQUESTED = 'ai.conversation.turn.requested.v1';
const TURN_COMPLETED = 'ai.conversation.turn.completed.v1';

function rabbit(string $user, ?string $password = null): AMQPStreamConnection
{
    $passwords = [
        'kai-admin' => getenv('KAI_RABBITMQ_ADMIN_PASSWORD'),
        'kai-api' => getenv('KAI_RABBITMQ_API_PASSWORD'),
        'kai-ai-engine' => getenv('KAI_RABBITMQ_AI_ENGINE_PASSWORD'),
    ];

    return new AMQPStreamConnection(
        (string) (getenv('RABBITMQ_HOST') ?: 'rabbitmq'), 5672, $user,
        $password ?? (string) ($passwords[$user] ?? ''), '/kai',
    );
}

/** @return array<string, mixed> */
function validExample(): array
{
    $dir = (string) (getenv('KAI_CONTRACTS_DIR') ?: '/contracts');
    $json = file_get_contents($dir.'/examples/'.TURN_REQUESTED.'/valid/minimo.json');
    expect($json)->toBeString();

    /** @var array<string, mixed> */
    return json_decode((string) $json, true, flags: JSON_THROW_ON_ERROR);
}

/**
 * Publica com publisher confirms; devolve true se o broker confirmou.
 *
 * @param  array<string, mixed>  $props
 */
function publishConfirmed(AMQPChannel $ch, string $exchange, string $routingKey, string $body, array $props = []): bool
{
    $confirmed = false;
    $ch->set_ack_handler(function () use (&$confirmed) {
        $confirmed = true;
    });
    $ch->confirm_select();
    $ch->basic_publish(new AMQPMessage($body, ['content_type' => 'application/json', 'delivery_mode' => 2] + $props), $exchange, $routingKey);
    $ch->wait_for_pending_acks(5.0);

    return $confirmed;
}

function getWithin(AMQPChannel $ch, string $queue, float $seconds): ?AMQPMessage
{
    $deadline = microtime(true) + $seconds;
    do {
        $msg = $ch->basic_get($queue);
        if ($msg !== null) {
            return $msg;
        }
        usleep(100_000);
    } while (microtime(true) < $deadline);

    return null;
}

/** Corre a acção e exige que o broker feche o canal com o código indicado. */
function expectChannelError(int $code, callable $action): void
{
    try {
        $action();
    } catch (AMQPProtocolChannelException $e) {
        expect($e->getCode())->toBe($code);

        return;
    }

    throw new RuntimeException("operação aceite pelo broker; esperava o erro {$code}");
}

/** Abre uma ligação, corre a acção num canal e exige o erro indicado. */
function expectRefusedAs(string $user, int $code, callable $action): void
{
    $conn = rabbit($user);
    try {
        expectChannelError($code, fn () => $action($conn->channel()));
    } finally {
        $conn->close();
    }
}

beforeEach(function () {
    $admin = rabbit('kai-admin');
    $ch = $admin->channel();
    foreach (['ai-engine.commands', 'ai-engine.commands.dlq', 'kai-api.events', 'kai-api.events.dlq'] as $q) {
        $ch->queue_purge($q);
    }
    $admin->close();
});

test('E2.1: o kai-api publica um turn.requested válido com confirm e user_id, e o ai-engine consome-o', function () {
    $body = json_encode(validExample(), JSON_THROW_ON_ERROR);

    $api = rabbit('kai-api');
    expect(publishConfirmed($api->channel(), 'kai.commands', TURN_REQUESTED, $body, ['user_id' => 'kai-api']))->toBeTrue();
    $api->close();

    $engine = rabbit('kai-ai-engine');
    $msg = getWithin($engine->channel(), 'ai-engine.commands', 5);
    expect($msg)->not->toBeNull()
        ->and($msg?->getBody())->toBe($body)
        ->and($msg?->getRoutingKey())->toBe(TURN_REQUESTED)
        ->and($msg?->get('user_id'))->toBe('kai-api');
    $msg?->ack();
    $engine->close();
});

test('E2.1 negativo: o broker recusa um user_id falsificado (406)', function () {
    expectRefusedAs('kai-ai-engine', 406, fn (AMQPChannel $ch) => publishConfirmed($ch, 'kai.events', TURN_COMPLETED, '{}', ['user_id' => 'kai-api']));
});

test('E2.1 negativo: um serviço não publica onde não deve (403)', function (string $user, string $exchange, string $routingKey) {
    expectRefusedAs($user, 403, fn (AMQPChannel $ch) => publishConfirmed($ch, $exchange, $routingKey, '{}'));
})->with([
    'kai-api em kai.events' => ['kai-api', 'kai.events', TURN_COMPLETED],
    'ai-engine em kai.commands' => ['kai-ai-engine', 'kai.commands', TURN_REQUESTED],
    'ai-engine na própria DLQ' => ['kai-ai-engine', 'ai-engine.dead', 'ai-engine.commands'],
    'kai-api na própria DLQ' => ['kai-api', 'kai-api.dead', 'kai-api.events'],
    'ai-engine no dead do kai-api' => ['kai-ai-engine', 'kai-api.dead', 'kai-api.events'],
    'ai-engine na exchange por omissão' => ['kai-ai-engine', '', 'ai-engine.commands'],
    'kai-api na exchange por omissão' => ['kai-api', '', 'kai-api.events'],
    'ai-engine em amq.topic' => ['kai-ai-engine', 'amq.topic', TURN_REQUESTED],
    'kai-api em amq.direct' => ['kai-api', 'amq.direct', 'kai-api.events'],
]);

test('E2.1 negativo: topic permissions só deixam publicar os tipos de cada serviço (403)', function (string $user, string $exchange, string $routingKey) {
    expectRefusedAs($user, 403, fn (AMQPChannel $ch) => publishConfirmed($ch, $exchange, $routingKey, '{}'));
})->with([
    'ai-engine publica um comando em kai.events' => ['kai-ai-engine', 'kai.events', 'ai.mission.step.resume.v1'],
    'ai-engine publica um cancel em kai.events' => ['kai-ai-engine', 'kai.events', 'ai.mission.cancel.requested.v1'],
    'kai-api publica um evento em kai.commands' => ['kai-api', 'kai.commands', TURN_COMPLETED],
    'kai-api publica um tipo desconhecido' => ['kai-api', 'kai.commands', 'ai.qualquer.coisa.v1'],
]);

test('E2.1 negativo: um serviço não lê a fila do outro nem a DLQ (403)', function (string $user, string $queue) {
    expectRefusedAs($user, 403, fn (AMQPChannel $ch) => $ch->basic_get($queue));
})->with([
    'kai-api lê ai-engine.commands' => ['kai-api', 'ai-engine.commands'],
    'ai-engine lê kai-api.events' => ['kai-ai-engine', 'kai-api.events'],
    'ai-engine lê a própria DLQ' => ['kai-ai-engine', 'ai-engine.commands.dlq'],
]);

test('E2.1 negativo: nenhum serviço declara filas nem cria bindings (403)', function (string $user, string $op) {
    expectRefusedAs($user, 403, fn (AMQPChannel $ch) => $op === 'declare'
        ? $ch->queue_declare('intrusa', false, true, false, false)
        : $ch->queue_bind('kai-api.events', 'kai.commands', '#'));
})->with([
    'kai-api declara' => ['kai-api', 'declare'],
    'ai-engine declara' => ['kai-ai-engine', 'declare'],
    'kai-api faz bind' => ['kai-api', 'bind'],
    'ai-engine faz bind' => ['kai-ai-engine', 'bind'],
]);

test('E2.1 negativo: o guest não existe e uma password errada é recusada', function (string $user, string $password) {
    $refused = null;
    try {
        rabbit($user, $password)->close();
    } catch (Throwable $e) {
        $refused = $e->getMessage();
    }
    expect($refused)->toContain('ACCESS_REFUSED');
})->with([
    'guest' => ['guest', 'guest'],
    'kai-api com password errada' => ['kai-api', 'errada'],
]);

function reachable(int $port): bool
{
    set_error_handler(fn () => true); // a recusa da ligação é o resultado esperado, não um aviso
    try {
        $socket = fsockopen((string) (getenv('RABBITMQ_HOST') ?: 'rabbitmq'), $port, $errno, $errstr, 2.0);
    } finally {
        restore_error_handler();
    }
    if ($socket === false) {
        return false;
    }
    fclose($socket);

    return true;
}

test('E2.1: o AMQP (5672) é alcançável a partir de outro contentor (controlo do teste seguinte)', function () {
    expect(reachable(5672))->toBeTrue();
});

test('E2.1 negativo: só o AMQP é alcançável a partir de outro contentor (gestão, métricas, Erlang)', function (int $port) {
    expect(reachable($port))->toBeFalse();
})->with(['gestão 15672' => 15672, 'prometheus 15692' => 15692, 'distribuição Erlang 25672' => 25672, 'epmd 4369' => 4369]);

/** @return list<array<string, mixed>> */
function xDeath(?AMQPMessage $msg): array
{
    $headers = $msg?->has('application_headers') ? $msg->get('application_headers') : null;

    /** @var list<array<string, mixed>> */
    return $headers instanceof AMQPTable ? ($headers->getNativeData()['x-death'] ?? []) : [];
}

test('E2.1 (ADR-0018): um nack sem requeue vai para a DLQ pelo broker, com o user_id original', function () {
    $api = rabbit('kai-api');
    publishConfirmed($api->channel(), 'kai.commands', TURN_REQUESTED, '{"marca":"nack"}', ['user_id' => 'kai-api']);
    $api->close();

    $engine = rabbit('kai-ai-engine');
    getWithin($engine->channel(), 'ai-engine.commands', 5)?->nack(false);
    $engine->close();

    $admin = rabbit('kai-admin');
    $dead = getWithin($admin->channel(), 'ai-engine.commands.dlq', 5);
    expect($dead?->getBody())->toBe('{"marca":"nack"}')
        ->and($dead?->get('user_id'))->toBe('kai-api')
        ->and(xDeath($dead)[0]['reason'] ?? null)->toBe('rejected');
    $dead?->ack();
    $admin->close();
});

test('E2.1 (ADR-0018, achado N1): uma mensagem que derruba o consumidor 6 vezes acaba na DLQ, nunca se perde', function () {
    $api = rabbit('kai-api');
    publishConfirmed($api->channel(), 'kai.commands', TURN_REQUESTED, '{"marca":"poison"}', ['user_id' => 'kai-api']);
    $api->close();

    // "crash": recebe e fecha a ligação sem ack; o delivery-limit é 5.
    for ($i = 1; $i <= 6; $i++) {
        $engine = rabbit('kai-ai-engine');
        expect(getWithin($engine->channel(), 'ai-engine.commands', 5))->not->toBeNull();
        $engine->close();
    }

    $admin = rabbit('kai-admin');
    $dead = getWithin($admin->channel(), 'ai-engine.commands.dlq', 10);
    expect($dead?->getBody())->toBe('{"marca":"poison"}')
        ->and(xDeath($dead)[0]['reason'] ?? null)->toBe('delivery_limit');
    $dead?->ack();
    $admin->close();
});

test('E2.1: uma mensagem acima de 16 MiB é recusada pelo broker (406)', function () {
    expectRefusedAs('kai-api', 406, fn (AMQPChannel $ch) => publishConfirmed($ch, 'kai.commands', TURN_REQUESTED, str_repeat('x', 16 * 1024 * 1024 + 1)));
});
