/**
 * Configuracao da camada de API — item 4 da Etapa D ("centralizar a URL da API em
 * variavel de ambiente").
 *
 * `VITE_API_URL` e lida pelo Vite em tempo de build. Fora do Vite (por exemplo no
 * script de smoke test rodando em Node) `import.meta.env` nao existe, e o valor
 * padrao local assume. Isso e proposital: permite executar **esta mesma camada**
 * contra o backend real, sem navegador, para validar a integracao.
 */

/** Valor lido do ambiente de build (Vite) ou do processo (Node). */
const AMBIENTE = import.meta.env ?? {};
const PROCESSO = globalThis.process ?? {};
const DO_AMBIENTE = AMBIENTE.VITE_API_URL ?? PROCESSO.env?.VITE_API_URL;

/** URL base da API, sem barra final. */
export const URL_DA_API = (DO_AMBIENTE || "http://127.0.0.1:8000/api/v1").replace(
  /\/+$/,
  ""
);

/** Tempo maximo de espera de uma chamada, em milissegundos. */
export const TEMPO_LIMITE_MS = 30000;

/** Prefixo das rotas, usado apenas para montar caminhos legiveis. */
export const VERSAO_DA_API = "v1";

