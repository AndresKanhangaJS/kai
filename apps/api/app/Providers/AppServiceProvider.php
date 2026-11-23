<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use RuntimeException;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        //
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        // App\Listeners\LogAuthenticationAttempt é auto-descoberto pelo
        // Laravel (os parâmetros tipados em Login/TwoFactorAuthenticationFailed
        // já bastam); registá-lo aqui também duplicava os logs.

        self::ensureSafeReverbSecret(
            (string) $this->app->environment(),
            config('broadcasting.default'),
            config('broadcasting.connections.reverb.secret'),
        );
    }

    /**
     * Recusa arrancar fora de local/testing com o segredo de exemplo do Reverb
     * (valor público, em .env.example e no docker-compose.yml) ou sem segredo.
     * Quem o tiver assina subscrições de qualquer canal privado (ADR-0015;
     * revisão de segurança do spike M03 E1.1, achado 1).
     */
    public static function ensureSafeReverbSecret(string $environment, mixed $connection, mixed $secret): void
    {
        if (in_array($environment, ['local', 'testing'], true) || $connection !== 'reverb') {
            return;
        }

        if (! is_string($secret) || $secret === '' || str_starts_with($secret, 'changeme')) {
            throw new RuntimeException('REVERB_APP_SECRET em falta ou com o valor de exemplo fora de local/testing.');
        }
    }
}
