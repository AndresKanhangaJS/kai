<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Cross-Origin Resource Sharing (CORS) Configuration
    |--------------------------------------------------------------------------
    |
    | Here you may configure your settings for cross-origin resource sharing
    | or "CORS". This determines what cross-origin operations may execute
    | in web browsers. You are free to adjust these settings as needed.
    |
    | To learn more: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
    |
    */

    // SPEC-002: o apps/web autentica-se por sessão/cookie cross-origin
    // (Sanctum), não só api/*: inclui as rotas do Fortify e dos passkeys.
    'paths' => [
        'api/*',
        'sanctum/csrf-cookie',
        'login',
        'login/*',
        'logout',
        'two-factor-challenge',
        'user/*',
        'passkeys/*',
    ],

    'allowed_methods' => ['*'],

    // Credentials exige uma lista explícita, nunca '*' (CORS não permite
    // combinar wildcard com supports_credentials).
    'allowed_origins' => array_filter(explode(',', env('FRONTEND_URL', 'http://localhost:5173'))),

    'allowed_origins_patterns' => [],

    'allowed_headers' => ['*'],

    'exposed_headers' => [],

    'max_age' => 0,

    'supports_credentials' => true,

];
