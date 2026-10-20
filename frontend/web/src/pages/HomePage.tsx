import { Navigate } from "react-router-dom";
import { useSession } from "../state/session";

/** Thin route redirect wrapper: logged-in -> /learn; logged-out -> /login */
export function HomePage() {
  const token = useSession((s) => s.token);
  if (token) {
    return <Navigate to="/learn" replace />;
  }
  return <Navigate to="/login" replace />;
}
