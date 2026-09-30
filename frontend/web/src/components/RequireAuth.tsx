import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { me } from "../api/auth";
import { useSession } from "../state/session";

/** Token in storage is the gate; /auth/me runs in the background to refresh
 * identity and to notice a rejected token (the api client clears the session
 * on 401). A slow or down API therefore never blocks the shell — same
 * forgiving posture the frozen Streamlit session takes, with the API still
 * as the sole authority for anything that actually reads data. */
export function RequireAuth() {
  const token = useSession((s) => s.token);
  const setUser = useSession((s) => s.setUser);
  const location = useLocation();

  const { data } = useQuery({
    queryKey: ["me"],
    queryFn: me,
    enabled: !!token,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (data) setUser(data);
  }, [data, setUser]);

  if (!token) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  return <Outlet />;
}
