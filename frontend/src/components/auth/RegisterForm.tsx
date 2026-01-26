// Modern Registration form component with dark theme styling

import React, { useState, FormEvent, useMemo } from 'react';
import { Mail, Lock, User, UserPlus, Bot, Check, X } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { RegisterRequest } from '../../types';
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
    if (!password) return { score: 0, feedback: [], color: 'slate', label: '' };

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

    const colors = ['rose', 'amber', 'amber', 'emerald', 'emerald'];
    const labels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];

    return {
      score,
      feedback,
      color: colors[score] || 'slate',
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

  // Get strength bar color class
  const getStrengthBarColor = (level: number) => {
    if (level > passwordStrength.score) return 'bg-white/10';
    switch (passwordStrength.color) {
      case 'rose': return 'bg-rose-500';
      case 'amber': return 'bg-amber-500';
      case 'emerald': return 'bg-emerald-500';
      default: return 'bg-slate-500';
    }
  };

  const getStrengthLabelColor = () => {
    switch (passwordStrength.color) {
      case 'rose': return 'text-rose-400';
      case 'amber': return 'text-amber-400';
      case 'emerald': return 'text-emerald-400';
      default: return 'text-slate-400';
    }
  };

  return (
    <div className="w-full max-w-lg mx-auto animate-slide-up">
      <Card variant="dark" size="lg" className="relative">
        <CardHeader className="text-center space-y-4">
          {/* Logo/Brand Icon */}
          <div className="mx-auto w-16 h-16 bg-gradient-to-br from-violet-500 to-fuchsia-500 rounded-2xl flex items-center justify-center shadow-lg shadow-violet-500/25">
            <Bot className="w-8 h-8 text-white" />
          </div>

          <CardTitle className="text-3xl bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            Create Account
          </CardTitle>
          <CardDescription className="text-base text-slate-400">
            Join Chatava and start building AI-powered chatbots
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Error Message */}
          {error && (
            <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 px-4 py-3 rounded-xl animate-slide-down">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-rose-500 rounded-full animate-pulse" />
                <span className="text-sm font-medium">{error}</span>
              </div>
            </div>
          )}

          {/* Registration Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Name Fields */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-300">First Name</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                  <input
                    type="text"
                    name="first_name"
                    placeholder="John"
                    value={formData.first_name}
                    onChange={handleChange}
                    required
                    disabled={loading}
                    className={`w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border ${
                      hasFieldError('first_name') ? 'border-rose-500/50' : 'border-white/10'
                    } text-white placeholder:text-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/50 transition-all disabled:opacity-50`}
                    data-testid="first-name"
                  />
                </div>
                {hasFieldError('first_name') && (
                  <p className="text-xs text-rose-400 animate-slide-down">
                    {getFieldError('first_name')}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-300">Last Name</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                  <input
                    type="text"
                    name="last_name"
                    placeholder="Doe"
                    value={formData.last_name}
                    onChange={handleChange}
                    required
                    disabled={loading}
                    className={`w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border ${
                      hasFieldError('last_name') ? 'border-rose-500/50' : 'border-white/10'
                    } text-white placeholder:text-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/50 transition-all disabled:opacity-50`}
                    data-testid="last-name"
                  />
                </div>
                {hasFieldError('last_name') && (
                  <p className="text-xs text-rose-400 animate-slide-down">
                    {getFieldError('last_name')}
                  </p>
                )}
              </div>
            </div>

            {/* Email Field */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input
                  type="email"
                  name="email"
                  placeholder="john@example.com"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  disabled={loading}
                  className={`w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border ${
                    hasFieldError('email') ? 'border-rose-500/50' : 'border-white/10'
                  } text-white placeholder:text-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/50 transition-all disabled:opacity-50`}
                  data-testid="email"
                />
              </div>
              {hasFieldError('email') && (
                <p className="text-xs text-rose-400 animate-slide-down">
                  {getFieldError('email')}
                </p>
              )}
            </div>

            {/* Password Field with Strength Indicator */}
            <div className="space-y-3">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-300">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                  <input
                    type="password"
                    name="password"
                    placeholder="Create a secure password"
                    value={formData.password}
                    onChange={handleChange}
                    onFocus={() => setFocusedField('password')}
                    onBlur={() => setFocusedField(null)}
                    required
                    disabled={loading}
                    className={`w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border ${
                      hasFieldError('password') ? 'border-rose-500/50' : 'border-white/10'
                    } text-white placeholder:text-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/50 transition-all disabled:opacity-50`}
                    data-testid="password"
                  />
                </div>
                {hasFieldError('password') && (
                  <p className="text-xs text-rose-400 animate-slide-down">
                    {getFieldError('password')}
                  </p>
                )}
              </div>

              {/* Password Strength Indicator */}
              {formData.password && (focusedField === 'password' || passwordStrength.score > 0) && (
                <div className="space-y-2 animate-slide-down">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-500">Password Strength</span>
                    <span className={`text-xs font-semibold ${getStrengthLabelColor()}`}>
                      {passwordStrength.label}
                    </span>
                  </div>

                  {/* Strength Bar */}
                  <div className="flex space-x-1">
                    {[1, 2, 3, 4].map((level) => (
                      <div
                        key={level}
                        className={`h-1.5 flex-1 rounded-full transition-all duration-300 ${getStrengthBarColor(level)}`}
                      />
                    ))}
                  </div>

                  {/* Feedback */}
                  {passwordStrength.feedback.length > 0 && (
                    <div className="space-y-1">
                      {passwordStrength.feedback.map((tip, index) => (
                        <div key={index} className="flex items-center space-x-2 text-xs text-slate-500">
                          <div className="w-1 h-1 bg-slate-600 rounded-full" />
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
              <label className="text-sm font-medium text-slate-300">Confirm Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input
                  type="password"
                  name="password_confirm"
                  placeholder="Confirm your password"
                  value={formData.password_confirm}
                  onChange={handleChange}
                  required
                  disabled={loading}
                  className={`w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border ${
                    passwordsDontMatch ? 'border-rose-500/50' : 'border-white/10'
                  } text-white placeholder:text-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/50 transition-all disabled:opacity-50`}
                  data-testid="password-confirm"
                />
              </div>

              {/* Password Match Indicator */}
              {formData.password_confirm && (
                <div className={`flex items-center space-x-2 text-xs animate-slide-down ${
                  passwordsMatch ? 'text-emerald-400' : 'text-rose-400'
                }`}>
                  {passwordsMatch ? (
                    <Check size={14} className="text-emerald-400" />
                  ) : (
                    <X size={14} className="text-rose-400" />
                  )}
                  <span className="font-medium">
                    {passwordsMatch ? 'Passwords match' : 'Passwords do not match'}
                  </span>
                </div>
              )}
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white font-medium hover:opacity-90 transition-opacity shadow-lg shadow-violet-500/25 disabled:opacity-50 mt-6"
              data-testid="register-button"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <UserPlus className="w-5 h-5" />
                  Create Account
                </>
              )}
            </button>
          </form>
        </CardContent>

        <CardFooter>
          {/* Switch to Login */}
          {onSwitchToLogin && (
            <div className="w-full text-center">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/10" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-transparent text-slate-500 font-medium">
                    Already have an account?
                  </span>
                </div>
              </div>

              <button
                onClick={onSwitchToLogin}
                disabled={loading}
                className="w-full mt-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white font-medium hover:bg-white/10 transition-colors disabled:opacity-50"
              >
                <span className="bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
                  Sign in instead
                </span>
              </button>
            </div>
          )}
        </CardFooter>

        {/* Decorative Elements */}
        <div className="absolute -top-2 -right-2 w-4 h-4 bg-gradient-to-br from-violet-400 to-fuchsia-400 rounded-full opacity-60 animate-pulse" />
        <div className="absolute -bottom-2 -left-2 w-3 h-3 bg-gradient-to-br from-fuchsia-400 to-cyan-400 rounded-full opacity-40 animate-pulse" style={{animationDelay: '0.5s'}} />
      </Card>

      {/* Security Badge */}
      <div className="mt-6 text-center">
        <div className="inline-flex items-center space-x-2 text-xs text-slate-500 bg-white/5 backdrop-blur-sm px-3 py-2 rounded-full border border-white/10">
          <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
          <span className="font-medium">Your data is protected with end-to-end encryption</span>
        </div>
      </div>
    </div>
  );
}
