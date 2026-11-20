<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * SPEC-002 (Identity & Access).
 * - last_authenticated_at: timestamp da última autenticação (passkey/TOTP/recuperação),
 *   não da última actividade. Preparado para o M05 exigir re-autenticação nos
 *   últimos 10 min em operações de nível 5 (D-05, ADR-0013) — o campo entra
 *   agora, a exigência (middleware) só chega com o M05.
 * - user_id passa a ter uma foreign key explícita: a migração original do
 *   scaffold só tinha a coluna e o índice, sem constraint.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('sessions', function (Blueprint $table) {
            $table->timestamp('last_authenticated_at')->nullable()->after('user_id');
            $table->foreign('user_id')->references('id')->on('users')->cascadeOnDelete();
        });
    }

    public function down(): void
    {
        Schema::table('sessions', function (Blueprint $table) {
            $table->dropForeign(['user_id']);
            $table->dropColumn('last_authenticated_at');
        });
    }
};
