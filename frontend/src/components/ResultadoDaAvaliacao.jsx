import { Link } from "react-router-dom";
import { ErroDaAPI } from "../api/cliente";
import { Avisos, Falha, Limitacoes, Origem } from "./Estado";
import Indicador from "./Indicador";
import NivelDeRisco from "./NivelDeRisco";
import { FEATURES_DO_MODELO } from "../dominio/catalogo";

/**
 * Renderizacao do resultado de `POST /avaliacoes`.
 *
 * Vive em modulo proprio porque a **mesma** estrutura aparece na tela de avaliacao e no
 * detalhe do historico — e o contrato da Fase 6 e grande (diagnostico, protocolos,
 * indicadores deterministas e trilha de execucao).
 */

/** Sucesso: risco + features do contrato + protocolos e trilha do pipeline. */
export function ResultadoDaAvaliacao({ envelope, titulo = "Resultado", featuresEnviadas = null }) {
  const contrato = envelope.dados;
  return (
    <section className="panel">
      <h3 className="panelTitle">
        {titulo}
        <Origem tipo="preditivo" />
      </h3>
      <NivelDeRisco diagnostico={contrato?.diagnostico} />
      <DetalhesDoContrato contrato={contrato} featuresEnviadas={featuresEnviadas} />
      <Avisos itens={envelope.avisos} titulo="Avisos" />
      <Limitacoes itens={envelope.limitacoes} />
    </section>
  );
}

/** Falha do pipeline — em `INCOMPLETO` o envelope ainda traz a trilha da Fase 6. */
export function ResultadoDaFalha({ falha }) {
  const parcial = falha instanceof ErroDaAPI ? falha.envelope?.dados : null;
  return (
    <section className="panel">
      <h3 className="panelTitle">A avaliacao nao foi concluida</h3>
      <Falha erro={falha} />
      {parcial && <DetalhesDoContrato contrato={parcial} />}
      <p className="helper" style={{ marginTop: 10 }}>
        A tentativa fica no <Link to="/historico">historico</Link> mesmo em falha — o
        registro conta o que aconteceu de fato.
      </p>
    </section>
  );
}

/**
 * Trilha do pipeline, protocolos e indicadores deterministas da Fase 6.
 *
 * ⚠️ **`diagnostico.features_utilizadas` e a lista de NOMES das 10 features**, nao os
 * valores — conferido contra a resposta real do backend. Os valores avaliados **nao
 * sao expostos** por nenhum endpoint hoje (ficam nas colunas de
 * `avaliacoes_de_risco`). Por isso as barras so aparecem quando quem chama passa
 * `featuresEnviadas` (o caso da tela de avaliacao, que acabou de receber os valores).
 * Inventa-los aqui seria apresentar dado que o backend nao devolveu.
 */
export function DetalhesDoContrato({ contrato, featuresEnviadas = null }) {
  if (!contrato) return null;
  const diagnostico = contrato.diagnostico ?? {};
  const nomesDasFeatures = Array.isArray(diagnostico.features_utilizadas)
    ? diagnostico.features_utilizadas
    : [];
  const justificativas = contrato.justificativas ?? [];
  const protocolos = contrato.protocolos ?? [];
  const indicadores = contrato.indicadores ?? [];
  const passos = contrato.passos ?? [];

  return (
    <div className="stack" style={{ marginTop: 14 }}>
      {featuresEnviadas ? (
        <div>
          <div className="blocoTitulo">Indicadores usados nesta avaliacao</div>
          <div className="gradeIndicadores">
            {FEATURES_DO_MODELO.map((feature) => (
              <Indicador
                key={feature.nome}
                feature={feature}
                valor={featuresEnviadas[feature.nome] ?? ""}
              />
            ))}
          </div>
        </div>
      ) : (
        nomesDasFeatures.length > 0 && (
          <div className="bloco">
            <div className="blocoTitulo">
              Features do contrato usadas pelo modelo ({nomesDasFeatures.length})
            </div>
            <div className="row" style={{ flexWrap: "wrap" }}>
              {nomesDasFeatures.map((nome) => (
                <span className="etiqueta" key={nome}>
                  {nome}
                </span>
              ))}
            </div>
            <p className="helper" style={{ marginTop: 8 }}>
              A API devolve os <strong>nomes</strong> das features usadas, nao os valores:
              eles ficam no registro persistido e nao sao expostos por nenhum endpoint.
            </p>
          </div>
        )
      )}

      {contrato.narrativa && (
        <div className="bloco">
          <div className="blocoTitulo">Narrativa da execucao</div>
          <p style={{ whiteSpace: "pre-wrap" }}>{contrato.narrativa}</p>
        </div>
      )}

      {justificativas.length > 0 && (
        <div className="bloco">
          <div className="blocoTitulo">Justificativas ({justificativas.length})</div>
          <ul className="listaSimples">
            {justificativas.map((texto, indice) => (
              <li key={indice}>{texto}</li>
            ))}
          </ul>
        </div>
      )}

      {protocolos.length > 0 && (
        <div className="bloco">
          <div className="blocoTitulo">Protocolos aplicaveis ({protocolos.length})</div>
          <div className="list">
            {protocolos.map((protocolo, indice) => (
              <div className="listItem" key={protocolo.identificador ?? indice}>
                <div>
                  <div className="listItemTitle">{protocolo.identificador}</div>
                  <div className="helper">{protocolo.acao}</div>
                  <div className="helper">{protocolo.texto_oficial}</div>
                </div>
                <span
                  className={`pill ${protocolo.condicao_satisfeita ? "" : "pill--inativo"}`}
                >
                  {protocolo.condicao_satisfeita ? "satisfeito" : "nao satisfeito"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}


      {indicadores.length > 0 && (
        <div className="bloco">
          <div className="blocoTitulo">Indicadores deterministas ({indicadores.length})</div>
          <div className="list">
            {indicadores.map((indicador, indice) => (
              <div className="listItem" key={indicador.nome ?? indice}>
                <div>
                  <div className="listItemTitle">{indicador.nome}</div>
                  <div className="mono helper">
                    {indicador.coluna} {indicador.operador} {indicador.limiar} · observado{" "}
                    {indicador.valor_observado}
                  </div>
                </div>
                <span className={`pill ${indicador.satisfeito ? "" : "pill--inativo"}`}>
                  {indicador.satisfeito ? "sim" : "nao"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {passos.length > 0 && (
        <details className="bloco bloco--limitacoes">
          <summary>Trilha de execucao ({passos.length} passos)</summary>
          <div className="list" style={{ marginTop: 10 }}>
            {passos.map((passo, indice) => (
              <div className="listItem" key={`${passo.ordem}-${indice}`}>
                <div>
                  <div className="listItemTitle">
                    {passo.ordem}. {passo.tipo}
                  </div>
                  <div className="helper">
                    {passo.agente} · {passo.detalhe}
                  </div>
                </div>
                <span className={`pill ${passo.sucesso ? "" : "pill--inativo"}`}>
                  {passo.sucesso ? "ok" : "falhou"}
                </span>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
