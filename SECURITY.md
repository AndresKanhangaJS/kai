# Política de segurança

## Estado
O KAI está em Product Discovery e ainda não tem código de aplicação nem versões publicadas. Esta política aplica-se ao repositório e a tudo o que vier a ser publicado a partir dele.

## Reportar uma vulnerabilidade
- **Não abras uma issue pública.** Usa o reporte privado do GitHub: separador **Security → Report a vulnerability** deste repositório.
- Inclui:
  - a descrição;
  - o impacto;
  - os passos para reproduzir;
  - as versões ou commits afectados;
  - uma sugestão de correcção, se tiveres.
- Não incluas dados pessoais reais nem segredos válidos. Se tiveres encontrado um segredo exposto, indica onde, sem o copiar.

<!-- TODO(owner): activar "Private vulnerability reporting" nas definições do repositório no GitHub. -->

## Princípios de segurança do projecto
- O modelo de linguagem **não** é uma fronteira de segurança. A autorização é determinística e fica fora do LLM (ADR-0004).
- O conteúdo externo (documentos, emails, páginas, repositórios) é tratado como não confiável.
- As operações seguem níveis de 1 a 6. As sensíveis exigem aprovação humana e ficam auditadas. As proibidas são sempre recusadas.
- Não há segredos no repositório. Os ficheiros de exemplo só têm valores fictícios e as demonstrações usam dados sintéticos.

## Âmbito
- **Dentro:** código, configuração, contratos e documentação deste repositório.
- **Fora:** serviços de terceiros, como os fornecedores de LLM e o GitHub, que se reportam aos respectivos responsáveis.
