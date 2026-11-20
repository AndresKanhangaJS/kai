# Configuração do Claude Code no KAI

- **Verificado a:** 2026-11-20
- **Versões do Claude Code:**
  - 2.1.329 (`latest` no npm; corre na sessão Windows);
  - 2.1.311 (`stable`);
  - 2.1.211 (instalada no WSL; deve ser actualizada).

Este documento regista **o que foi verificado na documentação oficial** antes de escrever a configuração, e onde vive cada peça. Se a sintaxe mudar, actualiza-se aqui primeiro.

## 1. Factos verificados

| Tema | Facto (citado ou parafraseado de perto) | Fonte |
|---|---|---|
| Memória | `./CLAUDE.md` ou `./.claude/CLAUDE.md`. "Target under 200 lines per CLAUDE.md file." Os imports `@caminho` resolvem relativamente ao ficheiro que importa, com profundidade máxima de 4. Imports dentro de code spans e de blocos de código são ignorados. Os comentários HTML de bloco são removidos antes de o texto ser injectado. | code.claude.com/docs/en/memory |
| Regras | `.claude/rules/**/*.md`. Sem `paths`: carregam no arranque. Com frontmatter `paths:` (lista YAML ou string separada por vírgulas): carregam quando Read/Write/Edit tocam num ficheiro correspondente. Os globs são relativos à pasta que contém `.claude`. YAML inválido equivale a não ter `paths`. | code.claude.com/docs/en/memory |
| Skills | `.claude/skills/<nome>/SKILL.md`. Todos os campos são opcionais; recomenda-se `description`. Campos usados aqui: `name`, `description`, `disable-model-invocation` (bool, por omissão `false`), `allowed-tools`. `description` + `when_to_use` são truncados a 1536 caracteres na listagem. "Keep `SKILL.md` under 500 lines." Ficheiros de apoio são referenciados por links markdown. Campos desconhecidos são ignorados sem erro. | code.claude.com/docs/en/skills |
| Subagentes | `.claude/agents/*.md`. `name` e `description` são obrigatórios. `tools` é uma string separada por vírgulas ou uma lista YAML; se for omitido, herda todas as ferramentas. `model` aceita `sonnet`, `opus`, `haiku`, `fable`, um ID completo ou `inherit`. Para delegação proactiva, a descrição deve incluir algo como "use proactively". Campos desconhecidos são ignorados sem erro. | code.claude.com/docs/en/sub-agents |
| Hooks | Estrutura `{"hooks": {"PreToolUse": [{"matcher": "...", "hooks": [{"type": "command", "command": "${CLAUDE_PROJECT_DIR}/...", "args": []}]}]}}`. Matcher `A\|B` é uma lista exacta; outros caracteres fazem dele uma regex JS. No stdin chegam `tool_name` e `tool_input` (Bash: `command`; Read/Write/Edit: `file_path` absoluto; Grep/Glob: `path` e `pattern`). **Bloquear: exit 2, com o motivo em stderr.** Em alternativa, JSON `hookSpecificOutput.permissionDecision: "deny"`. Exit 0 sem output não aprova nada. SessionStart: o stdout é acrescentado ao contexto. PostToolUse não bloqueia. "Command hooks execute shell commands with your full user permissions." Recomenda-se o exec form (`args`) quando o comando usa placeholders. | code.claude.com/docs/en/hooks |
| Settings | Ficheiros `.claude/settings.json` (partilhado) e `.claude/settings.local.json` (pessoal). O `settings.local.json` **não** é posto no `.gitignore` do repositório, por isso foi acrescentado ao nosso. Schema: `https://json.schemastore.org/claude-code-settings.json`. As listas fazem merge entre ficheiros. | code.claude.com/docs/en/settings |
| Permissões | A ordem é deny → ask → allow; um allow não abre excepção num deny. Bash: `Bash(git commit *)`, onde o `*` final com espaço também casa o comando sem argumentos. Comandos compostos são divididos e cada subcomando tem de ser permitido; deny e ask casam qualquer subcomando. Read/Edit usam padrões gitignore: `./` e caminho simples são relativos ao directório actual, `/` à origem das settings, `//` absoluto, `~/` a home. **Aviso oficial:** as regras Bash "isn't a security boundary around the program"; para defesa a sério usam-se hooks PreToolUse ou sandbox. | code.claude.com/docs/en/permissions |
| MCP | `.mcp.json` com `mcpServers`. Tipos: `http`, `sse` (obsoleto), `ws`; sem `type` é stdio. Expansão `${VAR}` e `${VAR:-default}`. Servidores de projecto pedem aprovação. "Verify you trust each server before connecting it." | code.claude.com/docs/en/mcp |

