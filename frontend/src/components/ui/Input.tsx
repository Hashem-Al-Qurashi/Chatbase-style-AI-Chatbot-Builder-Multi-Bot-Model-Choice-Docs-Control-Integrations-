import React, { forwardRef, useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
  label?: string;
  hint?: string;
  variant?: 'default' | 'elegant' | 'floating';
  icon?: React.ReactNode;
  showPasswordToggle?: boolean;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ 
    className, 
    type, 
    error, 
    label, 
    hint,
    variant = 'elegant',
    icon,
    showPasswordToggle = false,
    value,
    placeholder,
    ...props 
  }, ref) => {
    const [showPassword, setShowPassword] = useState(false);
    const [isFocused, setIsFocused] = useState(false);
    const actualType = showPasswordToggle && showPassword ? 'text' : type;
    const hasValue = Boolean(value && value.toString().length > 0);
    
    const inputElement = (
      <div className="relative">
        {/* Icon */}
        {icon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 transition-colors duration-200">
            {icon}
          </div>
        )}
        
        {/* Input */}
        <input
          type={actualType}
          className={cn(
            // Base styles
            'w-full transition-all duration-200 outline-none',
            'text-gray-900 placeholder:text-gray-400',
            
            // Variant styles
            variant === 'default' && [
              'h-10 rounded-lg border border-gray-300 bg-white px-3 py-2',
              'focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20',
              'hover:border-gray-400',
            ],
            
            variant === 'elegant' && [
              'h-12 rounded-xl border border-gray-200 bg-white/50 px-4 py-3',
              'backdrop-blur-sm',
              'focus:border-primary-400 focus:bg-white focus:shadow-lg focus:shadow-primary-500/10',
              'hover:border-gray-300 hover:bg-white/70',
              'focus:ring-4 focus:ring-primary-500/10',
            ],
            
            variant === 'floating' && [
              'h-14 rounded-xl border border-gray-200 bg-white/50 px-4 pt-6 pb-2',
              'backdrop-blur-sm peer',
              'focus:border-primary-400 focus:bg-white focus:shadow-lg focus:shadow-primary-500/10',
              'hover:border-gray-300 hover:bg-white/70',
              'focus:ring-4 focus:ring-primary-500/10',
            ],
            
            // Icon spacing
            icon && !showPasswordToggle && 'pl-10',
            icon && showPasswordToggle && 'pl-10 pr-10',
            !icon && showPasswordToggle && 'pr-10',
            
            // Error styles
            error && [
              'border-error-400 focus:border-error-500 focus:ring-error-500/20',
              'bg-error-50/50',
            ],
            
            // Disabled styles
            'disabled:opacity-50 disabled:cursor-not-allowed',
            
            className
          )}
          ref={ref}
          value={value}
          placeholder={variant === 'floating' ? ' ' : placeholder}
          onFocus={(e) => {
            setIsFocused(true);
            props.onFocus?.(e);
          }}
          onBlur={(e) => {
            setIsFocused(false);
            props.onBlur?.(e);
          }}
          {...props}
        />
        
        {/* Floating Label */}
        {variant === 'floating' && label && (
          <label
            className={cn(
              'absolute left-4 transition-all duration-200 pointer-events-none',
              'text-gray-500 font-medium',
              (isFocused || hasValue) ? [
                'top-2 text-xs text-primary-600',
                error && 'text-error-600'
              ] : [
                'top-1/2 -translate-y-1/2 text-base',
                error && 'text-error-500'
              ]
            )}
          >
            {label}
          </label>
        )}
        
        {/* Password Toggle */}
        {showPasswordToggle && type === 'password' && (
          <button
            type="button"
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors duration-200 focus:outline-none focus:text-primary-600"
            onClick={() => setShowPassword(!showPassword)}
          >
            {showPassword ? (
              <EyeOff size={18} />
            ) : (
              <Eye size={18} />
            )}
          </button>
        )}
      </div>
    );

    if (variant === 'floating') {
      return inputElement;
    }

    return (
      <div className="space-y-2">
        {/* Standard Label */}
        {label && (
          <label className={cn(
            'text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70',
            error ? 'text-error-600' : 'text-gray-700'
          )}>
            {label}
          </label>
        )}
        
        {inputElement}
        
        {/* Hint Text */}
        {hint && (
          <p className={cn(
            'text-xs',
            error ? 'text-error-600' : 'text-gray-500'
          )}>
            {hint}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export { Input };