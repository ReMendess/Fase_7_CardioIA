import { useReducer } from "react";

const initialState = {
  patient: "",
  date: "",
};

function reducer(state, action) {
  switch (action.type) {
    case "SET_FIELD":
      return { ...state, [action.field]: action.value };
    case "RESET":
      return initialState;
    default:
      return state;
  }
}

export default function Schedule() {
  const [state, dispatch] = useReducer(reducer, initialState);

  const handleSubmit = (e) => {
    e.preventDefault();
    console.log("Agendado:", state);
    dispatch({ type: "RESET" });
  };

  return (
    <section className="panel" aria-label="Agendamento">
      <h2 className="pageTitle">Agenda</h2>
      <p className="helper">Crie um agendamento rápido (exemplo com reducer).</p>

      <div style={{ height: 10 }} />

      <form onSubmit={handleSubmit} className="stack">
        <div>
          <input
            placeholder="Paciente"
            value={state.patient}
            onChange={(e) =>
              dispatch({
                type: "SET_FIELD",
                field: "patient",
                value: e.target.value,
              })
            }
          />
          <div className="helper">Ex.: Maria Silva</div>
        </div>

        <div>
          <input
            type="date"
            value={state.date}
            onChange={(e) =>
              dispatch({ type: "SET_FIELD", field: "date", value: e.target.value })
            }
          />
        </div>

        <div className="row">
          <button type="submit">Agendar</button>
          <button
            type="button"
            className="logoutBtn"
            onClick={() => dispatch({ type: "RESET" })}
          >
            Limpar
          </button>
        </div>

        <div className="mutedBox">
          Ao enviar, o agendamento aparece no console (demo).
        </div>
      </form>
    </section>
  );
}