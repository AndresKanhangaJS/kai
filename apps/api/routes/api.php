<?php

use App\Http\Controllers\Auth\SessionController;
use Illuminate\Support\Facades\Route;

Route::middleware('auth:sanctum')->group(function () {
    Route::get('/sessions', [SessionController::class, 'index'])->name('api.sessions.index');
    Route::delete('/sessions/{id}', [SessionController::class, 'destroy'])->name('api.sessions.destroy');
});
