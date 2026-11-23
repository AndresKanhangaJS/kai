// Só para o contentor E2E (docker-compose.yml, perfil "e2e"): reencaminha
// localhost:5173 → web:5173 e localhost:8000 → api:8000, para o Chromium ver
// a mesma origem (http://localhost:5173) que o RP ID e as origens permitidas
// das passkeys esperam. Evita `network_mode: host`, que não funciona no
// Docker Desktop por omissão.
import net from 'node:net'

const routes = [
  { port: 5173, host: 'web' },
  { port: 8000, host: 'api' },
]

for (const { port, host } of routes) {
  net
    .createServer((client) => {
      const upstream = net.connect(port, host)
      client.pipe(upstream).pipe(client)
      const close = () => {
        client.destroy()
        upstream.destroy()
      }
      client.on('error', close)
      upstream.on('error', close)
    })
    .listen(port, '127.0.0.1')
}
