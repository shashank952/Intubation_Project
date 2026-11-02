import clsx from 'clsx';

type NeoLoaderVariant = 'inline' | 'block' | 'page';

interface NeoLoaderProps {
  variant?: NeoLoaderVariant;
  label?: string;
  className?: string;
}

const BLOCK_SIZES: Record<NeoLoaderVariant, string> = {
  inline: 'h-2 w-2',
  block: 'h-3.5 w-3.5',
  page: 'h-4 w-4',
};

function PulseBlocks({ variant }: { variant: NeoLoaderVariant }) {
  return (
    <span
      aria-hidden="true"
      className={clsx('inline-flex items-end', variant === 'inline' ? 'gap-1' : 'gap-1.5')}
    >
      {[0, 1, 2].map((index) => (
        <span
          key={index}
          className={clsx(
            'neo-loader-block border-2 border-black bg-brand-500',
            BLOCK_SIZES[variant]
          )}
          style={{ animationDelay: `${index * 130}ms` }}
        />
      ))}
    </span>
  );
}

function ScanBar({ className }: { className?: string }) {
  return (
    <div
      className={clsx(
        'relative overflow-hidden rounded-[2px] border-2 border-black bg-neutral-100 dark:border-neutral-600 dark:bg-neutral-800',
        className
      )}
    >
      <div aria-hidden="true" className="neo-loader-scan absolute inset-y-0 w-1/3 bg-brand-500" />
    </div>
  );
}

export default function NeoLoader({ variant = 'block', label, className }: NeoLoaderProps) {
  const statusText = label ?? 'Loading';

  if (variant === 'inline') {
    return (
      <span role="status" aria-live="polite" className={clsx('inline-flex items-center', className)}>
        <PulseBlocks variant="inline" />
        <span className="sr-only">{statusText}</span>
      </span>
    );
  }

  if (variant === 'page') {
    return (
      <div
        role="status"
        aria-live="polite"
        className={clsx('neo-loader-page-surface flex min-h-[100dvh] items-center justify-center', className)}
      >
        <svg
          aria-hidden="true"
          className="neo-loader-airway-mark h-16 w-16"
          viewBox="0 0 80 80"
          fill="none"
        >
          <path d="M12 39 34 16l23 22-21 23" />
        </svg>
        <span className="sr-only">{statusText}</span>
      </div>
    );
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className={clsx(
        'flex w-full flex-col items-center gap-3 rounded-[4px] border-2 border-black bg-white p-5 shadow-card dark:border-neutral-600 dark:bg-neutral-900',
        className
      )}
    >
      <ScanBar className="h-2.5 w-full max-w-[220px]" />
      <PulseBlocks variant="block" />
      <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-neutral-500 dark:text-neutral-400">
        {statusText}
      </p>
      <span className="sr-only">{statusText}</span>
    </div>
  );
}
