/**
 * Paciente selecionado, compartilhado entre as telas.
 *
 * Por que um contexto: o Dashboard, o Historico e a Avaliacao giram em torno do
 * **mesmo** paciente. Sem isso, cada tela recarregaria a lista e o usuario perderia a
 * selecao ao navegar (item 3 da Etapa D: "identificacao clara do paciente selecionado").
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { criarPaciente, listarPacientes } from "../api/endpoints";

/* Mesma justificativa de `AuthContext.jsx`: contexto + hook + provedor no mesmo arquivo
   e o padrao documentado do React; a regra existe apenas por causa do HMR. */
/* eslint-disable react-refresh/only-export-components */

export const PacienteContext = createContext(null);

export function usePacientes() {
  const ctx = useContext(PacienteContext);
  if (!ctx) throw new Error("usePacientes deve ser usado dentro de PacienteProvider");
  return ctx;
}

export function PacienteProvider({ children }) {
  const [pacientes, setPacientes] = useState([]);
  const [selecionado, setSelecionado] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);

  const recarregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const envelope = await listarPacientes();
      // `dados` e uma lista (contrato §8), nao um objeto paginado.
      const lista = Array.isArray(envelope.dados) ? envelope.dados : [];
      setPacientes(lista);
      setSelecionado((atual) => {
        if (atual && lista.some((p) => p.id_paciente === atual.id_paciente)) return atual;
        return lista[0] ?? null;
      });
    } catch (falha) {
      setErro(falha);
      setPacientes([]);
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    recarregar();
  }, [recarregar]);

  /** Cria o paciente no backend e ja o seleciona. */
  const cadastrar = useCallback(async (nome) => {
    const envelope = await criarPaciente(nome);
    const novo = envelope.dados;
    setPacientes((atuais) => [novo, ...atuais]);
    setSelecionado(novo);
    return novo;
  }, []);

  const valor = useMemo(
    () => ({
      pacientes,
      selecionado,
      selecionar: setSelecionado,
      carregando,
      erro,
      recarregar,
      cadastrar,
    }),
    [pacientes, selecionado, carregando, erro, recarregar, cadastrar]
  );

  return <PacienteContext.Provider value={valor}>{children}</PacienteContext.Provider>;
}
