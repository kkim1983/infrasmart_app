import { type ButtonHTMLAttributes, type ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  children: ReactNode;
}

const VARIANT_CLASSES = {
  primary: 'bg-[#2563EB] text-white hover:bg-[#1D4ED8] disabled:bg-blue-300',
  secondary: 'bg-white text-[#2563EB] border border-[#2563EB] hover:bg-[#EFF6FF]',
  danger: 'bg-[#EF4444] text-white hover:bg-red-600 disabled:bg-red-300',
  ghost: 'bg-transparent text-[#6B7280] hover:bg-gray-100',
};

const SIZE_CLASSES = {
  sm: 'px-3 py-1.5 text-sm rounded-lg',
  md: 'px-4 py-2.5 text-sm rounded-xl',
  lg: 'px-6 py-3 text-base rounded-xl',
};

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  children,
  disabled,
  className = '',
  ...props
}: ButtonProps) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`
        font-semibold transition-colors duration-150 flex items-center justify-center gap-2
        ${VARIANT_CLASSES[variant]}
        ${SIZE_CLASSES[size]}
        disabled:cursor-not-allowed
        ${className}
      `}
    >
      {loading && (
        <svg
          className="animate-spin h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      )}
      {children}
    </button>
  );
}
