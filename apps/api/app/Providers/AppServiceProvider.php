<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;

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
    }
}
