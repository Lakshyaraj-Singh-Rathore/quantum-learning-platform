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
import hljs from "highlight.js/lib/core";
import python from "highlight.js/lib/languages/python";
import bash from "highlight.js/lib/languages/bash";
import json from "highlight.js/lib/languages/json";
// KaTeX's stylesheet is imported in main.tsx, not here: a CSS import in this
// module would break the Node render harnesses (scripts/render-*.mts), which
// load the real components outside a bundler.

/**
 * Only the grammars the curriculum can actually ask for. Every fenced block in
 * /content is Python; bash and json cover anything the lesson text adds later.
 *
 * This uses highlight.js' `core` build with explicit language registration
 * rather than the rehype-highlight plugin. rehype-highlight statically imports
 * lowlight's `common` set (~35 grammars) at module scope, so *every* one of
 * them ends up in the bundle no matter what you pass as `languages`; going
 * through core keeps the bundle to the three we named.
 *
 * An unregistered or absent fence language is left uncoloured rather than
 * guessed at: mis-highlighting a block is worse than not highlighting it.
 */
hljs.registerLanguage("python", python);
hljs.registerLanguage("bash", bash);
hljs.registerLanguage("json", json);

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
  "[&_pre]:mb-3 [&_pre]:overflow-auto [&_pre]:rounded-lg [&_pre]:border [&_pre]:border-line-soft [&_pre]:bg-hover/60 [&_pre]:p-3",
  "[&_pre_code]:bg-transparent [&_pre_code]:p-0",
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
  const language = LANGUAGE_CLASS.exec(className ?? "")?.[1];

  const html = useMemo(() => {
    if (!language || !hljs.getLanguage(language)) return null;
    // Strip the trailing newline markdown leaves on the block; without this the
    // highlighted output ends in an empty line inside the <pre>.
    const source = String(children).replace(/\n$/, "");
    // highlight() escapes the source it is given, so the result is markup we
    // generated ourselves rather than markup that came from the lesson text.
    return hljs.highlight(source, { language }).value;
  }, [children, language]);

  if (html === null) {
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

export function Markdown({ children }: { children: string }) {
  return (
    <div className={STYLES}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
        components={{ code: CodeBlock }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
