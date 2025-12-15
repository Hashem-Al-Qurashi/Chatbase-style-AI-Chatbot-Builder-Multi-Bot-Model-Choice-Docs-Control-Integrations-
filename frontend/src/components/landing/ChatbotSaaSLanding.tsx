import React, { useEffect, useState } from 'react';
import { 
  ArrowRight, 
  MessageSquare, 
  Bot, 
  Upload, 
  BarChart3, 
  Shield, 
  Zap, 
  Check, 
  Star,
  Play,
  Code,
  Brain,
  Users,
  Clock,
  Globe,
  ChevronRight,
  Sparkles,
  X,
  Settings,
  Database,
  Crown,
  AlertCircle
} from 'lucide-react';
import { Button } from '../ui/Button';
import { checkoutService } from '../../services/checkout';

interface ChatMessage {
  role: 'bot' | 'user';
  text: string;
  source?: string;
}

const ChatbotSaaSLanding = () => {
  const [isTyping, setIsTyping] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [demoInput, setDemoInput] = useState('');
  const [isSubmittingDemo, setIsSubmittingDemo] = useState(false);
  const [isSigningUp, setIsSigningUp] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    { role: 'bot', text: "How can I help you today?" },
    { role: 'user', text: "What are your business hours?" },
    { role: 'bot', text: "We're open Monday-Friday, 9 AM to 6 PM EST. You can also reach us 24/7 through this chat!", source: "Business Hours Policy.pdf" }
  ]);

  // Check for pending upgrade after login
  useEffect(() => {
    checkoutService.checkPendingUpgrade()
  }, [])

  const handleDemoSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!demoInput.trim() || isSubmittingDemo) return;

    setIsSubmittingDemo(true);

    // Add user message
    const userMessage: ChatMessage = { role: 'user', text: demoInput };
    setChatMessages(prev => [...prev, userMessage]);
    setDemoInput('');

    // Show typing indicator
    setIsTyping(true);

    // Simulate bot response
    setTimeout(() => {
      setIsTyping(false);
      const responses: ChatMessage[] = [
        { role: 'bot', text: "I can help you with that! Let me check our knowledge base.", source: "FAQ.pdf" },
        { role: 'bot', text: "Based on our documentation, here's what I found...", source: "User Guide.pdf" },
        { role: 'bot', text: "Great question! Our system is designed to handle exactly this scenario.", source: "Technical Docs.pdf" }
      ];
      const randomResponse = responses[Math.floor(Math.random() * responses.length)];
      setChatMessages(prev => [...prev, randomResponse]);
      setIsSubmittingDemo(false);
    }, 2000);
  };

  // Intersection observer for scroll animations
  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("animate");
        }
      });
    }, { threshold: 0.1, rootMargin: "0px 0px -10% 0px" });
    
    document.querySelectorAll('.animate-on-scroll').forEach((el) => {
      observer.observe(el);
    });

    return () => {
      observer.disconnect();
    };
  }, []);

  return (
    <div className="antialiased text-gray-900 min-h-screen relative overflow-hidden">
      {/* Modern Background with Journal Texture - Matching Login Page */}
      <div className="absolute inset-0 bg-gradient-to-br from-gray-50 via-white to-gray-100" />
      <div 
        className="absolute inset-0 bg-dot-pattern opacity-50"
        style={{
          backgroundSize: '24px 24px'
        }}
      />
      
      {/* Animated Background Elements - Matching Login Page */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 w-80 h-80 bg-gradient-to-br from-primary-400/20 to-accent-400/20 rounded-full blur-3xl animate-float" />
        <div className="absolute -top-20 -right-40 w-96 h-96 bg-gradient-to-br from-accent-400/15 to-primary-400/15 rounded-full blur-3xl animate-float" style={{animationDelay: '2s'}} />
        <div className="absolute -bottom-40 -left-20 w-96 h-96 bg-gradient-to-br from-primary-400/10 to-accent-400/10 rounded-full blur-3xl animate-float" style={{animationDelay: '4s'}} />
        <div className="absolute top-1/4 right-1/4 w-32 h-32 bg-gradient-to-br from-accent-300/20 to-primary-300/20 rounded-full blur-2xl animate-pulse-gentle" />
      </div>

      {/* Content */}
      <div className="relative z-10 min-h-screen">
      {/* Header */}
      <header className="relative z-50">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="flex pt-6 pb-6 items-center justify-between">
            {/* Brand */}
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-accent-500 rounded-xl flex items-center justify-center shadow-lg shadow-primary-500/25">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <h1 className="text-2xl font-bold gradient-text-elegant">
                Chatbot SaaS
              </h1>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-600">
              <a href="#features" className="hover:text-gray-900 transition-colors">Features</a>
              <a href="#demo" className="hover:text-gray-900 transition-colors">Demo</a>
              <a href="#pricing" className="hover:text-gray-900 transition-colors">Pricing</a>
              <a href="/login" className="inline-flex items-center gap-2 bg-gradient-to-r from-primary-600 to-accent-600 hover:from-primary-700 hover:to-accent-700 text-white px-5 py-2.5 rounded-full transition-all transform hover:scale-105 shadow-lg shadow-primary-500/25" data-testid="get-started">
                Get Started Free
                <ArrowRight className="w-4 h-4" />
              </a>
            </nav>

            {/* Mobile Menu */}
            <button 
              className="md:hidden p-2 hover:bg-neutral-100 rounded-lg transition-colors"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>

          {/* Mobile Navigation Menu */}
          {mobileMenuOpen && (
            <div className="md:hidden absolute top-full left-0 right-0 bg-white border-t border-neutral-200 shadow-lg z-50">
              <nav className="px-6 py-6 space-y-4">
                <a href="#features" className="block text-lg font-medium text-gray-700 hover:text-primary-600 transition-colors">Features</a>
                <a href="#demo" className="block text-lg font-medium text-gray-700 hover:text-primary-600 transition-colors">Demo</a>
                <a href="#pricing" className="block text-lg font-medium text-gray-700 hover:text-primary-600 transition-colors">Pricing</a>
                <div className="pt-4 border-t border-neutral-200">
                  <Button 
                    variant="gradient"
                    className="w-full"
                    onClick={() => window.location.href = '/login'}
                  >
                    Get Started Free
                  </Button>
                </div>
              </nav>
            </div>
          )}
        </div>
      </header>

      <main>
        {/* Hero Section */}
        <section className="relative px-6 lg:px-8 pt-20 pb-32">
          <div className="max-w-7xl mx-auto">
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              {/* Left: Value Proposition */}
              <div className="max-w-2xl">
                {/* Social Proof */}
                <div className="flex items-center gap-4 mb-8">
                  <div className="flex -space-x-3">
                    {['S', 'M', 'A', 'J', 'K'].map((letter, i) => (
                      <div 
                        key={i}
                        className="w-8 h-8 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center text-white text-sm font-semibold ring-2 ring-white"
                      >
                        {letter}
                      </div>
                    ))}
                  </div>
                  <div className="text-sm text-gray-600">
                    <span className="font-semibold text-gray-900">2,500+</span> businesses trust our chatbots
                  </div>
                </div>

                {/* Main Headline */}
                <h1 className="text-4xl lg:text-6xl font-bold text-gray-900 leading-tight mb-8">
                  Turn your docs into{' '}
                  <span className="gradient-text">
                    smart chatbots
                  </span>
                </h1>

                <p className="text-xl text-gray-600 leading-relaxed mb-10">
                  Upload your knowledge base and create intelligent chatbots that provide instant, accurate answers. 
                  <span className="font-semibold text-gray-900">No coding required.</span>
                </p>

                {/* Value Props */}
                <div className="grid sm:grid-cols-3 gap-6 mb-12">
                  <div className="flex items-center gap-3 group">
                    <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center group-hover:bg-primary-200 transition-colors duration-200">
                      <Clock className="w-5 h-5 text-primary-600" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900">5 min setup</p>
                      <p className="text-sm text-gray-600">Ready instantly</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 group">
                    <div className="w-10 h-10 bg-accent-100 rounded-lg flex items-center justify-center group-hover:bg-accent-200 transition-colors duration-200">
                      <Shield className="w-5 h-5 text-accent-600" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900">100% Private</p>
                      <p className="text-sm text-gray-600">Your data stays safe</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 group">
                    <div className="w-10 h-10 bg-success-100 rounded-lg flex items-center justify-center group-hover:bg-success-200 transition-colors duration-200">
                      <Globe className="w-5 h-5 text-success-600" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900">Any website</p>
                      <p className="text-sm text-gray-600">Embed anywhere</p>
                    </div>
                  </div>
                </div>

                {/* CTA Buttons */}
                <div className="flex flex-col sm:flex-row gap-4">
                  <Button 
                    variant="gradient"
                    size="xl"
                    loading={isSigningUp}
                    icon={<Sparkles />}
                    onClick={() => {
                      setIsSigningUp(true);
                      setTimeout(() => {
                        window.location.href = '/login';
                      }, 500);
                    }}
                  >
                    Create Your First Chatbot
                  </Button>
                  <Button 
                    variant="outline"
                    size="xl"
                    icon={<Play />}
                  >
                    Watch 2-min Demo
                  </Button>
                </div>

                {/* Trust Indicators */}
                <div className="mt-12">
                  <p className="text-sm text-gray-500 mb-4">Trusted by leading companies</p>
                  <div className="flex items-center gap-8 opacity-60">
                    <div className="text-lg font-bold text-gray-700">OPENAI</div>
                    <div className="text-lg font-bold text-gray-700">STRIPE</div>
                    <div className="text-lg font-bold text-gray-700">VERCEL</div>
                    <div className="text-lg font-bold text-gray-700">PINECONE</div>
                  </div>
                </div>
              </div>

              {/* Right: Live Chatbot Demo */}
              <div className="relative">
                <div className="relative bg-white rounded-2xl shadow-2xl border border-neutral-200 overflow-hidden">
                  {/* Browser UI */}
                  <div className="flex items-center gap-2 px-4 py-3 bg-neutral-50 border-b border-neutral-200">
                    <div className="flex gap-2">
                      <div className="w-3 h-3 rounded-full bg-red-400"></div>
                      <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
                      <div className="w-3 h-3 rounded-full bg-green-400"></div>
                    </div>
                    <div className="flex-1 text-center">
                      <div className="text-xs text-gray-600 bg-neutral-100 px-3 py-1 rounded-full inline-block">
                        yoursite.com/chat
                      </div>
                    </div>
                  </div>

                  {/* Chat Interface Demo */}
                  <div className="h-96 bg-gradient-to-br from-gray-50 to-white p-6 flex flex-col">
                    {/* Chat Header */}
                    <div className="flex items-center gap-3 mb-6">
                      <div className="w-10 h-10 bg-gradient-to-br from-purple-600 to-blue-600 rounded-full flex items-center justify-center">
                        <Bot className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">AI Assistant</h3>
                        <p className="text-sm text-green-600 flex items-center gap-1">
                          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                          Online
                        </p>
                      </div>
                    </div>

                    {/* Messages */}
                    <div className="flex-1 space-y-4 overflow-y-auto max-h-60">
                      {chatMessages.map((message, index) => (
                        <div key={index}>
                          {message.role === 'bot' ? (
                            <div className="flex gap-3">
                              <div className="w-8 h-8 bg-gradient-to-br from-purple-600 to-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
                                <Bot className="w-4 h-4 text-white" />
                              </div>
                              <div className="space-y-2">
                                <div className="bg-white rounded-2xl rounded-tl-md px-4 py-3 shadow-sm border border-neutral-200 max-w-xs">
                                  <p className="text-sm text-neutral-800">{message.text}</p>
                                </div>
                                {message.source && (
                                  <div className="text-xs text-gray-600 px-2">
                                    📄 Source: {message.source}
                                  </div>
                                )}
                              </div>
                            </div>
                          ) : (
                            <div className="flex gap-3 justify-end">
                              <div className="bg-gradient-to-r from-purple-600 to-blue-600 rounded-2xl rounded-br-md px-4 py-3 max-w-xs">
                                <p className="text-sm text-white">{message.text}</p>
                              </div>
                              <div className="w-8 h-8 bg-neutral-200 rounded-full flex items-center justify-center flex-shrink-0">
                                <span className="text-sm font-semibold">U</span>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                      
                      {/* Typing Indicator */}
                      {isTyping && (
                        <div className="flex gap-3">
                          <div className="w-8 h-8 bg-gradient-to-br from-purple-600 to-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
                            <Bot className="w-4 h-4 text-white" />
                          </div>
                          <div className="bg-white rounded-2xl rounded-tl-md px-4 py-3 shadow-sm border border-neutral-200 max-w-xs">
                            <div className="flex items-center gap-1">
                              <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce"></span>
                              <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></span>
                              <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Chat Input */}
                    <form onSubmit={handleDemoSubmit} className="mt-4 flex gap-2">
                      <input 
                        type="text" 
                        placeholder="Ask me anything..."
                        value={demoInput}
                        onChange={(e) => setDemoInput(e.target.value)}
                        className="flex-1 px-4 py-3 border border-neutral-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none"
                      />
                      <button 
                        type="submit"
                        className="px-4 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl hover:scale-105 transition-transform disabled:opacity-50"
                        disabled={!demoInput.trim() || isSubmittingDemo}
                      >
                        {isSubmittingDemo ? (
                          <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                        ) : (
                          <ArrowRight className="w-5 h-5" />
                        )}
                      </button>
                    </form>
                  </div>

                  {/* Floating Feature Badges */}
                  <div className="absolute -top-4 -right-4 bg-green-500 text-white px-3 py-1 rounded-full text-xs font-semibold shadow-lg">
                    ✨ AI-Powered
                  </div>
                  <div className="absolute -bottom-4 -left-4 bg-blue-500 text-white px-3 py-1 rounded-full text-xs font-semibold shadow-lg">
                    🚀 Instant Setup
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="py-24 px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-20">
              <h2 className="text-4xl lg:text-6xl font-bold tracking-tight mb-6">
                Everything your business needs
              </h2>
              <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                Built for real businesses who need reliable, intelligent customer support
              </p>
            </div>

            <div className="grid lg:grid-cols-3 gap-8">
              {/* Feature 1 */}
              <div className="group p-8 bg-white rounded-2xl border border-neutral-200 hover:border-purple-200 hover:shadow-xl transition-all duration-300">
                <div className="w-16 h-16 bg-gradient-to-br from-purple-100 to-purple-200 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <Brain className="w-8 h-8 text-purple-600" />
                </div>
                <h3 className="text-2xl font-bold mb-4">Smart RAG Technology</h3>
                <p className="text-gray-600 leading-relaxed mb-6">
                  Advanced retrieval-augmented generation ensures your chatbot gives accurate, contextual answers from your specific documents.
                </p>
              </div>

              {/* Feature 2 */}
              <div className="group p-8 bg-white rounded-2xl border border-neutral-200 hover:border-blue-200 hover:shadow-xl transition-all duration-300">
                <div className="w-16 h-16 bg-gradient-to-br from-blue-100 to-blue-200 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <Code className="w-8 h-8 text-blue-600" />
                </div>
                <h3 className="text-2xl font-bold mb-4">One-Click Integration</h3>
                <p className="text-gray-600 leading-relaxed mb-6">
                  Copy our embed code and your chatbot is live. Works with WordPress, Shopify, React, or any website.
                </p>
                <div className="bg-neutral-100 rounded-lg p-3 text-xs font-mono text-neutral-800">
                  &lt;script src="chatbot.js"&gt;&lt;/script&gt;
                </div>
              </div>

              {/* Feature 3 */}
              <div className="group p-8 bg-white rounded-2xl border border-neutral-200 hover:border-green-200 hover:shadow-xl transition-all duration-300">
                <div className="w-16 h-16 bg-gradient-to-br from-green-100 to-green-200 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <BarChart3 className="w-8 h-8 text-green-600" />
                </div>
                <h3 className="text-2xl font-bold mb-4">Deep Analytics</h3>
                <p className="text-gray-600 leading-relaxed mb-6">
                  See what customers ask, track satisfaction, and optimize your chatbot's performance with detailed insights.
                </p>
                <div className="flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                    <span className="text-gray-600">95% satisfaction</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                    <span className="text-gray-600">1.2k questions</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Pricing Section - Chatbase Style */}
        <section id="pricing" className="py-24 px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-16">
              <h2 className="text-4xl lg:text-6xl font-bold tracking-tight mb-6 gradient-text-elegant">
                Simple, Transparent Pricing
              </h2>
              <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                Choose the perfect plan for your AI chatbot needs
              </p>
              
              {/* Billing Toggle */}
              <div className="flex items-center justify-center space-x-4 mt-8">
                <span className="text-gray-700 font-medium">Monthly</span>
                <button className="relative inline-flex h-6 w-11 items-center rounded-full transition-all duration-200 bg-gradient-to-r from-primary-200 to-accent-200 hover:from-primary-300 hover:to-accent-300 shadow-sm">
                  <span className="inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform translate-x-1" />
                </button>
                <span className="text-gray-700 font-medium">Yearly</span>
                <span className="text-sm bg-gradient-to-r from-primary-100 to-accent-100 text-primary-800 px-3 py-1.5 rounded-full font-medium shadow-sm">
                  Save 20%
                </span>
              </div>
            </div>

            <div className="grid lg:grid-cols-4 gap-8 mb-16">
              {/* Free Plan */}
              <div className="bg-white/80 backdrop-blur-sm p-6 rounded-2xl border border-white/20 hover:border-primary-200 transition-all duration-200 shadow-soft hover:shadow-lg hover:shadow-primary-500/5">
                <div className="text-center mb-6">
                  <h3 className="text-2xl font-bold mb-2">Free</h3>
                  <div className="flex items-baseline justify-center gap-1 mb-4">
                    <span className="text-4xl font-bold">$0</span>
                    <span className="text-gray-600">/month</span>
                  </div>
                  <p className="text-gray-600">Perfect for testing and personal projects</p>
                </div>

                {/* Key Metrics */}
                <div className="space-y-3 mb-6 text-sm">
                  <div className="flex items-center">
                    <Zap className="w-4 h-4 mr-2 text-blue-600" />
                    <span className="font-medium">50 message credits</span>
                  </div>
                  <div className="flex items-center">
                    <Settings className="w-4 h-4 mr-2 text-green-600" />
                    <span>1 AI agent</span>
                  </div>
                  <div className="flex items-center">
                    <Database className="w-4 h-4 mr-2 text-purple-600" />
                    <span>400KB per agent</span>
                  </div>
                </div>

                {/* Features */}
                <ul className="space-y-2 mb-6 text-sm">
                  <li className="flex items-center">
                    <Check className="w-4 h-4 mr-2 text-green-600" />
                    <span>Embed on unlimited websites</span>
                  </li>
                  <li className="flex items-center">
                    <X className="w-4 h-4 mr-2 text-neutral-400" />
                    <span className="text-neutral-500">API access</span>
                  </li>
                </ul>

                {/* Warning */}
                <div className="mb-6 text-sm text-amber-700 bg-amber-50 p-2 rounded flex items-start">
                  <AlertCircle className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
                  <span>AI agents deleted after 14 days of inactivity</span>
                </div>

                <Button 
                  variant="elegant" 
                  className="w-full"
                  onClick={() => window.location.href = '/login'}
                  data-testid="free-plan-get-started"
                >
                  Get Started
                </Button>
              </div>

              {/* Hobby Plan - Most Popular */}
              <div className="bg-gradient-to-br from-primary-50 to-accent-50 backdrop-blur-sm p-6 rounded-2xl border-2 border-primary-500 ring-2 ring-primary-200/50 relative transform lg:scale-105 shadow-lg shadow-primary-500/25">
                <div className="absolute -top-4 left-1/2 transform -translate-x-1/2 bg-gradient-to-r from-primary-600 to-accent-600 text-white px-4 py-1 rounded-full text-sm font-medium flex items-center shadow-lg shadow-primary-500/25 animate-bounce-gentle">
                  <Crown className="w-4 h-4 mr-1" />
                  Most Popular
                </div>
                
                <div className="text-center mb-6">
                  <h3 className="text-2xl font-bold mb-2">Hobby</h3>
                  <div className="flex items-baseline justify-center gap-1 mb-4">
                    <span className="text-4xl font-bold">$40</span>
                    <span className="text-gray-600">/month</span>
                  </div>
                  <p className="text-gray-600">For solo founders and small projects</p>
                </div>

                {/* Key Metrics */}
                <div className="space-y-3 mb-6 text-sm">
                  <div className="flex items-center">
                    <Zap className="w-4 h-4 mr-2 text-blue-600" />
                    <span className="font-medium">2K message credits</span>
                  </div>
                  <div className="flex items-center">
                    <Settings className="w-4 h-4 mr-2 text-green-600" />
                    <span>1 AI agent</span>
                  </div>
                  <div className="flex items-center">
                    <Database className="w-4 h-4 mr-2 text-purple-600" />
                    <span>40MB per agent</span>
                  </div>
                  <div className="flex items-center">
                    <Zap className="w-4 h-4 mr-2 text-orange-600" />
                    <span>5 AI Actions per agent</span>
                  </div>
                </div>

                {/* Features */}
                <ul className="space-y-2 mb-6 text-sm">
                  <li className="flex items-center">
                    <Check className="w-4 h-4 mr-2 text-green-600" />
                    <span>Unlimited training links</span>
                  </li>
                  <li className="flex items-center">
                    <Check className="w-4 h-4 mr-2 text-green-600" />
                    <span>API access</span>
                  </li>
                  <li className="flex items-center">
                    <Check className="w-4 h-4 mr-2 text-green-600" />
                    <span>Basic integrations</span>
                  </li>
                </ul>

                <Button 
                  variant="gradient"
                  className="w-full"
                  onClick={() => checkoutService.upgradeToHobby()}
                >
                  Upgrade to Hobby
                </Button>
              </div>

              {/* Standard Plan */}
              <div className="bg-white/80 backdrop-blur-sm p-6 rounded-2xl border border-white/20 hover:border-accent-200 transition-all duration-200 shadow-soft hover:shadow-lg hover:shadow-accent-500/5">
                <div className="text-center mb-6">
                  <h3 className="text-2xl font-bold mb-2">Standard</h3>
                  <div className="flex items-baseline justify-center gap-1 mb-4">
                    <span className="text-4xl font-bold">$150</span>
                    <span className="text-gray-600">/month</span>
                  </div>
                  <p className="text-gray-600">For small teams and growing businesses</p>
                </div>

                {/* Key Metrics */}
                <div className="space-y-3 mb-6 text-sm">
                  <div className="flex items-center">
                    <Zap className="w-4 h-4 mr-2 text-blue-600" />
                    <span className="font-medium">12K message credits</span>
                  </div>
                  <div className="flex items-center">
                    <Settings className="w-4 h-4 mr-2 text-green-600" />
                    <span>2 AI agents</span>
                  </div>
                  <div className="flex items-center">
                    <Database className="w-4 h-4 mr-2 text-purple-600" />
                    <span>33MB per agent</span>
                  </div>
                  <div className="flex items-center">
                    <Zap className="w-4 h-4 mr-2 text-orange-600" />
                    <span>10 AI Actions per agent</span>
                  </div>
                  <div className="flex items-center">
                    <Users className="w-4 h-4 mr-2 text-indigo-600" />
                    <span>3 seats</span>
                  </div>
                </div>

                {/* Features */}
                <ul className="space-y-2 mb-6 text-sm">
                  <li className="flex items-center">
                    <Check className="w-4 h-4 mr-2 text-green-600" />
                    <span>Multiple agents</span>
                  </li>
                  <li className="flex items-center">
                    <Check className="w-4 h-4 mr-2 text-green-600" />
                    <span>Team collaboration</span>
                  </li>
                  <li className="flex items-center">
                    <Check className="w-4 h-4 mr-2 text-green-600" />
                    <span>More AI actions</span>
                  </li>
                </ul>

                <Button 
                  variant="elegant" 
                  className="w-full"
                  onClick={() => checkoutService.upgradeToStandard()}
                >
                  Upgrade to Standard
                </Button>
              </div>

              {/* Pro Plan */}
              <div className="bg-white/80 backdrop-blur-sm p-6 rounded-2xl border border-white/20 hover:border-accent-300 transition-all duration-200 shadow-soft hover:shadow-lg hover:shadow-accent-500/10">
                <div className="text-center mb-6">
                  <h3 className="text-2xl font-bold mb-2">Pro</h3>
                  <div className="flex items-baseline justify-center gap-1 mb-4">
                    <span className="text-4xl font-bold">$500</span>
                    <span className="text-gray-600">/month</span>
                  </div>
                  <p className="text-gray-600">For businesses needing advanced features</p>
                </div>

                {/* Key Metrics */}
                <div className="space-y-3 mb-6 text-sm">
                  <div className="flex items-center">
                    <Zap className="w-4 h-4 mr-2 text-blue-600" />
                    <span className="font-medium">40K message credits</span>
                  </div>
                  <div className="flex items-center">
                    <Settings className="w-4 h-4 mr-2 text-green-600" />
                    <span>3 AI agents</span>
                  </div>
                  <div className="flex items-center">
                    <Database className="w-4 h-4 mr-2 text-purple-600" />
                    <span>33MB per agent</span>
                  </div>
                  <div className="flex items-center">
                    <Zap className="w-4 h-4 mr-2 text-orange-600" />
                    <span>15 AI Actions per agent</span>
                  </div>
                  <div className="flex items-center">
                    <Users className="w-4 h-4 mr-2 text-indigo-600" />
                    <span>5 seats</span>
                  </div>
                </div>

                {/* Features */}
                <ul className="space-y-2 mb-6 text-sm">
                  <li className="flex items-center">
                    <Check className="w-4 h-4 mr-2 text-green-600" />
                    <span>Advanced analytics</span>
                  </li>
                  <li className="flex items-center">
                    <Check className="w-4 h-4 mr-2 text-green-600" />
                    <span>Priority support</span>
                  </li>
                  <li className="flex items-center">
                    <Check className="w-4 h-4 mr-2 text-green-600" />
                    <span>Larger teams</span>
                  </li>
                </ul>

                <Button 
                  variant="elegant" 
                  className="w-full"
                  onClick={() => checkoutService.upgradeToPro()}
                >
                  Upgrade to Pro
                </Button>
              </div>
            </div>

            {/* Add-ons Section */}
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-white/20 shadow-lg shadow-primary-500/10 p-8">
              <div className="text-center mb-8">
                <h2 className="text-3xl font-bold gradient-text-elegant mb-4">
                  Add-ons & Extras
                </h2>
                <p className="text-gray-600">
                  Enhance your plan with additional features and resources
                </p>
              </div>

              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                <div className="bg-white/60 backdrop-blur-sm border border-white/30 rounded-xl p-6 hover:border-primary-200 hover:shadow-lg hover:shadow-primary-500/5 transition-all duration-200">
                  <h3 className="font-semibold text-gray-900 mb-2">
                    Extra Message Credits
                  </h3>
                  <p className="text-gray-600 text-sm mb-4">
                    1,000 additional message credits per month
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-bold text-gray-900">
                      $12/month
                    </span>
                    <button className="text-primary-600 hover:text-primary-700 bg-primary-50 hover:bg-primary-100 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 hover:shadow-md">
                      Add
                    </button>
                  </div>
                </div>

                <div className="bg-white/60 backdrop-blur-sm border border-white/30 rounded-xl p-6 hover:border-accent-200 hover:shadow-lg hover:shadow-accent-500/5 transition-all duration-200">
                  <h3 className="font-semibold text-gray-900 mb-2">
                    Auto-recharge Credits
                  </h3>
                  <p className="text-gray-600 text-sm mb-4">
                    Automatically adds 1,000 credits when you run low
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-bold text-gray-900">
                      $14/month
                    </span>
                    <button className="text-primary-600 hover:text-primary-700 bg-primary-50 hover:bg-primary-100 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 hover:shadow-md">
                      Add
                    </button>
                  </div>
                </div>

                <div className="bg-white/60 backdrop-blur-sm border border-white/30 rounded-xl p-6 hover:border-accent-200 hover:shadow-lg hover:shadow-accent-500/5 transition-all duration-200">
                  <h3 className="font-semibold text-gray-900 mb-2">
                    Additional AI Agent
                  </h3>
                  <p className="text-gray-600 text-sm mb-4">
                    Add one more AI agent to your account
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-bold text-gray-900">
                      $7/month
                    </span>
                    <button className="text-primary-600 hover:text-primary-700 bg-primary-50 hover:bg-primary-100 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 hover:shadow-md">
                      Add
                    </button>
                  </div>
                </div>

                <div className="bg-white/60 backdrop-blur-sm border border-white/30 rounded-xl p-6 hover:border-accent-200 hover:shadow-lg hover:shadow-accent-500/5 transition-all duration-200">
                  <h3 className="font-semibold text-gray-900 mb-2">
                    Remove Branding
                  </h3>
                  <p className="text-gray-600 text-sm mb-4">
                    Remove "Powered by [Brand]" from chatbots
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-bold text-gray-900">
                      $39/month
                    </span>
                    <button className="text-primary-600 hover:text-primary-700 bg-primary-50 hover:bg-primary-100 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 hover:shadow-md">
                      Add
                    </button>
                  </div>
                </div>

                <div className="bg-white/60 backdrop-blur-sm border border-white/30 rounded-xl p-6 hover:border-accent-200 hover:shadow-lg hover:shadow-accent-500/5 transition-all duration-200">
                  <h3 className="font-semibold text-gray-900 mb-2">
                    Custom Domain
                  </h3>
                  <p className="text-gray-600 text-sm mb-4">
                    Use your own domain for chat widgets
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-bold text-gray-900">
                      $59/month
                    </span>
                    <button className="text-primary-600 hover:text-primary-700 bg-primary-50 hover:bg-primary-100 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 hover:shadow-md">
                      Add
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Enterprise CTA */}
            <div className="text-center mt-12">
              <p className="text-gray-600">
                Need custom limits or enterprise features?{' '}
                <a href="#" className="text-blue-600 hover:text-blue-700 font-medium">
                  Contact us for Enterprise pricing
                </a>
              </p>
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="py-24 px-6 lg:px-8 bg-gradient-to-br from-primary-600 via-accent-600 to-primary-700 relative overflow-hidden">
          {/* Background Decorative Elements */}
          <div className="absolute inset-0 overflow-hidden">
            <div className="absolute -top-32 -left-32 w-96 h-96 bg-white/10 rounded-full blur-3xl animate-float" />
            <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-white/10 rounded-full blur-3xl animate-float" style={{animationDelay: '2s'}} />
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-white/5 rounded-full blur-2xl animate-pulse-gentle" />
          </div>
          
          <div className="max-w-4xl mx-auto text-center text-white relative z-10">
            <h2 className="text-4xl lg:text-6xl font-bold tracking-tight mb-6 animate-slide-up">
              Ready to transform your customer support?
            </h2>
            <p className="text-xl text-white/90 mb-12 max-w-2xl mx-auto">
              Join thousands of businesses using intelligent chatbots to provide better customer experiences.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-6 justify-center items-center">
              <Button 
                variant="elegant"
                size="xl"
                className="bg-white/90 backdrop-blur-sm text-primary-700 hover:bg-white hover:text-primary-800 border border-white/20 shadow-xl hover:shadow-2xl transform hover:scale-105 animate-bounce-gentle"
                onClick={() => window.location.href = '/login'}
                icon={<Sparkles size={20} />}
              >
                Start Building for Free
              </Button>
              <button className="flex items-center gap-3 text-white/90 hover:text-white font-medium bg-white/10 backdrop-blur-sm px-6 py-3 rounded-xl border border-white/20 hover:bg-white/20 transition-all duration-200 hover:shadow-lg">
                <Play className="w-5 h-5" />
                Watch Success Stories
              </button>
            </div>

            <div className="mt-12 text-white/80 text-sm">
              ✅ No credit card required • ✅ 5-minute setup • ✅ Cancel anytime
            </div>
          </div>
        </section>
      </main>

      {/* Decorative Elements - Matching Login Page */}
      <div className="absolute top-10 right-10 w-2 h-2 bg-primary-400 rounded-full animate-pulse opacity-60" />
      <div className="absolute bottom-20 left-10 w-3 h-3 bg-accent-400 rounded-full animate-bounce-gentle opacity-50" />
      <div className="absolute top-1/3 right-1/4 w-1 h-1 bg-primary-500 rounded-full animate-pulse opacity-40" />

      {/* Footer */}
      <footer className="bg-neutral-900 text-white py-16 px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-4 gap-8 mb-12">
            <div>
              <div className="flex items-center gap-3 mb-6">
                <div className="w-8 h-8 bg-gradient-to-br from-purple-600 to-blue-600 rounded-lg flex items-center justify-center">
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <span className="text-xl font-bold">ChatBot SaaS</span>
              </div>
              <p className="text-neutral-400 leading-relaxed">
                Transform your documents into intelligent chatbots that actually help your customers.
              </p>
            </div>

            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <ul className="space-y-3 text-neutral-400">
                <li><a href="#features" className="hover:text-white transition-colors">Features</a></li>
                <li><a href="#pricing" className="hover:text-white transition-colors">Pricing</a></li>
                <li><a href="#" className="hover:text-white transition-colors">API Docs</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold mb-4">Support</h4>
              <ul className="space-y-3 text-neutral-400">
                <li><a href="#" className="hover:text-white transition-colors">Help Center</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Contact</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Status</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <ul className="space-y-3 text-neutral-400">
                <li><a href="#" className="hover:text-white transition-colors">About</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Privacy</a></li>
              </ul>
            </div>
          </div>

          <div className="border-t border-neutral-800 pt-8 flex flex-col sm:flex-row justify-between items-center">
            <p className="text-neutral-400 text-sm">
              © 2024 ChatBot SaaS. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
      </div>
    </div>
  );
};

export default ChatbotSaaSLanding;