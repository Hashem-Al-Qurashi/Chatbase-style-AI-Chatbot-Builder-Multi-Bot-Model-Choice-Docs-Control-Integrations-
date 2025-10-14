// Modern Login form component with elegant styling

import React, { useState, FormEvent } from 'react';
import { Mail, Lock, LogIn, Sparkles } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../ui/Card';

interface LoginFormProps {
  onSuccess?: () => void;
  onSwitchToRegister?: () => void;
}

export function LoginForm({ onSuccess, onSwitchToRegister }: LoginFormProps) {
  const { login } = useAuth();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await login(formData);
      onSuccess?.();
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  return (
    <div className="w-full max-w-md mx-auto animate-slide-up">
      {/* Background Decorative Elements */}
      <div className="absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-24 -left-24 w-96 h-96 bg-gradient-to-br from-primary-500/20 to-accent-500/20 rounded-full blur-3xl animate-float" />
        <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-gradient-to-br from-accent-500/20 to-primary-500/20 rounded-full blur-3xl animate-float" style={{animationDelay: '1s'}} />
      </div>

      <Card variant="elegant" size="lg" className="relative backdrop-blur-fix">
        <CardHeader className="text-center space-y-4">
          {/* Logo/Brand Icon */}
          <div className="mx-auto w-16 h-16 bg-gradient-to-br from-primary-500 to-accent-500 rounded-2xl flex items-center justify-center shadow-lg shadow-primary-500/25 animate-bounce-gentle">
            <Sparkles className="w-8 h-8 text-white" />
          </div>
          
          <CardTitle className="text-3xl gradient-text-elegant">
            Welcome Back
          </CardTitle>
          <CardDescription className="text-base">
            Sign in to your account to continue your journey
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Error Message */}
          {error && (
            <div className="bg-gradient-to-r from-error-50 to-error-100 border border-error-200 text-error-700 px-4 py-3 rounded-xl animate-slide-down">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-error-500 rounded-full animate-pulse" />
                <span className="text-sm font-medium">{error}</span>
              </div>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-4">
              {/* Email Field */}
              <Input
                type="email"
                name="email"
                label="Email Address"
                placeholder="Enter your email"
                value={formData.email}
                onChange={handleChange}
                variant="elegant"
                icon={<Mail size={18} />}
                required
                disabled={loading}
                className="transition-all duration-200 hover:shadow-lg hover:shadow-primary-500/5"
              />

              {/* Password Field */}
              <Input
                type="password"
                name="password"
                label="Password"
                placeholder="Enter your password"
                value={formData.password}
                onChange={handleChange}
                variant="elegant"
                icon={<Lock size={18} />}
                showPasswordToggle
                required
                disabled={loading}
                className="transition-all duration-200 hover:shadow-lg hover:shadow-primary-500/5"
              />
            </div>

            {/* Forgot Password Link */}
            <div className="flex justify-end">
              <button
                type="button"
                className="text-sm font-medium text-primary-600 hover:text-primary-700 hover:underline transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 rounded-md px-2 py-1"
              >
                Forgot password?
              </button>
            </div>

            {/* Submit Button */}
            <Button
              type="submit"
              variant="gradient"
              size="lg"
              loading={loading}
              icon={<LogIn size={18} />}
              className="w-full mt-6"
              disabled={loading}
            >
              {loading ? 'Signing you in...' : 'Sign In'}
            </Button>
          </form>
        </CardContent>

        <CardFooter>
          {/* Switch to Register */}
          {onSwitchToRegister && (
            <div className="w-full text-center">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-white text-gray-500 font-medium">
                    New to our platform?
                  </span>
                </div>
              </div>
              
              <Button
                variant="ghost"
                size="lg"
                onClick={onSwitchToRegister}
                className="w-full mt-4 group"
                disabled={loading}
              >
                <span className="gradient-text group-hover:from-primary-700 group-hover:to-accent-700">
                  Create your account
                </span>
              </Button>
            </div>
          )}
        </CardFooter>

        {/* Decorative Elements */}
        <div className="absolute -top-2 -right-2 w-4 h-4 bg-gradient-to-br from-primary-400 to-accent-400 rounded-full opacity-60 animate-pulse-gentle" />
        <div className="absolute -bottom-2 -left-2 w-3 h-3 bg-gradient-to-br from-accent-400 to-primary-400 rounded-full opacity-40 animate-pulse-gentle" style={{animationDelay: '0.5s'}} />
      </Card>

      {/* Security Badge */}
      <div className="mt-6 text-center">
        <div className="inline-flex items-center space-x-2 text-xs text-gray-500 bg-white/50 backdrop-blur-sm px-3 py-2 rounded-full border border-gray-200/50">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          <span className="font-medium">Secured with enterprise-grade encryption</span>
        </div>
      </div>
    </div>
  );
}