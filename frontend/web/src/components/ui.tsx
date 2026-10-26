import { clsx, type ClassValue } from "clsx";
import React, {
  forwardRef,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type InputHTMLAttributes,
  type LabelHTMLAttributes,
  type ReactNode,
  useState,
  useEffect,
  useRef,
  useCallback,
} from "react";
import * as SelectPrimitive from "@radix-ui/react-select";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { Toaster as SonnerToaster, toast } from "sonner";
import { Check, ChevronDown, X } from "lucide-react";

export const cn = (...inputs: ClassValue[]) => clsx(inputs);

/* -------------------------------------------------------------------------- */
/* Button                                                                     */
/* -------------------------------------------------------------------------- */
type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: "sm" | "md" | "lg";
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "secondary", size = "md", className, ...props },
  ref,
) {
  const variants: Record<ButtonVariant, string> = {
    primary:
      "btn-primary-glow text-white font-semibold active:scale-[0.98]",
    secondary:
      "bg-raised/80 backdrop-blur-md text-ink border border-line hover:bg-hover hover:border-white/20 shadow-xs active:scale-[0.98]",
    ghost: "text-ink-2 hover:bg-hover hover:text-ink active:scale-[0.98]",
    danger:
      "border border-danger/40 bg-danger/10 text-danger hover:bg-danger/20 active:scale-[0.98]",
  };

  const sizes = {
    sm: "h-8 px-3 text-xs rounded-lg gap-1.5",
    md: "h-9 px-4 text-xs sm:text-sm rounded-xl gap-2",
    lg: "h-11 px-5 text-sm sm:text-base rounded-xl gap-2.5",
  };

  return (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center font-medium transition-all duration-150 cursor-pointer disabled:cursor-not-allowed disabled:opacity-40 disabled:pointer-events-none select-none tracking-tight",
        sizes[size],
        variants[variant],
        className,
      )}
      {...props}
    />
  );
});

/* -------------------------------------------------------------------------- */
/* Input & Form Primitives                                                   */
/* -------------------------------------------------------------------------- */
export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-9.5 w-full rounded-xl border border-line bg-subtle/80 px-3.5 text-sm text-ink",
        "placeholder:text-ink-3 focus:outline-none focus:border-line-focus focus:ring-2 focus:ring-line-focus/25 transition-all shadow-inner",
        className,
      )}
      {...props}
    />
  );
}

export function Textarea({
  className,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "w-full rounded-xl border border-line bg-subtle/80 p-3.5 text-sm text-ink",
        "placeholder:text-ink-3 focus:outline-none focus:border-line-focus focus:ring-2 focus:ring-line-focus/25 transition-all resize-y shadow-inner",
        className,
      )}
      {...props}
    />
  );
}

export function Label({ className, ...props }: LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={cn("mb-1.5 block text-xs font-semibold text-ink-2 uppercase tracking-wider", className)}
      {...props}
    />
  );
}

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("glass-card rounded-2xl p-6 shadow-xl", className)}
      {...props}
    />
  );
}

export function Badge({
  tone = "neutral",
  className,
  children,
  ...props
}: HTMLAttributes<HTMLSpanElement> & {
  tone?: "neutral" | "accent" | "danger" | "warn" | "ok";
}) {
  const tones = {
    neutral: "border-line bg-subtle/80 text-ink-2",
    accent: "border-accent/40 bg-accent/15 text-accent-ink shadow-[0_0_12px_-2px_rgba(59,130,246,0.3)]",
    danger: "border-danger/40 bg-danger/15 text-danger shadow-[0_0_12px_-2px_rgba(239,68,68,0.3)]",
    warn: "border-warn/40 bg-warn/15 text-warn shadow-[0_0_12px_-2px_rgba(245,158,11,0.3)]",
    ok: "border-ok/40 bg-ok/15 text-ok shadow-[0_0_12px_-2px_rgba(16,185,129,0.3)]",
  } as const;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tracking-tight backdrop-blur-xs",
        tones[tone],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}

