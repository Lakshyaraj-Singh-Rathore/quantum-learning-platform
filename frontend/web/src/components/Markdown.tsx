/**
 * Curriculum markdown, rendered the way Streamlit renders it.
 *
 * The lessons in /content are LaTeX-heavy (`$|0\rangle$`, display `$$…$$`) and
 * use GFM tables and fenced code, all of which Streamlit's st.markdown handles.
 * Dropping any of that would quietly delete half the curriculum, so the reader
 * carries the real plugins rather than a hand-rolled subset.
 */
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
// KaTeX's stylesheet is imported in main.tsx, not here: a CSS import in this
// module would break the Node render harnesses (scripts/render-*.mts), which
// load the real components outside a bundler.

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

export function Markdown({ children }: { children: string }) {
  return (
    <div className={STYLES}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
