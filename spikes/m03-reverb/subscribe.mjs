// Spike M03 E1.1: subscreve o canal privado run.{id} no Reverb, como o
// browser vai fazer (protocolo Pusher 7), e mede ordem e latência dos deltas.
//
// A assinatura da subscrição é calculada aqui com o segredo da app: no produto
// quem a emite é o Laravel em /broadcasting/auth, depois de verificar o dono
// do run (E4.6). O spike só prova o transporte e a recusa de auth inválida.
// Node 24: WebSocket e crypto nativos, sem dependências.
import { createHmac } from 'node:crypto';

const { REVERB_APP_KEY: KEY, REVERB_APP_SECRET: SECRET, SPIKE_CHANNEL: CHANNEL } = process.env;
const WS_URL = process.env.REVERB_WS_URL ?? 'ws://reverb:8080';
const ORIGIN = process.env.SPIKE_ORIGIN ?? 'http://localhost:5173';
const COUNT = Number(process.env.SPIKE_COUNT ?? 100);
const TIMEOUT_MS = Number(process.env.SPIKE_TIMEOUT_MS ?? 60000);

function connect({ origin, signWith }) {
  return new Promise((resolve) => {
    const ws = new WebSocket(`${WS_URL}/app/${KEY}?protocol=7&client=js&version=8.4.0`, { headers: { Origin: origin } });
    const out = { ws, events: [], subscribed: false, error: null };
    ws.addEventListener('message', (msg) => {
      const m = JSON.parse(msg.data);
      if (m.event === 'pusher:connection_established') {
        const { socket_id } = JSON.parse(m.data);
        const sig = createHmac('sha256', signWith).update(`${socket_id}:${CHANNEL}`).digest('hex');
        ws.send(JSON.stringify({ event: 'pusher:subscribe', data: { channel: CHANNEL, auth: `${KEY}:${sig}` } }));
      } else if (m.event === 'pusher_internal:subscription_succeeded') {
        out.subscribed = true;
        resolve(out);
      } else if (m.event === 'pusher:error' || m.event === 'pusher:subscription_error') {
        out.error = m.data;
        resolve(out);
      } else if (m.event === 'delta') {
        out.events.push({ ...JSON.parse(m.data), received_at_ms: Date.now() });
      }
    });
    ws.addEventListener('error', (e) => { out.error = String(e.message ?? e.type); resolve(out); });
    ws.addEventListener('close', (e) => { if (!out.subscribed) { out.error ??= `close ${e.code}`; resolve(out); } });
    setTimeout(() => { out.error ??= 'timeout'; resolve(out); }, 10000);
  });
}

const fail = (msg) => { console.log(`FALHA: ${msg}`); process.exit(1); };

// Negativos primeiro: assinatura errada e origem não permitida.
const badAuth = await connect({ origin: ORIGIN, signWith: 'segredo-errado' });
console.log(`subscricao-auth-invalida subscrito=${badAuth.subscribed} erro=${JSON.stringify(badAuth.error)}`);
if (badAuth.subscribed) fail('subscrição aceite com assinatura inválida');
badAuth.ws.close();

const badOrigin = await connect({ origin: 'http://evil.example', signWith: SECRET });
console.log(`ligacao-origem-invalida subscrito=${badOrigin.subscribed} erro=${JSON.stringify(badOrigin.error)}`);
if (badOrigin.subscribed) fail('ligação aceite de uma origem não permitida');
badOrigin.ws.close();

// Positivo: subscreve e espera pelos deltas.
const sub = await connect({ origin: ORIGIN, signWith: SECRET });
if (!sub.subscribed) fail(`subscrição válida recusada: ${JSON.stringify(sub.error)}`);
// Negativo: client events desligados (accept_client_events_from = none).
// Um subscritor não pode injectar eventos aos outros subscritores do canal.
const clientEventError = await new Promise((resolve) => {
  const onMsg = (msg) => {
    const m = JSON.parse(msg.data);
    if (m.event === 'pusher:error') { sub.ws.removeEventListener('message', onMsg); resolve(m.data); }
  };
  sub.ws.addEventListener('message', onMsg);
  sub.ws.send(JSON.stringify({ event: 'client-injecao', channel: CHANNEL, data: { seq: -1 } }));
  setTimeout(() => resolve(null), 3000);
});
console.log(`client-event recusado=${clientEventError !== null} erro=${JSON.stringify(clientEventError)}`);
if (clientEventError === null) fail('client event aceite');
console.log('READY');

const deadline = Date.now() + TIMEOUT_MS;
while (sub.events.length < COUNT && Date.now() < deadline) await new Promise((r) => setTimeout(r, 50));
sub.ws.close();

const seqs = sub.events.map((e) => e.seq);
const inOrder = seqs.every((s, i) => i === 0 || s > seqs[i - 1]);
const lat = sub.events.map((e) => e.received_at_ms - e.sent_at_ms).sort((a, b) => a - b);
const pct = (p) => lat[Math.min(lat.length - 1, Math.ceil((p / 100) * lat.length) - 1)];
console.log(`recebidos=${sub.events.length}/${COUNT} por_ordem=${inOrder} latencia_ms p50=${pct(50)?.toFixed(1)} p95=${pct(95)?.toFixed(1)} max=${lat.at(-1)?.toFixed(1)}`);
if (sub.events.length !== COUNT || !inOrder) fail('deltas em falta ou fora de ordem');
if (pct(95) >= 100) fail(`p95 ${pct(95).toFixed(1)} ms ≥ 100 ms`);
console.log('OK: critério do E1.1 cumprido');
