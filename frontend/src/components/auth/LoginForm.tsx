// Modern Login form component with dark theme styling

import React, { useState, FormEvent } from 'react';
import { Mail, Lock, LogIn, Bot } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
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
      <Card variant="dark" size="lg" className="relative">
        <CardHeader className="text-center space-y-4">
          {/* Logo/Brand Icon */}
          <div className="mx-auto w-16 h-16 bg-gradient-to-br from-violet-500 to-fuchsia-500 rounded-2xl flex items-center justify-center shadow-lg shadow-violet-500/25">
            <Bot className="w-8 h-8 text-white" />
          </div>

          <CardTitle className="text-3xl bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            Welcome Back
          </CardTitle>
          <CardDescription className="text-base text-slate-400">
            Sign in to your account to continue your journey
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

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-4">
              {/* Email Field */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-300">Email Address</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                  <input
                    type="email"
                    name="email"
                    placeholder="Enter your email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                    disabled={loading}
                    className="w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/50 transition-all disabled:opacity-50"
                  />
                </div>
              </div>

              {/* Password Field */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-300">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                  <input
                    type="password"
                    name="password"
                    placeholder="Enter your password"
                    value={formData.password}
                    onChange={handleChange}
                    required
                    disabled={loading}
                    className="w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/50 transition-all disabled:opacity-50"
                  />
                </div>
              </div>
            </div>

            {/* Forgot Password Link */}
            <div className="flex justify-end">
              <button
                type="button"
                className="text-sm font-medium text-violet-400 hover:text-violet-300 transition-colors focus:outline-none"
              >
                Forgot password?
              </button>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white font-medium hover:opacity-90 transition-opacity shadow-lg shadow-violet-500/25 disabled:opacity-50"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <LogIn className="w-5 h-5" />
                  Sign In
                </>
              )}
            </button>
          </form>
        </CardContent>

        <CardFooter>
          {/* Switch to Register */}
          {onSwitchToRegister && (
            <div className="w-full text-center">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/10" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-transparent text-slate-500 font-medium">
                    New to our platform?
                  </span>
                </div>
              </div>

              <button
                onClick={onSwitchToRegister}
                disabled={loading}
                className="w-full mt-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white font-medium hover:bg-white/10 transition-colors disabled:opacity-50"
              >
                <span className="bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
                  Create your account
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
          <span className="font-medium">Secured with enterprise-grade encryption</span>
        </div>
      </div>
    </div>
  );
}