**Limitações da verificação:**
- Parte das páginas longas foi lida através de um resumo e não de texto literal: a tabela completa de frontmatter das skills (depois confirmada literalmente para os campos usados), os detalhes de `.mcp.json` com `env` e a aprovação de servidores MCP.
- Confirmar visualmente com `/memory`, `/skills`, `/agents`, `/hooks`, `/permissions` e `/mcp`.

## 2. Inventário do harness

| Peça | Caminho | Notas |
|---|---|---|
| Memória do projecto | `CLAUDE.md` | ≤ 150 linhas; importa `docs/STATUS.md`; refere `docs/product/kai-vision.md` sem a importar (D-17) |
| Regras | `.claude/rules/*.md` | Globais: `security`, `git-workflow`, `testing`, `observability`. Com `paths`: `docs-and-adrs`, `laravel`, `react-typescript`, `python-ai-engine`, `contracts`. Só fazem efeito quando as pastas existirem. |
| Skills | `.claude/skills/kai-*`, `status`, `done` | `status` e `done` são manuais (`disable-model-invocation: true`) |
| Subagentes | `.claude/agents/kai-*.md` | Privilégio mínimo; modelo escolhido por custo/benefício (secção 3) |
| Hooks | `.claude/hooks/` | `guard.sh` (PreToolUse), `session-start.sh` (SessionStart), `post-edit-format.sh` (PostToolUse, sem efeito por agora) |
| Permissões | `.claude/settings.json` | allow / ask / deny (secção 4) |
| Validação | `.claude/scripts/validate_harness.py`, `.claude/hooks/tests/test_guard.sh` | Corridos na Fase 3 |

## 3. Escolha de modelos dos subagentes

| Modelo | Subagentes | Razão |
|---|---|---|
| `opus` | `kai-architect`, `kai-security-reviewer`, `kai-verifier` | Decisões e auditorias de baixa frequência e alto impacto |
| `sonnet` | `kai-laravel-engineer`, `kai-react-engineer`, `kai-python-ai-engineer`, `kai-qa-engineer`, `kai-devops-engineer`, `kai-ai-eval-engineer` | Implementação frequente com boa relação custo/qualidade |
| `haiku` | `kai-docs-writer` | Escrita estruturada, de baixo risco |

## 4. Permissões e hooks: defesa em camadas

- As **regras de permissão** apanham os casos comuns, mas a documentação avisa que não são uma fronteira de segurança.
- O **hook `guard.sh`** inspecciona o comando e os caminhos reais e bloqueia com exit 2:
  - leitura ou escrita de segredos, incluindo directórios de credenciais (`~/.ssh`, `~/.aws`, …) e globs que os possam apanhar (`.env*`);
  - `sudo`, `doas`, `su`, `pkexec`;
  - `rm` recursivo fora de caminhos seguros;
  - `git push --force`/`-f`/`+refspec`, apagar branches remotas, `--no-verify`;
  - `curl` ou `wget` canalizados para uma shell, mesmo com caminho absoluto ou `tee` pelo meio.
