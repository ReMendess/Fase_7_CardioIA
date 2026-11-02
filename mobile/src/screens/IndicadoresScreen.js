import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { mensagemDoErro } from "../api/cliente.js";
import {
  listarAvaliacoes,
  listarLeituras,
  listarPacientes,
  obterAvaliacao,
} from "../api/endpoints.js";
import { useAuth } from "../contexts/AuthContext";
import { colors, fonts, radii, shadow, spacing } from "../theme";

const CLASSIFICACOES = {
  sem_pico_de_risco: { rotulo: "Sem pico de risco", cor: colors.online },
  pico_de_risco: { rotulo: "Pico de risco", cor: colors.error },
};

const STATUS = {
  CONCLUIDO: "Concluido",
  CONCLUIDO_COM_RESSALVAS: "Concluido com ressalvas",
  INCOMPLETO: "Incompleto",
  ERRO: "Erro",
};

function formatarData(iso) {
  if (!iso) return "--";
  const data = new Date(iso);
  return Number.isNaN(data.getTime()) ? String(iso) : data.toLocaleString("pt-BR");
}

/**
 * Indicadores cardiacos do paciente.
 *
 * Fontes:
 *
 * | Bloco | Origem |
 * |---|---|
 * | Paciente em foco | `GET /pacientes` |
 * | Risco | `GET /avaliacoes` + `GET /avaliacoes/{id}` (resultado preditivo) |
 * | Sinais vitais | `GET /iot/leituras` (telemetria do dispositivo) |
 *
 * A telemetria **nao e vinculada a paciente** no contrato §4.2 — os sinais vitais sao do
 * dispositivo, e a tela diz isso.
 */
