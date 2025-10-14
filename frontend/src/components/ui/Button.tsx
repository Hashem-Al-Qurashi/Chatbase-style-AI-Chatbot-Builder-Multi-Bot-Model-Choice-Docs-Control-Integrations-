import React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'outline' | 'gradient' | 'glow' | 'danger';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ 
    className, 
    variant = 'primary', 
    size = 'md', 
    loading = false,
    icon,
    iconPosition = 'left',
    children,
    disabled,
    ...props 
  }, ref) => {
    return (
      <button
        className={cn(
          // Base styles
          'relative inline-flex items-center justify-center font-medium transition-all duration-200',
          'focus:outline-none focus:ring-2 focus:ring-offset-2',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'overflow-hidden group',
          
          // Size variants
          size === 'sm' && 'px-3 py-1.5 text-xs rounded-lg h-8',
          size === 'md' && 'px-4 py-2 text-sm rounded-xl h-10',
          size === 'lg' && 'px-6 py-3 text-base rounded-xl h-12',
          size === 'xl' && 'px-8 py-4 text-lg rounded-xl h-14',
          
          // Color variants
          variant === 'primary' && [
            'bg-gradient-to-r from-primary-600 to-primary-700',
            'text-white shadow-lg shadow-primary-500/25',
            'hover:from-primary-700 hover:to-primary-800 hover:shadow-xl hover:shadow-primary-500/30',
            'focus:ring-primary-500 focus:ring-offset-2',
            'active:scale-[0.98] active:shadow-md',
            // Shimmer effect with pointer-events fix
            'before:absolute before:inset-0 before:-translate-x-full before:pointer-events-none',
            'before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent',
            'hover:before:translate-x-full before:transition-transform before:duration-700',
          ],
          
          variant === 'secondary' && [
            'bg-white border border-gray-300 text-gray-700',
            'shadow-sm hover:shadow-md hover:bg-gray-50',
            'focus:ring-primary-500 focus:border-primary-500',
            'active:scale-[0.98]',
          ],
          
          variant === 'ghost' && [
            'text-gray-600 hover:text-gray-900 hover:bg-gray-100',
            'focus:ring-gray-500',
            'active:scale-[0.98]',
          ],
          
          variant === 'outline' && [
            'border-2 border-primary-600 text-primary-600 bg-transparent',
            'hover:bg-primary-600 hover:text-white hover:shadow-lg hover:shadow-primary-500/25',
            'focus:ring-primary-500',
            'active:scale-[0.98]',
            'transition-all duration-200',
          ],
          
          variant === 'gradient' && [
            'bg-gradient-to-br from-primary-500 via-primary-600 to-accent-600',
            'text-white shadow-lg shadow-primary-500/30',
            'hover:shadow-xl hover:shadow-primary-500/40 hover:scale-[1.02]',
            'focus:ring-primary-500',
            'active:scale-[0.98]',
            // Animated gradient with pointer-events fix
            'bg-size-200 hover:bg-pos-0',
            'before:absolute before:inset-0 before:-translate-x-full before:pointer-events-none',
            'before:bg-gradient-to-r before:from-transparent before:via-white/30 before:to-transparent',
            'hover:before:translate-x-full before:transition-transform before:duration-1000',
          ],
          
          variant === 'glow' && [
            'bg-gradient-to-r from-primary-600 to-primary-700',
            'text-white shadow-glow',
            'hover:shadow-glow-lg hover:from-primary-700 hover:to-primary-800',
            'focus:ring-primary-500 focus:ring-offset-2',
            'active:scale-[0.98]',
            'animate-pulse-gentle',
          ],
          
          variant === 'danger' && [
            'bg-gradient-to-r from-red-600 to-red-700',
            'text-white shadow-lg shadow-red-500/25',
            'hover:from-red-700 hover:to-red-800 hover:shadow-xl hover:shadow-red-500/30',
            'focus:ring-red-500 focus:ring-offset-2',
            'active:scale-[0.98] active:shadow-md',
            // Shimmer effect with pointer-events fix
            'before:absolute before:inset-0 before:-translate-x-full before:pointer-events-none',
            'before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent',
            'hover:before:translate-x-full before:transition-transform before:duration-700',
          ],
          
          className
        )}
        disabled={disabled || loading}
        ref={ref}
        {...props}
      >
        {/* Loading spinner */}
        {loading && (
          <Loader2 className={cn(
            'animate-spin',
            size === 'sm' && 'w-3 h-3',
            size === 'md' && 'w-4 h-4',
            size === 'lg' && 'w-5 h-5',
            size === 'xl' && 'w-6 h-6',
            children && 'mr-2'
          )} />
        )}
        
        {/* Left icon */}
        {!loading && icon && iconPosition === 'left' && (
          <span className={cn(
            'flex items-center',
            children && 'mr-2',
            size === 'sm' && '[&>*]:w-3 [&>*]:h-3',
            size === 'md' && '[&>*]:w-4 [&>*]:h-4',
            size === 'lg' && '[&>*]:w-5 [&>*]:h-5',
            size === 'xl' && '[&>*]:w-6 [&>*]:h-6',
          )}>
            {icon}
          </span>
        )}
        
        {/* Button text */}
        {children && (
          <span className="relative z-10">
            {children}
          </span>
        )}
        
        {/* Right icon */}
        {!loading && icon && iconPosition === 'right' && (
          <span className={cn(
            'flex items-center',
            children && 'ml-2',
            size === 'sm' && '[&>*]:w-3 [&>*]:h-3',
            size === 'md' && '[&>*]:w-4 [&>*]:h-4',
            size === 'lg' && '[&>*]:w-5 [&>*]:h-5',
            size === 'xl' && '[&>*]:w-6 [&>*]:h-6',
          )}>
            {icon}
          </span>
        )}
        
        {/* Ripple effect container */}
        <span className="absolute inset-0 overflow-hidden rounded-xl pointer-events-none">
          <span className="absolute inset-0 bg-white/10 opacity-0 group-active:opacity-100 transition-opacity duration-75" />
        </span>
      </button>
    );
  }
);

Button.displayName = 'Button';

export { Button };