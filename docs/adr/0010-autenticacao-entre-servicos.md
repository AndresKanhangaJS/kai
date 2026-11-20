# ADR-0010: Autenticação entre serviços: JWS assimétrico + rede privada

- **Estado:** Aceite (2026-11-20, D-06)
- **Data:** 2026-11-20
- **Decisores:** owner
- **Relacionados:** PDF p.13, p.20; ADR-0002, 0004

## Contexto
- O PDF pergunta qual será o mecanismo de autenticação entre serviços [C p.20].
- O AI Engine é o componente mais exposto a prompt injection. Não deve conseguir forjar autorizações (ADR-0004).

## Opções consideradas
1. **JWS assimétrico de curta duração + rede Docker privada + um utilizador RabbitMQ por serviço.** O Python verifica mas não consegue forjar.
2. **HMAC partilhado.** Mais simples, mas simétrico: quem verifica também consegue assinar.
3. **mTLS desde o início.** Identidade forte, mas há certificados para gerir, e não autentica a origem do payload depois de passar pelo broker.
4. **Só isolamento de rede.** Insuficiente: um contentor comprometido passa a confiar em tudo.

## Decisão
- **Opção 1.**
- O Python fica só numa rede Docker privada, sem porta exposta no host.
- **Laravel → Python:**
  - JWS com `aud`, `jti`, `scope` e validade ≤ 60 s;
  - os *execution grants* são também JWS, assinados pelo Laravel; o Python só tem a chave pública.
- **Python → Laravel:** usa uma chave própria do Python.
- **RabbitMQ:** um utilizador por serviço, com permissões mínimas no vhost.
- **mTLS:** só quando houver vários hosts.

## Consequências
- **Positivas:** o Python não consegue criar autorizações; cada mensagem é autenticada; serve para v1 e evolui sem ruptura.
- **Negativas:** distribuição e rotação de chaves; validação de JWS em cada pedido.

## Verificação
Testes negativos com:
- assinatura inválida;
- `aud` errado;
- token expirado;
- `jti` repetido.
