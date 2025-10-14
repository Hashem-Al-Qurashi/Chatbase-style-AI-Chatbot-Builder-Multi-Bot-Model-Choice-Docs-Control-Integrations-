import React from 'react';
import { cn } from '../../utils/cn';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'glass' | 'elegant' | 'glow';
  size?: 'sm' | 'md' | 'lg';
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'elegant', size = 'md', children, ...props }, ref) => {
    return (
      <div
        className={cn(
          'relative overflow-hidden transition-all duration-300',
          // Base styles
          'rounded-xl border backdrop-blur-sm',
          
          // Variants
          variant === 'default' && [
            'bg-white border-gray-200',
            'shadow-sm hover:shadow-md',
          ],
          
          variant === 'glass' && [
            'bg-white/10 border-white/20',
            'shadow-glass backdrop-blur-md',
            'hover:bg-white/20 hover:border-white/30',
            'before:absolute before:inset-0',
            'before:bg-glass-gradient before:opacity-50',
            'before:pointer-events-none',
          ],
          
          variant === 'elegant' && [
            'bg-white/95 border-gray-200/50',
            'shadow-elegant hover:shadow-2xl',
            'backdrop-blur-sm',
            'hover:bg-white',
            'hover:border-primary-200/50',
            'hover:shadow-primary-500/10',
          ],
          
          variant === 'glow' && [
            'bg-gradient-to-br from-white/90 to-gray-50/90',
            'border-primary-200/50',
            'shadow-glow hover:shadow-glow-lg',
            'hover:border-primary-300/50',
          ],
          
          // Sizes
          size === 'sm' && 'p-4',
          size === 'md' && 'p-6',
          size === 'lg' && 'p-8',
          
          className
        )}
        ref={ref}
        {...props}
      >
        {/* Glass effect overlay */}
        {variant === 'glass' && (
          <div className="absolute inset-0 bg-gradient-to-br from-white/10 via-transparent to-white/5 pointer-events-none" />
        )}
        
        {/* Content */}
        <div className="relative">
          {children}
        </div>
        
        {/* Subtle inner glow for elegant variant */}
        {variant === 'elegant' && (
          <div className="absolute inset-0 rounded-xl shadow-inner-glow pointer-events-none opacity-30" />
        )}
      </div>
    );
  }
);

Card.displayName = 'Card';

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {}

const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('flex flex-col space-y-1.5 pb-6', className)}
      {...props}
    />
  )
);
CardHeader.displayName = 'CardHeader';

export interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {}

const CardTitle = React.forwardRef<HTMLParagraphElement, CardTitleProps>(
  ({ className, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn(
        'font-display text-2xl font-bold leading-tight tracking-tight',
        'bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent',
        className
      )}
      {...props}
    />
  )
);
CardTitle.displayName = 'CardTitle';

export interface CardDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {}

const CardDescription = React.forwardRef<HTMLParagraphElement, CardDescriptionProps>(
  ({ className, ...props }, ref) => (
    <p
      ref={ref}
      className={cn('text-sm text-gray-500 font-medium', className)}
      {...props}
    />
  )
);
CardDescription.displayName = 'CardDescription';

export interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {}

const CardContent = React.forwardRef<HTMLDivElement, CardContentProps>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('', className)} {...props} />
  )
);
CardContent.displayName = 'CardContent';

export interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {}

const CardFooter = React.forwardRef<HTMLDivElement, CardFooterProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('flex items-center pt-6', className)}
      {...props}
    />
  )
);
CardFooter.displayName = 'CardFooter';

export { 
  Card, 
  CardHeader, 
  CardFooter, 
  CardTitle, 
  CardDescription, 
  CardContent 
};