export default function IndicadoresScreen() {
  const { usuario, logout } = useAuth();

  const [estado, setEstado] = useState({
    carregando: true,
    erro: null,
    paciente: null,
    diagnostico: null,
    avaliacao: null,
    leitura: null,
  });

  const carregar = useCallback(async () => {
    setEstado((atual) => ({ ...atual, carregando: true, erro: null }));
    try {
      const pacientes = await listarPacientes();
      const lista = Array.isArray(pacientes.dados) ? pacientes.dados : [];
      const paciente = lista[0] ?? null;

      let avaliacao = null;
      let diagnostico = null;
      if (paciente) {
        const resumos = await listarAvaliacoes({
          limite: 1,
          idPaciente: paciente.id_paciente,
        });
        const itens = Array.isArray(resumos.dados) ? resumos.dados : [];
        if (itens.length) {
          const detalhe = await obterAvaliacao(itens[0].id_execucao);
          avaliacao = detalhe.dados;
          diagnostico = avaliacao?.resposta?.diagnostico ?? null;
        }
      }

      const leituras = await listarLeituras({ limite: 1 });
      const listaDeLeituras = Array.isArray(leituras.dados) ? leituras.dados : [];

      setEstado({
        carregando: false,
        erro: null,
        paciente,
        diagnostico,
        avaliacao,
        leitura: listaDeLeituras[0] ?? null,
      });
    } catch (falha) {
      setEstado({
        carregando: false,
        erro: mensagemDoErro(falha),
        paciente: null,
        diagnostico: null,
        avaliacao: null,
        leitura: null,
      });
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const classificacao = CLASSIFICACOES[estado.diagnostico?.classificacao_risco];
  const probabilidade = estado.diagnostico?.probabilidade_risco;

  return (
    <ScrollView
      style={styles.tela}
      contentContainerStyle={styles.conteudo}
      refreshControl={<RefreshControl refreshing={false} onRefresh={carregar} />}
    >
      <View style={styles.cabecalho}>
        {/* `flex: 1` no bloco de texto: sem ele, um nome longo empurra o botao Sair
            para fora da tela em vez de quebrar a linha. */}
        <View style={styles.cabecalhoTexto}>
          <Text style={styles.titulo}>Indicadores cardiacos</Text>
          <Text style={styles.subtitulo}>
            {usuario?.nome} · {usuario?.papel}
          </Text>
        </View>
        <Pressable onPress={logout} accessibilityRole="button" accessibilityLabel="Sair">
          <Text style={styles.sair}>Sair</Text>
        </Pressable>
      </View>

      {estado.carregando && <ActivityIndicator color={colors.primary} />}

      {estado.erro && (
        <View style={styles.cartao}>
          <Text style={styles.erroTitulo}>Nao foi possivel carregar</Text>
          <Text style={styles.ajuda}>{estado.erro}</Text>
          <Pressable onPress={carregar} accessibilityRole="button">
            <Text style={styles.link}>Tentar de novo</Text>
          </Pressable>
        </View>
      )}

      {!estado.carregando && !estado.erro && (
        <>
          <View style={styles.cartao}>
            <Text style={styles.rotuloSecao}>Paciente em foco</Text>
            {estado.paciente ? (
              <>
                <Text style={styles.valorGrande}>{estado.paciente.nome}</Text>
                <Text style={styles.ajuda}>{estado.paciente.id_paciente}</Text>
              </>
            ) : (
              <Text style={styles.ajuda}>Nenhum paciente cadastrado.</Text>
            )}
          </View>

          <View style={styles.cartao}>
            <Text style={styles.rotuloSecao}>Risco de pico (resultado preditivo)</Text>
            {estado.diagnostico ? (
              <>
                <Text style={styles.valorGrande}>
                  {typeof probabilidade === "number"
                    ? `${(probabilidade * 100).toFixed(1)}%`
                    : "--"}
                </Text>
                <View style={styles.linha}>
                  <Text
                    style={[
                      styles.selo,
                      { backgroundColor: classificacao?.cor ?? colors.textMuted },
                    ]}
                  >
                    {classificacao?.rotulo ?? estado.diagnostico.classificacao_risco}
                  </Text>
                </View>
                <Text style={styles.ajuda}>
                  {estado.diagnostico.modelo_utilizado ?? "--"} ·{" "}
                  {formatarData(estado.avaliacao?.criado_em)}
                </Text>
              </>
            ) : (
              <Text style={styles.ajuda}>Este paciente ainda nao tem avaliacao.</Text>
            )}
          </View>

          <View style={styles.cartao}>
            <Text style={styles.rotuloSecao}>Sinais vitais (telemetria do dispositivo)</Text>
            {estado.leitura ? (
              <View style={styles.grade}>
                <Sinal rotulo="Frequencia" valor={estado.leitura.bpm} unidade="bpm" />
                <Sinal
                  rotulo="Temperatura"
                  valor={estado.leitura.temperatura}
                  unidade="°C"
                />
                <Sinal rotulo="Umidade" valor={estado.leitura.umidade} unidade="%" />
                <Sinal
                  rotulo="Luminosidade"
                  valor={estado.leitura.luminosidade}
                  unidade="lx"
                />
              </View>
            ) : (
              <Text style={styles.ajuda}>Nenhuma leitura recebida ainda.</Text>
            )}
            <Text style={styles.ajuda}>
              {estado.leitura?.id_dispositivo ?? "--"} ·{" "}
              {formatarData(estado.leitura?.recebido_em)}. Numeros do dispositivo, nao do
              paciente.
            </Text>
          </View>

          <View style={styles.cartao}>
            <Text style={styles.rotuloSecao}>Qualidade da resposta</Text>
            <Text style={styles.ajuda}>
              status: {STATUS[estado.avaliacao?.status] ?? estado.avaliacao?.status ?? "--"}
            </Text>
            {(estado.avaliacao?.avisos ?? []).slice(0, 3).map((aviso, indice) => (
              <Text style={styles.ajuda} key={indice}>
                · {aviso}
              </Text>
            ))}
            {(estado.avaliacao?.resposta?.limitacoes ?? [])
              .slice(0, 2)
              .map((item, indice) => (
                <Text style={styles.ajuda} key={`lim-${indice}`}>
                  · {item}
                </Text>
              ))}
          </View>

          <Text style={styles.rodape}>
            Dados sinteticos, sem validacao clinica. Nao e diagnostico nem prescricao.
          </Text>
        </>
      )}
    </ScrollView>
  );
}

function Sinal({ rotulo, valor, unidade }) {
  const ausente = valor === null || valor === undefined;
  return (
    <View style={styles.sinal}>
      <Text style={styles.ajuda}>{rotulo}</Text>
      <Text style={styles.valorSinal}>{ausente ? "--" : `${valor} ${unidade}`}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  tela: { flex: 1, backgroundColor: colors.background },
  conteudo: { padding: spacing.lg, rowGap: spacing.md },
  cabecalho: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
  },
  cabecalhoTexto: { flex: 1, marginRight: spacing.md },
  titulo: { fontSize: fonts.header, fontWeight: "700", color: colors.text },
  subtitulo: { fontSize: fonts.small, color: colors.textMuted },
  // `padding` aqui e area de toque, nao decoracao: o Android recomenda 48dp de alvo, e
  // um texto de 13pt sozinho fica bem abaixo disso.
  sair: {
    color: colors.primary,
    fontWeight: "700",
    fontSize: fonts.small,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.sm,
  },
  cartao: {
    backgroundColor: colors.surface,
    borderRadius: radii.banner,
    padding: spacing.lg,
    ...shadow,
  },
  rotuloSecao: {
    fontSize: fonts.small,
    fontWeight: "700",
    color: colors.textMuted,
    marginBottom: spacing.sm,
  },
  valorGrande: { fontSize: 30, fontWeight: "700", color: colors.text },
  valorSinal: { fontSize: 20, fontWeight: "700", color: colors.text },
  linha: { flexDirection: "row", marginVertical: spacing.sm },
  selo: {
    color: colors.white,
    fontSize: fonts.tiny,
    fontWeight: "700",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: 999,
    overflow: "hidden",
  },
  grade: { flexDirection: "row", flexWrap: "wrap", gap: spacing.lg },
  sinal: { minWidth: 120 },
  ajuda: { fontSize: fonts.tiny, color: colors.textMuted, marginTop: spacing.xs },
  erroTitulo: { fontSize: fonts.title, fontWeight: "700", color: colors.error },
  link: {
    marginTop: spacing.md,
    color: colors.primary,
    fontWeight: "700",
    fontSize: fonts.small,
  },
  rodape: {
    fontSize: fonts.tiny,
    color: colors.textMuted,
    textAlign: "center",
    paddingVertical: spacing.lg,
  },
});


