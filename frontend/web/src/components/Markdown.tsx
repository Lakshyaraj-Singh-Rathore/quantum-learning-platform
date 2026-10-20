/**
 * Curriculum markdown, rendered the way Streamlit renders it.
 *
 * The lessons in /content are LaTeX-heavy (`$|0\rangle$`, display `$$…$$`) and
 * use GFM tables and fenced code, all of which Streamlit's st.markdown handles.
 * Dropping any of that would quietly delete half the curriculum, so the reader
 * carries the real plugins rather than a hand-rolled subset.
 */
import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { Link, useInRouterContext } from "react-router-dom";
import hljs from "highlight.js/lib/core";
import python from "highlight.js/lib/languages/python";
import bash from "highlight.js/lib/languages/bash";
import json from "highlight.js/lib/languages/json";
import javascript from "highlight.js/lib/languages/javascript";
// KaTeX's stylesheet is imported in main.tsx, not here: a CSS import in this
// module would break the Node render harnesses (scripts/render-*.mts), which
// load the real components outside a bundler.

/**
 * Grammars the curriculum and code blocks can ask for. Every fenced block in
 * /content is Python or quantum frameworks; bash, json, and javascript cover tooling.
 */
hljs.registerLanguage("python", python);
hljs.registerLanguage("bash", bash);
hljs.registerLanguage("json", json);
hljs.registerLanguage("javascript", javascript);

/** Applied by <Markdown> to keep lesson body text on the app's type scale. */
const STYLES = [
  "text-[15px] leading-7 text-ink-2",
  "[&_h1]:mt-6 [&_h1]:mb-3 [&_h1]:text-2xl [&_h1]:font-semibold [&_h1]:tracking-tight [&_h1]:text-ink",
  "[&_h2]:mt-6 [&_h2]:mb-2 [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:text-ink",
  "[&_h3]:mt-4 [&_h3]:mb-2 [&_h3]:text-base [&_h3]:font-semibold [&_h3]:text-ink",
  "[&_p]:mb-3",
  "[&_ul]:mb-3 [&_ul]:list-disc [&_ul]:pl-6 [&_ol]:mb-3 [&_ol]:list-decimal [&_ol]:pl-6",
  "[&_li]:mb-1",
  "[&_strong]:font-semibold [&_strong]:text-ink",
  "[&_code]:rounded [&_code]:bg-hover [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[13px] [&_code]:text-ink",
  "[&_pre]:my-4 [&_pre]:overflow-auto [&_pre]:rounded-xl [&_pre]:border [&_pre]:border-white/10 [&_pre]:bg-[#080d1a] [&_pre]:p-4 [&_pre]:shadow-lg",
  "[&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_pre_code]:font-mono [&_pre_code]:text-[13px] [&_pre_code]:leading-relaxed",
  "[&_blockquote]:mb-3 [&_blockquote]:border-l-2 [&_blockquote]:border-line [&_blockquote]:pl-3 [&_blockquote]:italic [&_blockquote]:text-ink-3",
  "[&_table]:mb-3 [&_table]:w-full [&_table]:border-collapse [&_table]:text-sm",
  "[&_th]:border [&_th]:border-line-soft [&_th]:bg-hover/60 [&_th]:px-2 [&_th]:py-1 [&_th]:text-left [&_th]:font-semibold [&_th]:text-ink",
  "[&_td]:border [&_td]:border-line-soft [&_td]:px-2 [&_td]:py-1",
  "[&_a]:text-accent [&_a]:underline",
  "[&_hr]:my-5 [&_hr]:border-line-soft",
  // KaTeX display maths should not be squeezed onto one line by the prose styles.
  "[&_.katex-display]:my-4 [&_.katex-display]:overflow-x-auto",
].join(" ");

const LANGUAGE_CLASS = /language-([\w-]+)/;

