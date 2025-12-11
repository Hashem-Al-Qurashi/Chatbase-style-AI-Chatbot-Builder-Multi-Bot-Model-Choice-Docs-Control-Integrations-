// Modern Registration form component with elegant styling

import React, { useState, FormEvent, useMemo } from 'react';
import { Mail, Lock, User, UserPlus, Sparkles, Check, X } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { RegisterRequest } from '../../types';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../ui/Card';

interface RegisterFormProps {
  onSuccess?: () => void;
  onSwitchToLogin?: () => void;
}

interface PasswordStrength {
  score: number;
  feedback: string[];
  color: string;
  label: string;
}

export function RegisterForm({ onSuccess, onSwitchToLogin }: RegisterFormProps) {
  const { register } = useAuth();
  const [formData, setFormData] = useState<RegisterRequest>({
    email: '',
    password: '',
    password_confirm: '',
    first_name: '',
    last_name: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
  const [focusedField, setFocusedField] = useState<string | null>(null);

  // Password strength checker
  const passwordStrength: PasswordStrength = useMemo(() => {
    const password = formData.password;
    if (!password) return { score: 0, feedback: [], color: 'gray', label: '' };

    let score = 0;
    const feedback: string[] = [];

    if (password.length >= 8) {
      score += 1;
    } else {
      feedback.push('At least 8 characters');
    }

    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) {
      score += 1;
    } else {
      feedback.push('Mix of uppercase & lowercase');
    }

    if (/\d/.test(password)) {
      score += 1;
    } else {
      feedback.push('Include numbers');
    }

    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
      score += 1;
    } else {
      feedback.push('Include special characters');
    }

    const colors = ['error', 'warning', 'warning', 'success', 'success'];
    const labels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];

    return {
      score,
      feedback,
      color: colors[score] || 'gray',
      label: labels[score] || ''
    };
  }, [formData.password]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    // Validate password confirmation
    if (formData.password !== formData.password_confirm) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    // Password strength validation
    if (passwordStrength.score < 2) {
      setError('Please choose a stronger password');
      setLoading(false);
      return;
    }

    try {
      await register(formData);
      setError(null);
      setFieldErrors({});
      onSuccess?.();
    } catch (err: any) {
      console.error('Registration error:', err);
      
      // Handle field-specific errors from API
      if (err.details && err.details.fieldErrors) {
        setFieldErrors(err.details.fieldErrors);
        setError('Please fix the errors below and try again.');
      } else {
        setError(err.message || 'Registration failed. Please try again.');
        setFieldErrors({});
      }
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const fieldName = e.target.name;
    setFormData(prev => ({
      ...prev,
      [fieldName]: e.target.value,
    }));
    
    // Clear field error when user starts typing
    if (fieldErrors[fieldName]) {
      setFieldErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[fieldName];
        return newErrors;
      });
    }
  };

  // Helper to get field error message
  const getFieldError = (fieldName: string): string | undefined => {
    return fieldErrors[fieldName]?.[0]; // Show first error for field
  };

  // Helper to check if field has error
  const hasFieldError = (fieldName: string): boolean => {
    return !!(fieldErrors[fieldName] && fieldErrors[fieldName].length > 0);
  };

  const passwordsMatch = formData.password && formData.password_confirm && 
                        formData.password === formData.password_confirm;
  const passwordsDontMatch = formData.password_confirm && 
                           formData.password !== formData.password_confirm;

  return (
    <div className="w-full max-w-lg mx-auto animate-slide-up">
      {/* Background Decorative Elements */}
      <div className="absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-32 -left-32 w-96 h-96 bg-gradient-to-br from-accent-500/15 to-primary-500/15 rounded-full blur-3xl animate-float" />
        <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-gradient-to-br from-primary-500/15 to-accent-500/15 rounded-full blur-3xl animate-float" style={{animationDelay: '1.5s'}} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-gradient-to-br from-primary-400/10 to-accent-400/10 rounded-full blur-2xl animate-pulse-gentle" />
      </div>

      <Card variant="elegant" size="lg" className="relative backdrop-blur-fix">
        <CardHeader className="text-center space-y-4">
          {/* Logo/Brand Icon */}
          <div className="mx-auto w-16 h-16 bg-gradient-to-br from-accent-500 to-primary-500 rounded-2xl flex items-center justify-center shadow-lg shadow-accent-500/25 animate-bounce-gentle">
            <Sparkles className="w-8 h-8 text-white" />
          </div>
          
          <CardTitle className="text-3xl gradient-text-elegant">
            Join Our Platform
          </CardTitle>
          <CardDescription className="text-base">
            Create your account and start your journey with us
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Error Message */}
          {error && (
            <div className="bg-gradient-to-r from-error-50 to-error-100 border border-error-200 text-error-700 px-4 py-3 rounded-xl animate-slide-down">
              <div className="flex items-center space-x-2">
                <X size={16} className="text-error-500" />
                <span className="text-sm font-medium">{error}</span>
              </div>
            </div>
          )}

          {/* Registration Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Name Fields */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Input
                  type="text"
                  name="first_name"
                  label="First Name"
                  placeholder="John"
                  value={formData.first_name}
                  onChange={handleChange}
                  variant="elegant"
                  icon={<User size={18} />}
                  required
                  disabled={loading}
                  error={hasFieldError('first_name')}
                  className="transition-all duration-200 hover:shadow-lg hover:shadow-primary-500/5"
                  data-testid="first-name"
                />
                {hasFieldError('first_name') && (
                  <p className="text-xs text-error-600 animate-slide-down">
                    {getFieldError('first_name')}
                  </p>
                )}
              </div>
              
              <div className="space-y-1">
                <Input
                  type="text"
                  name="last_name"
                  label="Last Name"
                  placeholder="Doe"
                  value={formData.last_name}
                  onChange={handleChange}
                  variant="elegant"
                  icon={<User size={18} />}
                  required
                  disabled={loading}
                  error={hasFieldError('last_name')}
                  className="transition-all duration-200 hover:shadow-lg hover:shadow-primary-500/5"
                  data-testid="last-name"
                />
                {hasFieldError('last_name') && (
                  <p className="text-xs text-error-600 animate-slide-down">
                    {getFieldError('last_name')}
                  </p>
                )}
              </div>
            </div>

            {/* Email Field */}
            <div className="space-y-1">
              <Input
                type="email"
                name="email"
                label="Email Address"
                placeholder="john@example.com"
                value={formData.email}
                onChange={handleChange}
                variant="elegant"
                icon={<Mail size={18} />}
                required
                disabled={loading}
                error={hasFieldError('email')}
                className="transition-all duration-200 hover:shadow-lg hover:shadow-primary-500/5"
                data-testid="email"
              />
              {hasFieldError('email') && (
                <p className="text-xs text-error-600 animate-slide-down">
                  {getFieldError('email')}
                </p>
              )}
            </div>

            {/* Password Field with Strength Indicator */}
            <div className="space-y-3">
              <div className="space-y-1">
                <Input
                  type="password"
                  name="password"
                  label="Password"
                  placeholder="Create a secure password"
                  value={formData.password}
                  onChange={handleChange}
                  onFocus={() => setFocusedField('password')}
                  onBlur={() => setFocusedField(null)}
                  variant="elegant"
                  icon={<Lock size={18} />}
                  showPasswordToggle
                  required
                  disabled={loading}
                  error={hasFieldError('password')}
                  className="transition-all duration-200 hover:shadow-lg hover:shadow-primary-500/5"
                  data-testid="password"
                />
                {hasFieldError('password') && (
                  <p className="text-xs text-error-600 animate-slide-down">
                    {getFieldError('password')}
                  </p>
                )}
              </div>
              
              {/* Password Strength Indicator */}
              {formData.password && (focusedField === 'password' || passwordStrength.score > 0) && (
                <div className="space-y-2 animate-slide-down">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-gray-600">Password Strength</span>
                    <span className={`text-xs font-semibold text-${passwordStrength.color}-600`}>
                      {passwordStrength.label}
                    </span>
                  </div>
                  
                  {/* Strength Bar */}
                  <div className="flex space-x-1">
                    {[1, 2, 3, 4].map((level) => (
                      <div
                        key={level}
                        className={`h-1.5 flex-1 rounded-full transition-all duration-300 ${
                          level <= passwordStrength.score 
                            ? `bg-${passwordStrength.color}-500`
                            : 'bg-gray-200'
                        }`}
                      />
                    ))}
                  </div>
                  
                  {/* Feedback */}
                  {passwordStrength.feedback.length > 0 && (
                    <div className="space-y-1">
                      {passwordStrength.feedback.map((tip, index) => (
                        <div key={index} className="flex items-center space-x-2 text-xs text-gray-600">
                          <div className="w-1 h-1 bg-gray-400 rounded-full" />
                          <span>{tip}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Confirm Password Field */}
            <div className="space-y-2">
              <Input
                type="password"
                name="password_confirm"
                label="Confirm Password"
                placeholder="Confirm your password"
                value={formData.password_confirm}
                onChange={handleChange}
                variant="elegant"
                icon={<Lock size={18} />}
                showPasswordToggle
                required
                disabled={loading}
                error={passwordsDontMatch ? true : undefined}
                className="transition-all duration-200 hover:shadow-lg hover:shadow-primary-500/5"
                data-testid="password-confirm"
              />
              
              {/* Password Match Indicator */}
              {formData.password_confirm && (
                <div className={`flex items-center space-x-2 text-xs animate-slide-down ${
                  passwordsMatch ? 'text-success-600' : 'text-error-600'
                }`}>
                  {passwordsMatch ? (
                    <Check size={14} className="text-success-500" />
                  ) : (
                    <X size={14} className="text-error-500" />
                  )}
                  <span className="font-medium">
                    {passwordsMatch ? 'Passwords match' : 'Passwords do not match'}
                  </span>
                </div>
              )}
            </div>

            {/* Submit Button */}
            <Button
              type="submit"
              variant="gradient"
              size="lg"
              loading={loading}
              icon={<UserPlus size={18} />}
              className="w-full mt-8"
              disabled={loading}
              data-testid="register-button"
            >
              {loading ? 'Creating your account...' : 'Create Account'}
            </Button>
          </form>
        </CardContent>

        <CardFooter>
          {/* Switch to Login */}
          {onSwitchToLogin && (
            <div className="w-full text-center">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-white text-gray-500 font-medium">
                    Already have an account?
                  </span>
                </div>
              </div>
              
              <Button
                variant="ghost"
                size="lg"
                onClick={onSwitchToLogin}
                className="w-full mt-4 group"
                disabled={loading}
              >
                <span className="gradient-text group-hover:from-primary-700 group-hover:to-accent-700">
                  Sign in instead
                </span>
              </Button>
            </div>
          )}
        </CardFooter>

        {/* Decorative Elements */}
        <div className="absolute -top-3 -right-3 w-5 h-5 bg-gradient-to-br from-accent-400 to-primary-400 rounded-full opacity-60 animate-pulse-gentle" />
        <div className="absolute -bottom-3 -left-3 w-4 h-4 bg-gradient-to-br from-primary-400 to-accent-400 rounded-full opacity-40 animate-pulse-gentle" style={{animationDelay: '0.7s'}} />
        <div className="absolute top-1/4 -left-2 w-2 h-2 bg-gradient-to-br from-accent-300 to-primary-300 rounded-full opacity-50 animate-bounce-gentle" style={{animationDelay: '1s'}} />
      </Card>

      {/* Security Badge */}
      <div className="mt-6 text-center">
        <div className="inline-flex items-center space-x-2 text-xs text-gray-500 bg-white/50 backdrop-blur-sm px-3 py-2 rounded-full border border-gray-200/50">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          <span className="font-medium">Your data is protected with end-to-end encryption</span>
        </div>
      </div>
    </div>
  );
}