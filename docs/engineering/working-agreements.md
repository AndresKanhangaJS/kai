# Acordos de trabalho

Como o owner e o Claude Code trabalham juntos no KAI. Complementa o `CLAUDE.md`, que tem as regras de ouro, o workflow e a DoD.

## Fases e aprovações
- O trabalho avança em fases ou entregas pequenas. No fim de cada uma há um **relatório de fase** e uma **paragem até aprovação explícita** do owner.
- Nada é commitado antes de a fase ser aprovada. Push e PR exigem uma confirmação separada.
- O Claude Code nunca avança sozinho para a fase seguinte.

## Relatório de fase (modelo)
```
FASE N — <nome>
Feito:        <lista curta>
Evidência:    <ficheiros, outputs de comandos, fontes consultadas + data>
Por validar:  <o que não foi verificado e porquê>
Decisões [P]: <o que o owner tem de decidir, com recomendação>
Riscos/Notas: <se existirem>
Próximo passo proposto: <…> (aguardo aprovação)
```

## Rigor
- Etiquetas obrigatórias em afirmações de produto e arquitectura: **[C]** confirmado (PDF p.N, D-xx), **[H]** hipótese com justificação, **[P]** pendente.
- Factos actuais (versões, licenças, sintaxe de ferramentas) só se usam depois de verificados na fonte oficial, citando a fonte e a data. A memória do modelo não conta como fonte.
- "Pronto" exige evidência: output de comando, teste executado, ou ficheiro relido.
- Falhas e lacunas reportam-se explicitamente. Não se escondem nem se suavizam.

## Perguntas
- Decisões de escolha múltipla: perguntas interactivas, no máximo 4 por ronda, com a recomendação em primeiro lugar.
- Pergunta-se sempre que se aplica a secção "Quando parar e perguntar" do `CLAUDE.md`.

## Idioma
- Conversa: PT-PT, conciso e directo.
- Repositório: PT-PT (ADR-0012). Identificadores de código e tipos de commit em inglês.

## Ambiente
- O Claude Code corre dentro do WSL (Ubuntu), em `~/projects/kai` (D-04).
- Ferramentas novas (ex.: `jq`, PyYAML, servidores MCP) só se instalam com aprovação do owner.
