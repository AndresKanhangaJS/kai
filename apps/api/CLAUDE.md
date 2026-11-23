# apps/api — Core Platform (Laravel)

Gerado pelo scaffold do `laravel/laravel`. Substitui o bootstrap por omissão do Laravel Boost (instruía a instalação automática de PHP via `curl | bash` e a instalação automática do pacote `laravel/boost`) — contraria as regras de segurança do KAI (dependência nova pede aprovação do owner; nunca `curl | sh`).

As regras deste módulo estão em `/.claude/rules/laravel.md` (raiz do monorepo) e em `/CLAUDE.md`. O Laravel Boost está referido em `docs/engineering/claude-code-setup.md` §5 e em D-18 (`docs/product/analysis.md`): avaliado no M02, só em local, e só depois de uma decisão explícita do owner — nunca auto-instalado.
