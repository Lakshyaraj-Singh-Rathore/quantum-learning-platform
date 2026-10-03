/**
 * Keeps one broken component from taking down the whole app.
 *
 * Without this, any throw inside a page -- a demo fed an unexpected value, an
 * API response with a shape nobody expected, a null where an object was
 * assumed -- unmounts the entire React tree and leaves a blank screen with the
 * real cause only in the console. The user sees nothing and cannot navigate
 * away, because the navigation is part of what just unmounted.
 *
 * This is mounted around page content rather than around the whole app, so a
 * crash costs you the page and not the shell: the sidebar and top bar survive,
 * so you can go somewhere else, or retry, instead of reloading the tab.
 *
 * The error message is shown, not hidden. Swallowing it would make debugging
 * harder for the person who has to fix it, and for a self-hosted tool there
 * is no reason to hide what went wrong from the person running it.
 */
import { Component, type ErrorInfo, type ReactNode } from "react";

import { Button, Card } from "../ui";

interface Props {
  children: ReactNode;
  /** Where the boundary sits, so the message can say what stopped working. */
  label?: string;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Keep the component stack: the message alone often points at a shared
    // component used by ten pages, which is not enough to find the caller.
    console.error(`[${this.props.label ?? "page"}] crashed:`, error, info.componentStack);
  }

  private reset = () => this.setState({ error: null });

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    return (
      <div className="p-6">
        <Card className="border-danger/40 p-5">
          <h2 className="text-base font-semibold text-ink">
            {this.props.label ?? "This page"} stopped working
          </h2>
          <p className="mt-1 text-[13px] leading-relaxed text-ink-2">
            The rest of the app is fine — you can navigate to another page, or try again. If it
            keeps happening, the message below is the thing to report.
          </p>

          <pre className="mt-3 max-h-48 overflow-auto rounded-lg border border-line-soft bg-hover/60 p-3 font-mono text-[12px] leading-relaxed text-ink-2">
            {error.message || String(error)}
          </pre>

          <div className="mt-4 flex gap-2">
            <Button variant="primary" size="sm" onClick={this.reset}>
              Try again
            </Button>
            <Button size="sm" onClick={() => window.location.reload()}>
              Reload
            </Button>
          </div>
        </Card>
      </div>
    );
  }
}