type CodeProps = React.ComponentPropsWithoutRef<"code"> & {
  /**
   * react-markdown hands every custom component the underlying hast node.
   * It is not a DOM attribute, so it must be pulled out here rather than
   * spread — spreading it rendered `node="[object Object]"` onto every code
   * element.
   */
  node?: unknown;
};

/**
 * Fenced blocks get highlighted; inline code does not. The two are told apart
 * by the `language-*` class, which markdown only sets on a fenced block — an
 * inline span never carries one.
 */
function CodeBlock({ className, children, node: _node, ...rest }: CodeProps) {
  const rawLang = LANGUAGE_CLASS.exec(className ?? "")?.[1];
  const source = String(children).replace(/\n$/, "");
  const isBlock = Boolean(rawLang) || String(children).endsWith("\n") || source.includes("\n");

  const html = useMemo(() => {
    if (!isBlock) return null;
    const langMap: Record<string, string> = {
      py: "python",
      python: "python",
      python3: "python",
      qiskit: "python",
      cirq: "python",
      pennylane: "python",
      cudaq: "python",
      qasm: "python",
      openqasm: "python",
      sh: "bash",
      shell: "bash",
      bash: "bash",
      zsh: "bash",
      js: "javascript",
      javascript: "javascript",
      ts: "javascript",
      typescript: "javascript",
      json: "json",
    };
    const normalized = rawLang ? rawLang.toLowerCase() : "";
    const targetLang = normalized && (langMap[normalized] || hljs.getLanguage(normalized))
      ? (langMap[normalized] || normalized)
      : "python";

    try {
      if (hljs.getLanguage(targetLang)) {
        return hljs.highlight(source, { language: targetLang }).value;
      }
      return hljs.highlight(source, { language: "python" }).value;
    } catch {
      return null;
    }
  }, [source, rawLang, isBlock]);

  if (!isBlock || html === null) {
    return (
      <code className={className} {...rest}>
        {children}
      </code>
    );
  }

  return (
    <code
      className={className ? `${className} hljs` : "hljs"}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

/**
 * Lessons cross-reference each other by bare filename — `see 02_gates.md` —
 * because /content is a flat directory and that is how the files sit on disk.
 * Rendered raw, that href 404s: there is no .md route in the SPA. The slug is
 * exactly what LearnPage's `?lesson=<slug>` deep link already consumes, so the
 * link is rewritten to stay inside the app instead of leaving it.
 *
 * There are 344 of these across the 67 lessons (scripts/render-b5-check.mts
 * verifies every one of them resolves to a real file), so this is the
 * difference between the curriculum being a set of documents and being a
 * navigable one.
 */
const CROSS_LESSON_LINK = /^(\d{2}_[a-z0-9_]+)\.md$/i;

const EXTERNAL = /^https?:\/\//i;

type AnchorProps = React.ComponentPropsWithoutRef<"a"> & { node?: unknown };

function SmartLink({ href, children, node: _node, ...rest }: AnchorProps) {
  // Always called: this is what lets the component render under the Node
  // harnesses, which have no Router mounted.
  const inRouter = useInRouterContext();
  const slug = href ? CROSS_LESSON_LINK.exec(href)?.[1] : undefined;

  if (slug) {
    // A search-only `to` keeps the current pathname, so the link works from
    // /learn without this component needing to know where it is mounted.
    return inRouter ? (
      <Link to={`?lesson=${slug}`} {...rest}>
        {children}
      </Link>
    ) : (
      <a href={`?lesson=${slug}`} {...rest}>
        {children}
      </a>
    );
  }

  // Leaving the app on an unannounced new tab is its own small betrayal, so
  // off-site links say what they do and lock down window.opener.
  if (href && EXTERNAL.test(href)) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" {...rest}>
        {children}
      </a>
    );
  }

  return (
    <a href={href} {...rest}>
      {children}
    </a>
  );
}

export function Markdown({ children }: { children: string }) {
  return (
    <div className={STYLES}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false, output: "html" }]]}
        components={{ code: CodeBlock, a: SmartLink }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
