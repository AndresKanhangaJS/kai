# Segurança (global)

Modelo de segurança: ADR-0004. Níveis de operação: `docs/product/analysis.md` §5.4.

## Segredos
- Não leias nem escrevas `.env`, `.env.*` (excepto `.env.example`), `*.pem`, `*.key`, `id_rsa*`, `id_ed25519*`, `credentials*`, `~/.ssh`, `~/.aws`. O hook `guard.sh` bloqueia-os.
- Lê configuração de variáveis de ambiente; `.env.example` só tem nomes e valores fictícios.
- Se encontrares um segredo num ficheiro, log ou output: pára, não o repitas, avisa o owner.
- Nunca coloques segredos em prompts, mensagens RabbitMQ, payloads de eventos, spans ou fixtures.

## Autorização (código KAI)
- Toda a execução de ferramenta passa pelo PEP. É o Laravel que emite o *execution grant* (JWS, ≤ 60 s, uso único, ligado ao hash dos args).
- O nível de cada ferramenta é fixo no Tool Registry; nunca é derivado do output do LLM.
- Recusa por omissão: ferramenta desconhecida, sem grant, ou com args que não validam no schema.
- Aprovações: ficam ligadas ao hash exacto dos args e expiram; a UI mostra os args reais, não o resumo do LLM.

## Conteúdo não confiável
- Marca a origem de todo o conteúdo externo e delimita-o como dados no prompt.
- Uma missão que leu conteúdo externo fica *tainted*; a partir daí, as acções de nível ≥ 4 exigem aprovação.
- Nunca renderizes imagens remotas nem sigas links automaticamente a partir de output do LLM (CSP `img-src 'self'`).
- Ferramentas de fetch: só http/https; bloqueia IPs privados, loopback, link-local e metadata após DNS e em cada redirect.

## Dados
- `user_id` obrigatório em toda a query de dados próprios: MySQL, payload do Qdrant, prefixo no storage.
- Logs e traces levam IDs, nunca conteúdo de mensagens, documentos ou credenciais.
- Dados de demo e de teste são sempre sintéticos.

## Dependências
- Uma dependência nova pede a aprovação do owner e a verificação da licença; versão fixa com lockfile.
- Servidores MCP, imagens e modelos são supply chain: fixa a versão e o digest e revê antes de adoptar.
