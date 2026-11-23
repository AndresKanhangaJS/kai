<?php

use App\Http\Controllers\Auth\TotpLoginController;
use Illuminate\Support\Facades\Route;

Route::get('/', function () {
    return view('welcome');
});

// SPEC-002: login por TOTP como alternativa à passkey (D-05), não um
// segundo factor depois de uma password — ver TotpLoginController.
Route::post('/login/totp', TotpLoginController::class)
    ->middleware(['guest:web', 'throttle:login'])
    ->name('login.totp');