export function Separator({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("h-px w-full bg-line-soft", className)} {...props} />;
}

export function Spinner({ className }: { className?: string }) {
  return (
    <svg
      className={cn("h-4 w-4 animate-spin text-accent", className)}
      viewBox="0 0 24 24"
      fill="none"
      role="status"
      aria-label="Loading"
    >
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeOpacity="0.2" strokeWidth="3" />
      <path d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function ErrorNote({ children, className }: { children: ReactNode; className?: string }) {
  if (children == null) return null;
  return (
    <p role="alert" className={cn("text-xs text-danger font-medium flex items-center gap-1.5 bg-danger/10 border border-danger/30 rounded-lg p-2.5", className)}>
      {children}
    </p>
  );
}

/* -------------------------------------------------------------------------- */
/* Skeleton                                                                   */
/* -------------------------------------------------------------------------- */
export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("ql-skeleton rounded-xl", className)}
      {...props}
    />
  );
}

/* -------------------------------------------------------------------------- */
/* Select (Radix UI)                                                          */
/* -------------------------------------------------------------------------- */
export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export function Select({
  value,
  onValueChange,
  defaultValue,
  options,
  placeholder = "Select...",
  disabled = false,
  className,
  "aria-label": ariaLabel,
  ariaLabel: ariaLabelProp,
  children,
}: {
  value?: string;
  onValueChange?: (val: string) => void;
  defaultValue?: string;
  options?: SelectOption[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  "aria-label"?: string;
  ariaLabel?: string;
  children?: ReactNode;
}) {
  const effectiveAriaLabel =
    ariaLabel || ariaLabelProp || (placeholder && placeholder !== "Select..." ? placeholder : "Select option");

  return (
    <SelectPrimitive.Root
      value={value}
      onValueChange={onValueChange}
      defaultValue={defaultValue}
      disabled={disabled}
    >
      <SelectPrimitive.Trigger
        aria-label={effectiveAriaLabel}
        className={cn(
          "inline-flex h-9 w-full items-center justify-between gap-2 rounded-xl border border-line bg-raised/80 backdrop-blur-md px-3 text-xs sm:text-sm text-ink",
          "hover:border-white/20 focus:outline-none focus:border-line-focus focus:ring-2 focus:ring-line-focus/25 disabled:opacity-40 transition-all cursor-pointer shadow-xs",
          className,
        )}
      >
        <SelectPrimitive.Value placeholder={placeholder} />
        <SelectPrimitive.Icon asChild>
          <ChevronDown className="h-4 w-4 text-ink-3 shrink-0" />
        </SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>

      <SelectPrimitive.Portal>
        <SelectPrimitive.Content
          className="z-50 min-w-[9rem] overflow-hidden rounded-xl border border-line/80 bg-raised/95 backdrop-blur-xl p-1.5 shadow-2xl text-ink animate-in fade-in-0 zoom-in-95"
          position="popper"
          sideOffset={6}
        >
          <SelectPrimitive.Viewport className="p-0.5">
            {options
              ? options.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value} disabled={opt.disabled}>
                    {opt.label}
                  </SelectItem>
                ))
              : children}
          </SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
      </SelectPrimitive.Portal>
    </SelectPrimitive.Root>
  );
}

export function SelectItem({
  value,
  disabled,
  className,
  children,
}: {
  value: string;
  disabled?: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    <SelectPrimitive.Item
      value={value}
      disabled={disabled}
      className={cn(
        "relative flex cursor-pointer select-none items-center rounded-lg py-2 pl-8 pr-3 text-xs sm:text-sm outline-none font-medium transition-colors",
        "data-[highlighted]:bg-hover data-[highlighted]:text-ink data-[disabled]:opacity-40 data-[disabled]:cursor-not-allowed",
        className,
      )}
    >
      <span className="absolute left-2.5 flex h-3.5 w-3.5 items-center justify-center">
        <SelectPrimitive.ItemIndicator>
          <Check className="h-4 w-4 text-accent" />
        </SelectPrimitive.ItemIndicator>
      </span>
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
  );
}

