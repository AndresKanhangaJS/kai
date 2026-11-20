<?php

namespace App\Http\Controllers\Auth;

use Illuminate\Http\Request;
use Illuminate\Routing\Controller;
use Illuminate\Support\Facades\DB;

/**
 * SPEC-002 AC-02d/e/f. threat-model-identity-access.md T-08: toda a query
 * filtra por user_id do pedido autenticado, nunca confia no id isolado.
 */
class SessionController extends Controller
{
    public function index(Request $request)
    {
        $sessions = DB::table('sessions')
            ->where('user_id', $request->user()->getKey())
            ->orderByDesc('last_activity')
            ->get(['id', 'ip_address', 'user_agent', 'last_activity', 'last_authenticated_at']);

        $currentId = $request->session()->getId();

        return response()->json([
            'data' => $sessions->map(fn ($session) => [
                'id' => $session->id,
                'ip_address' => $session->ip_address,
                'user_agent' => $session->user_agent,
                'last_activity' => $session->last_activity,
                'last_authenticated_at' => $session->last_authenticated_at,
                'current' => $session->id === $currentId,
            ]),
        ]);
    }

    public function destroy(Request $request, string $id)
    {
        $deleted = DB::table('sessions')
            ->where('id', $id)
            ->where('user_id', $request->user()->getKey())
            ->delete();

        if ($deleted === 0) {
            return response()->json(['message' => 'Sessão não encontrada.'], 404);
        }

        return response()->noContent();
    }
}
