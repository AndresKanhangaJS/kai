<?php

namespace App\Console\Commands;

use App\Models\User;
use App\Models\UserPreference;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Validator;

/**
 * D-05: o owner é criado por CLI, nunca por um formulário de registo público.
 * Sem password: a autenticação é só por passkey/TOTP (SPEC-002), configurada
 * depois do login inicial, não por este comando.
 */
class CreateOwnerCommand extends Command
{
    protected $signature = 'kai:create-owner {name} {email} {--force : Cria mesmo já existindo um owner}';

    protected $description = 'Cria o owner do KAI (D-05: sem registo público)';

    public function handle(): int
    {
        $name = $this->argument('name');
        $email = $this->argument('email');

        $validator = Validator::make(
            ['name' => $name, 'email' => $email],
            ['name' => ['required', 'string', 'max:255'], 'email' => ['required', 'email', 'max:255', 'unique:users,email']],
        );

        if ($validator->fails()) {
            foreach ($validator->errors()->all() as $message) {
                $this->error($message);
            }

            return self::FAILURE;
        }

        if (User::query()->exists() && ! $this->option('force')) {
            $this->error('Já existe pelo menos um utilizador. O KAI é pensado para um só owner (D-05). Usa --force para criar outro mesmo assim.');

            return self::FAILURE;
        }

        $owner = User::query()->create([
            'name' => $name,
            'email' => $email,
            'email_verified_at' => now(),
            'password' => null,
        ]);

        $owner->preferences()->save(new UserPreference(['locale' => 'pt', 'theme' => 'dark']));

        $this->info("Owner criado: #{$owner->id} <{$owner->email}>.");
        $this->line('Sem password: autentica-te por passkey ou TOTP depois de configurares uma credencial.');

        return self::SUCCESS;
    }
}
