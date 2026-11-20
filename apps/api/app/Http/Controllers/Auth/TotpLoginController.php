<?php

namespace App\Http\Controllers\Auth;

use App\Models\User;
use Illuminate\Contracts\Auth\StatefulGuard;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Log;
use Laravel\Fortify\Contracts\TwoFactorAuthenticationProvider;
use Laravel\Fortify\Events\TwoFactorAuthenticationFailed;
use Laravel\Fortify\Events\ValidTwoFactorAuthenticationCodeProvided;
use Laravel\Fortify\Fortify;

/**
 * D-05 / SPEC-002: TOTP é uma alternativa à passkey, não um segundo factor
 * depois de uma password (o Fortify só tem o 2.º caso embutido, e não há
 * password nesta aplicação). Reutiliza o TwoFactorAuthenticationProvider do
 * Fortify para verificar o código exactamente como o Fortify o faria.
 *
 * Resposta genérica em qualquer falha (utilizador inexistente, sem TOTP
 * activo, código errado): threat-model-identity-access.md T-01.
 */
class TotpLoginController extends Controller
{
    public function __invoke(Request $request, TwoFactorAuthenticationProvider $provider)
    {
        $request->validate([
            'email' => ['required', 'email'],
            'code' => ['nullable', 'string'],
            'recovery_code' => ['nullable', 'string'],
        ]);

        $user = User::query()->where('email', $request->string('email'))->first();

        $genericError = ['email' => [__('Credenciais inválidas.')]];

        if (! $user || ! $user->hasEnabledTwoFactorAuthentication()) {
            Log::warning('auth.login.failed', ['method' => 'totp', 'trace_id' => $request->header('traceparent')]);

            return response()->json(['errors' => $genericError], 422);
        }

        if ($recoveryCode = $request->string('recovery_code')->toString()) {
            $validCode = collect($user->recoveryCodes())->first(
                fn (string $code) => hash_equals($code, $recoveryCode)
            );

            if ($validCode) {
                $user->replaceRecoveryCode($validCode);

                return $this->login($request, $user);
            }
        } elseif ($code = $request->string('code')->toString()) {
            if ($provider->verify(Fortify::currentEncrypter()->decrypt($user->two_factor_secret), $code)) {
                ValidTwoFactorAuthenticationCodeProvided::dispatch($user);

                return $this->login($request, $user);
            }
        }

        TwoFactorAuthenticationFailed::dispatch($user);

        return response()->json(['errors' => $genericError], 422);
    }

    private function login(Request $request, User $user): \Illuminate\Http\JsonResponse
    {
        /** @var StatefulGuard $guard */
        $guard = Auth::guard('web');
        $guard->login($user);
        $request->session()->regenerate();

        return response()->json(['data' => ['id' => $user->id]]);
    }
}