- O comando é analisado tal como vem e também normalizado (sem aspas nem escapes, com `bash -c`, `eval`, `$(…)` e crases expostos). Desde a auditoria do `kai-verifier` na Fase 3, os testes cobrem 22 bypasses (75 casos no total).
- **Auto-modificação:** editar `.claude/settings*.json`, `.claude/hooks/**` ou `.claude/scripts/**` com as ferramentas Edit/Write fica em `ask`, porque o agente não deve desligar o próprio guard sem o owner ver.
- **Limites conhecidos** (não é uma sandbox):
  - variáveis (`f=.e; cat ${f}nv`), scripts escritos e depois executados, `find -delete`, aliases do git;
  - `grep -r TOKEN .`, que lê segredos sem os nomear;
  - escrita em `.claude/hooks` através do Bash (`sed -i`); o Bash já pede confirmação por omissão;
  - o `WebFetch` dos agentes só-leitura é um canal de saída. Como não está em `allow`, cada pedido pede confirmação.
- As regras `Bash(curl * | sh*)` do `deny` são [H]: o Claude Code divide comandos compostos e pode nunca as fazer coincidir. A protecção efectiva é o hook.
- O guard é um wrapper bash (`guard.sh`) sobre `guard.py`: Python stdlib, executado com `python3 -I`. O parsing de JSON e de comandos em bash puro é frágil, e o `jq` não está instalado.
- **Requisito:** os hooks precisam de `python3` no PATH, por isso o Claude Code tem de correr **dentro do WSL** (D-04). Numa sessão Windows nativa, os hooks falham.

## 5. MCP: proposta (nada instalado)

**Estado:** proposta aprovada pelo owner a 2026-11-20 (D-18). Nada está instalado; a instalação acontece no M02 e pede nova aprovação.

Factos verificados a 2026-11-20 nos repositórios oficiais. Nenhum servidor é configurado sem aprovação do owner. Credenciais apenas em variáveis de ambiente ou OAuth, nunca em ficheiros.

| Servidor | O que ganha o KAI | Risco | Credenciais / permissões | Recomendação |
|---|---|---|---|---|
| **GitHub MCP** (github/github-mcp-server, MIT) | Issues, PRs e Actions sem sair da sessão | Escrita no GitHub; prompt injection vinda de issues e PRs. O "lockdown mode" é "best-effort", não uma fronteira. | OAuth, ou PAT via `GITHUB_PERSONAL_ACCESS_TOKEN`; usar `--read-only` e `--toolsets` mínimos | **Adoptar no M02**, em modo read-only e com PAT fine-grained só para este repositório |
| **Laravel Boost** (laravel/boost, MIT; suporta Laravel 12.41+ e 13) | Pesquisa na documentação Laravel, schema da BD, logs, último erro | A ferramenta "Database Query" executa queries sem modo read-only documentado; o `boost:install` reescreve `CLAUDE.md`/`.mcp.json` | Nenhuma; stdio `php artisan boost:mcp` | **Avaliar no M02**, só em local, com BD de dados sintéticos; **não** correr o `boost:install` sobre o nosso `CLAUDE.md` |
| **Playwright MCP** (microsoft/playwright-mcp, Apache-2.0) | Testes E2E e verificação visual da UI | Não é fronteira de segurança; `browser_run_code_unsafe` equivale a execução remota de código | Nenhuma; `npx @playwright/mcp@latest` (Node 20+) | **Adiar para o M02/M03**; o README sugere a Playwright CLI como alternativa mais económica |
| **Context7** (upstash/context7, MIT) | Documentação actualizada de bibliotecas | As consultas vão para servidores da Upstash; os docs são contribuídos pela comunidade e não confiáveis | API key opcional via header, ou OAuth | **Não adoptar** por agora: preferimos as fontes oficiais via WebFetch |

Formato a usar quando aprovado (sem segredos; expansão de variáveis verificada):

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": { "Authorization": "Bearer ${GITHUB_MCP_PAT}" }
    }
  }
}
```

Fontes:
- github.com/github/github-mcp-server
- github.com/laravel/boost
- laravel.com/docs/13.x/boost
- github.com/microsoft/playwright-mcp
- github.com/upstash/context7