/* -------------------------------------------------------------------------- */
/* Tabs                                                                       */
/* -------------------------------------------------------------------------- */
interface TabsContextValue {
  activeTab: string;
  setActiveTab: (val: string) => void;
}

const TabsContext = React.createContext<TabsContextValue | null>(null);

export function Tabs({
  value,
  onValueChange,
  defaultValue = "",
  className,
  children,
}: {
  value?: string;
  onValueChange?: (val: string) => void;
  defaultValue?: string;
  className?: string;
  children: ReactNode;
}) {
  const [internalTab, setInternalTab] = useState(defaultValue);
  const activeTab = value !== undefined ? value : internalTab;
  const setActiveTab = (tab: string) => {
    if (value === undefined) setInternalTab(tab);
    onValueChange?.(tab);
  };

  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab }}>
      <div className={cn("w-full", className)}>{children}</div>
    </TabsContext.Provider>
  );
}

export function TabsList({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "inline-flex h-9.5 items-center justify-start rounded-xl bg-subtle/80 backdrop-blur-md p-1 text-ink-2 border border-line shadow-inner",
        className,
      )}
      role="tablist"
      {...props}
    />
  );
}

export function TabsTrigger({
  value,
  disabled,
  className,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { value: string }) {
  const ctx = React.useContext(TabsContext);
  const isActive = ctx?.activeTab === value;

  return (
    <button
      role="tab"
      value={value}
      aria-selected={isActive}
      disabled={disabled}
      onClick={() => ctx?.setActiveTab(value)}
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all cursor-pointer select-none",
        "disabled:opacity-40 disabled:cursor-not-allowed",
        isActive
          ? "bg-raised text-white border border-white/10 shadow-[0_2px_8px_-2px_rgba(0,0,0,0.5),inset_0_1px_0_0_rgba(255,255,255,0.1)]"
          : "text-ink-2 hover:text-white hover:bg-hover/50",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function TabsContent({
  value,
  className,
  children,
  ...props
}: HTMLAttributes<HTMLDivElement> & { value: string }) {
  const ctx = React.useContext(TabsContext);
  if (ctx?.activeTab !== value) return null;

  return (
    <div
      role="tabpanel"
      className={cn("mt-4 outline-none focus:ring-0 animate-in fade-in-0 duration-200", className)}
      {...props}
    >
      {children}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Dialog (Radix UI)                                                          */
/* -------------------------------------------------------------------------- */
export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;

export function DialogContent({
  className,
  children,
  ...props
}: DialogPrimitive.DialogContentProps & { className?: string; children: ReactNode }) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm transition-opacity duration-200 animate-in fade-in-0" />
      <DialogPrimitive.Content
        className={cn(
          "fixed left-[50%] top-[50%] z-50 w-full max-w-lg translate-x-[-50%] translate-y-[-50%] rounded-2xl border border-line bg-raised/95 backdrop-blur-2xl p-6 sm:p-8 shadow-2xl focus:outline-none animate-in fade-in-0 zoom-in-95 duration-200",
          className,
        )}
        {...props}
      >
        {children}
        <DialogPrimitive.Close className="absolute right-4 top-4 rounded-lg p-1.5 text-ink-3 hover:text-ink hover:bg-hover transition-colors">
          <X className="h-4 w-4" />
          <span className="sr-only">Close</span>
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

export function DialogHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("flex flex-col space-y-1.5 text-left mb-5", className)} {...props} />
  );
}

export function DialogTitle({ className, ...props }: DialogPrimitive.DialogTitleProps) {
  return (
    <DialogPrimitive.Title
      className={cn("text-xl font-bold tracking-tight text-ink font-display", className)}
      {...props}
    />
  );
}

export function DialogDescription({
  className,
  ...props
}: DialogPrimitive.DialogDescriptionProps) {
  return (
    <DialogPrimitive.Description
      className={cn("text-xs sm:text-sm text-ink-2 leading-relaxed", className)}
      {...props}
    />
  );
}

export function DialogFooter({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 mt-6 pt-4 border-t border-line-soft", className)}
      {...props}
    />
  );
}

/* -------------------------------------------------------------------------- */
/* ConfirmModal                                                               */
/* -------------------------------------------------------------------------- */
export function ConfirmModal({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "danger",
  onConfirm,
  onCancel,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "primary";
  onConfirm: () => void;
  onCancel?: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="ghost"
            onClick={() => {
              onCancel?.();
              onOpenChange(false);
            }}
          >
            {cancelLabel}
          </Button>
          <Button
            variant={variant}
            onClick={() => {
              onConfirm();
              onOpenChange(false);
            }}
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* -------------------------------------------------------------------------- */
/* Tooltip (Radix UI)                                                         */
/* -------------------------------------------------------------------------- */
export const TooltipProvider = TooltipPrimitive.Provider;
export const TooltipRoot = TooltipPrimitive.Root;
export const TooltipTrigger = TooltipPrimitive.Trigger;

export function Tooltip({
  content,
  children,
  side = "top",
}: {
  content: ReactNode;
  children: ReactNode;
  side?: "top" | "bottom" | "left" | "right";
}) {
  if (!content) return <>{children}</>;
  return (
    <TooltipPrimitive.Provider delayDuration={150}>
      <TooltipPrimitive.Root>
        <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
        <TooltipPrimitive.Portal>
          <TooltipPrimitive.Content
            side={side}
            sideOffset={5}
            className="z-50 overflow-hidden rounded-lg border border-white/10 bg-raised/95 backdrop-blur-md px-3 py-1.5 text-xs font-medium text-ink shadow-xl animate-in fade-in-0 zoom-in-95"
          >
            {content}
          </TooltipPrimitive.Content>
        </TooltipPrimitive.Portal>
      </TooltipPrimitive.Root>
    </TooltipPrimitive.Provider>
  );
}

/* -------------------------------------------------------------------------- */
/* Toast System                                                               */
/* -------------------------------------------------------------------------- */
export function ToastProvider() {
  return (
    <SonnerToaster
      theme="dark"
      position="bottom-right"
      toastOptions={{
        style: {
          background: "rgba(15, 19, 31, 0.95)",
          backdropFilter: "blur(16px)",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          color: "var(--ink)",
          boxShadow: "0 10px 30px -5px rgba(0,0,0,0.5)",
          borderRadius: "1rem",
        },
      }}
    />
  );
}

export { toast };

/* -------------------------------------------------------------------------- */
/* EmptyState                                                                 */
/* -------------------------------------------------------------------------- */
export function EmptyState({
  icon,
  illustration,
  title,
  description,
  action,
  className,
}: {
  icon?: ReactNode;
  illustration?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-10 text-center rounded-2xl border border-line bg-gradient-to-b from-raised/40 to-subtle/20 backdrop-blur-md",
        className,
      )}
    >
      {illustration ? (
        <div className="mb-4">{illustration}</div>
      ) : icon ? (
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-subtle border border-line text-accent shadow-inner">
          {icon}
        </div>
      ) : null}
      <h3 className="text-base font-bold text-ink font-display">{title}</h3>
      {description && (
        <p className="mt-1.5 text-xs sm:text-sm text-ink-3 max-w-sm leading-relaxed">{description}</p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* SplitPane (Resizable Divider)                                              */
/* -------------------------------------------------------------------------- */
export function SplitPane({
  split = "vertical",
  initialSize = 55,
  minSize = 25,
  maxSize = 75,
  storageKey,
  pane1,
  pane2,
  className,
}: {
  split?: "vertical" | "horizontal";
  initialSize?: number;
  minSize?: number;
  maxSize?: number;
  storageKey?: string;
  pane1: ReactNode;
  pane2: ReactNode;
  className?: string;
}) {
  const [size, setSize] = useState<number>(() => {
    if (storageKey) {
      const saved = localStorage.getItem(`ql-split-${storageKey}`);
      if (saved) {
        const parsed = parseFloat(saved);
        if (!isNaN(parsed) && parsed >= minSize && parsed <= maxSize) return parsed;
      }
    }
    return initialSize;
  });

  const isDragging = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDragging.current = true;
    document.body.style.cursor = split === "vertical" ? "row-resize" : "col-resize";
    document.body.style.userSelect = "none";
  }, [split]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      let newPercent = split === "vertical"
        ? ((e.clientY - rect.top) / rect.height) * 100
        : ((e.clientX - rect.left) / rect.width) * 100;

      newPercent = Math.max(minSize, Math.min(maxSize, newPercent));
      setSize(newPercent);
      if (storageKey) {
        localStorage.setItem(`ql-split-${storageKey}`, newPercent.toFixed(1));
      }
    };

    const handleMouseUp = () => {
      if (isDragging.current) {
        isDragging.current = false;
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      }
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [minSize, maxSize, split, storageKey]);

  return (
    <div
      ref={containerRef}
      className={cn(
        "flex w-full h-full overflow-hidden select-none",
        split === "vertical" ? "flex-col" : "flex-row",
        className,
      )}
    >
      <div
        style={{ [split === "vertical" ? "height" : "width"]: `${size}%` }}
        className="overflow-auto min-h-0 min-w-0"
      >
        {pane1}
      </div>

      {/* Resizer Handle */}
      <div
        onMouseDown={handleMouseDown}
        className={cn(
          "relative z-20 flex items-center justify-center bg-line hover:bg-accent/80 transition-colors shrink-0 group",
          split === "vertical"
            ? "h-2 w-full cursor-row-resize py-0.5 hover:h-2.5"
            : "w-2 h-full cursor-col-resize px-0.5 hover:w-2.5",
        )}
        title="Drag to resize split panes"
      >
        <div
          className={cn(
            "rounded-full bg-white/20 group-hover:bg-white transition-colors",
            split === "vertical" ? "h-1 w-10" : "w-1 h-10",
          )}
        />
      </div>

      <div
        style={{ [split === "vertical" ? "height" : "width"]: `${100 - size}%` }}
        className="overflow-auto min-h-0 min-w-0"
      >
        {pane2}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* DataTable                                                                  */
/* -------------------------------------------------------------------------- */
export interface ColumnDef<T = any> {
  key: string;
  label: string;
  render?: (value: any, row: T) => ReactNode;
  className?: string;
}

export function DataTable<T extends Record<string, any>>({
  columns,
  rows,
  emptyMessage = "No data available",
  className,
}: {
  columns: ColumnDef<T>[];
  rows: T[];
  emptyMessage?: string;
  className?: string;
}) {
  return (
    <div className={cn("w-full overflow-x-auto rounded-xl border border-line bg-raised/60 backdrop-blur-md shadow-sm", className)}>
      <table className="w-full text-left text-xs sm:text-sm text-ink">
        <thead className="bg-subtle/80 text-[11px] font-bold uppercase tracking-wider text-ink-3 border-b border-line">
          <tr>
            {columns.map((col) => (
              <th key={col.key} className={cn("px-4 py-3 font-semibold", col.className)}>
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line-soft">
          {rows.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-8 text-center text-ink-3 text-xs"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map((row, idx) => (
              <tr
                key={row.id ?? idx}
                className="hover:bg-white/[0.03] transition-colors"
              >
                {columns.map((col) => (
                  <td key={col.key} className={cn("px-4 py-3 text-xs sm:text-sm", col.className)}>
                    {col.render ? col.render(row[col.key], row) : (row[col.key] ?? "—")}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export { QuantumLogo, QuantumLogoIcon } from "./ui/QuantumLogo";
