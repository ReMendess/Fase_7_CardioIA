import { Navigate } from "react-router-dom";
import { useContext } from "react";
import { AuthContext } from "../contexts/AuthContext";

export default function ProtectedRoute({ children }) {
  const { usuario, loading } = useContext(AuthContext);

  if (loading) return <p>Carregando...</p>;

  if (!usuario) {
    return <Navigate to="/" />;
  }

  return children;
}