import { LoginPage } from "./LoginPage";

/** Landing page: directly serves the LoginPage so visitors can authenticate first. */
export function HomePage() {
  return <LoginPage mode="login" />;
}
