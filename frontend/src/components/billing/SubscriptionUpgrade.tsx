import React, { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useNavigate } from 'react-router-dom';

const SubscriptionUpgrade = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [selectedPayment, setSelectedPayment] = useState('visa');
  const [isProcessing, setIsProcessing] = useState(false);

  const handleUpgrade = () => {
    if (!user) {
      navigate('/login');
      return;
    }
    
    setIsProcessing(true);
    setTimeout(() => {
      // Handle upgrade logic here
      alert('Upgrade Successful! Welcome to StreamFlow Pro');
      setIsProcessing(false);
    }, 2000);
  };

  return (
    <div 
      className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden"
      style={{
        background: 'linear-gradient(to bottom right, hsl(225, 15%, 15%), hsl(225, 20%, 10%), rgb(15 23 42))',
        fontFamily: 'Inter, sans-serif'
      }}
    >
      {/* Background Image */}
      <div 
        className="fixed top-0 w-full h-screen bg-cover bg-center -z-10"
        style={{
          backgroundImage: 'url("https://hoirqrkdgbmvpwutwuwj.supabase.co/storage/v1/object/public/assets/assets/04f24b31-1be5-4425-bd2c-46dbf17db590_3840w.jpg")'
        }}
      ></div>
      
      {/* Animated background */}
      <div className="absolute inset-0">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-500/30 rounded-full blur-3xl"></div>
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-blue-500/20 rounded-full blur-3xl"></div>
      </div>

      <div className="relative">
        {/* Base Card (Purple) - Moved to right */}
        <div 
          className="absolute z-0 h-2/3 rounded-[1.5rem] bg-cover translate-x-20 translate-y-28"
          style={{
            width: '32rem',
            maxWidth: '90vw',
            minHeight: '32rem',
            backgroundImage: 'url("https://hoirqrkdgbmvpwutwuwj.supabase.co/storage/v1/object/public/assets/assets/e923ad25-c307-4eeb-a564-655c0bce21f7_1600w.jpg")',
            boxShadow: '0 0 30px rgba(139, 92, 246, 0.4), 0 2.8px 2.2px rgba(0, 0, 0, 0.034), 0 6.7px 5.3px rgba(0, 0, 0, 0.048), 0 12.5px 10px rgba(0, 0, 0, 0.06), 0 22.3px 17.9px rgba(0, 0, 0, 0.072), 0 41.8px 33.4px rgba(0, 0, 0, 0.086), 0 100px 80px rgba(0, 0, 0, 0.12)'
          }}
        ></div>
        
        {/* Glass Modal */}
        <div 
          className="overflow-hidden relative z-10 top-8"
          style={{
            width: '32rem',
            maxWidth: '90vw',
            minHeight: '32rem',
            borderRadius: '1.5rem',
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
            background: 'linear-gradient(to right, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0.05))',
            boxShadow: '0 2.8px 2.2px rgba(0, 0, 0, 0.034), 0 6.7px 5.3px rgba(0, 0, 0, 0.048), 0 12.5px 10px rgba(0, 0, 0, 0.06), 0 22.3px 17.9px rgba(0, 0, 0, 0.072), 0 41.8px 33.4px rgba(0, 0, 0, 0.086), 0 100px 80px rgba(0, 0, 0, 0.12)'
          }}
        >
          {/* Border overlay */}
          <div 
            className="absolute inset-0 rounded-[1.5rem] border"
            style={{
              borderColor: 'rgba(255, 255, 255, 0.5)',
              maskImage: 'linear-gradient(135deg, white, transparent 50%)'
            }}
          ></div>
          <div 
            className="absolute inset-0 rounded-[1.5rem] border"
            style={{
              borderColor: 'hsl(260, 95%, 63%, 0.5)',
              maskImage: 'linear-gradient(135deg, transparent 50%, white)'
            }}
          ></div>
          
          {/* Content */}
          <div 
            className="flex flex-col h-full relative text-white"
            style={{
              backgroundImage: `
                linear-gradient(to bottom, rgba(255,255,255,0) 3.125rem, hsl(270, 95%, 68%) 3.375rem, hsl(280, 90%, 80%) 4.5rem),
                linear-gradient(to right, hsl(280, 90%, 80%) 19.5rem, hsl(270, 95%, 68%) calc(100% - 6rem), rgba(255,255,255,0) 28.65rem),
                linear-gradient(to right, rgba(255,255,255,0.5) 6rem, rgba(255,255,255,0.2))
              `,
              backgroundSize: 'calc(100% - 6rem) 35%, 100% 35%, 100% 100%',
              backgroundPosition: '0 0, 0 100%, 0 0',
              backgroundRepeat: 'no-repeat',
              WebkitBackgroundClip: 'text',
              backgroundClip: 'text'
            }}
          >
            {/* Header */}
            <div className="flex pt-6 pr-6 pb-0 pl-6 items-start justify-between">
              <div className="flex items-center gap-4">
                <div 
                  className="flex items-center justify-center"
                  style={{
                    height: '2.5rem',
                    width: '2.5rem',
                    borderRadius: '50%',
                    background: 'rgba(255,255,255,0.12)',
                    border: '1px solid rgba(255,255,255,0.25)',
                    boxShadow: '0 2.8px 2.2px rgba(0, 0, 0, 0.034), 0 6.7px 5.3px rgba(0, 0, 0, 0.048), 0 12.5px 10px rgba(0, 0, 0, 0.06), 0 22.3px 17.9px rgba(0, 0, 0, 0.072), 0 41.8px 33.4px rgba(0, 0, 0, 0.086), 0 100px 80px rgba(0, 0, 0, 0.12)'
                  }}
                >
                  <i className="fas fa-bolt text-lg" style={{color: 'hsl(270, 95%, 68%)'}}></i>
                </div>
                <div>
                  <h1 className="text-2xl font-semibold tracking-tight" style={{fontFamily: '"Plus Jakarta Sans", sans-serif'}}>
                    Upgrade Plan
                  </h1>
                  <p className="text-sm opacity-80">Unlock premium AI capabilities</p>
                </div>
              </div>
              <button className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-white/10 transition-colors">
                <i className="fas fa-times text-sm opacity-60 hover:opacity-100"></i>
              </button>
            </div>

            {/* Scrollable Content */}
            <div 
              className="flex-1 overflow-y-auto pt-6 pr-6 pb-6 pl-6"
              style={{
                scrollbarWidth: 'thin',
                scrollbarColor: 'rgba(139, 92, 246, 0.5) transparent'
              }}
            >
              {/* Plan Info */}
              <div className="flex items-center gap-3 text-sm font-medium opacity-80 mb-4">
                <i className="fas fa-arrow-right text-xs text-emerald-400"></i>
                Upgrading from Basic to Pro
              </div>
              
              {/* Price Display */}
              <div className="flex gap-2 mb-6 items-end">
                <div 
                  className="gradient-text"
                  style={{
                    fontSize: '2.5rem',
                    fontWeight: 600,
                    lineHeight: 1,
                    background: 'linear-gradient(to right, rgba(255,255,255,0.9), rgba(255,255,255,0.7))',
                    WebkitBackgroundClip: 'text',
                    backgroundClip: 'text',
                    color: 'transparent'
                  }}
                >
                  $49
                </div>
                <div className="text-lg opacity-70 mb-2">/month</div>
              </div>

              {/* Features Grid */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div 
                  className="flex items-center gap-2"
                  style={{
                    fontSize: '0.8rem',
                    opacity: 0.9,
                    lineHeight: 1.3
                  }}
                >
                  <i className="fas fa-check text-emerald-400 text-xs"></i>
                  25,000 AI tokens/month
                </div>
                <div 
                  className="flex items-center gap-2"
                  style={{
                    fontSize: '0.8rem',
                    opacity: 0.9,
                    lineHeight: 1.3
                  }}
                >
                  <i className="fas fa-check text-emerald-400 text-xs"></i>
                  Priority processing
                </div>
                <div 
                  className="flex items-center gap-2"
                  style={{
                    fontSize: '0.8rem',
                    opacity: 0.9,
                    lineHeight: 1.3
                  }}
                >
                  <i className="fas fa-check text-emerald-400 text-xs"></i>
                  Advanced templates
                </div>
                <div 
                  className="flex items-center gap-2"
                  style={{
                    fontSize: '0.8rem',
                    opacity: 0.9,
                    lineHeight: 1.3
                  }}
                >
                  <i className="fas fa-check text-emerald-400 text-xs"></i>
                  24/7 priority support
                </div>
                <div 
                  className="flex items-center gap-2"
                  style={{
                    fontSize: '0.8rem',
                    opacity: 0.9,
                    lineHeight: 1.3
                  }}
                >
                  <i className="fas fa-check text-emerald-400 text-xs"></i>
                  Custom integrations
                </div>
                <div 
                  className="flex items-center gap-2"
                  style={{
                    fontSize: '0.8rem',
                    opacity: 0.9,
                    lineHeight: 1.3
                  }}
                >
                  <i className="fas fa-check text-emerald-400 text-xs"></i>
                  API access
                </div>
                <div 
                  className="flex items-center gap-2"
                  style={{
                    fontSize: '0.8rem',
                    opacity: 0.9,
                    lineHeight: 1.3
                  }}
                >
                  <i className="fas fa-check text-emerald-400 text-xs"></i>
                  Advanced analytics
                </div>
                <div 
                  className="flex items-center gap-2"
                  style={{
                    fontSize: '0.8rem',
                    opacity: 0.9,
                    lineHeight: 1.3
                  }}
                >
                  <i className="fas fa-check text-emerald-400 text-xs"></i>
                  Multi-user workspace
                </div>
              </div>

              {/* Feature tags */}
              <div className="flex flex-wrap gap-2 mb-6">
                <span className="text-[10px] px-2 py-1 rounded-full bg-white/10 border border-white/20">AI POWERED</span>
                <span className="text-[10px] px-2 py-1 rounded-full bg-white/10 border border-white/20">CLOUD SYNC</span>
                <span className="text-[10px] px-2 py-1 rounded-full bg-white/10 border border-white/20">TEAM READY</span>
                <span className="text-[10px] px-2 py-1 rounded-full bg-white/10 border border-white/20">ENTERPRISE</span>
              </div>

              <div 
                className="w-full mb-6"
                style={{
                  height: '1px',
                  backgroundImage: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3) 20%, rgba(255,255,255,0.5) 50%, rgba(255,255,255,0.3) 80%, transparent)'
                }}
              ></div>

              {/* Billing Notice */}
              <div 
                className="bg-white/5 border-white/10 border rounded-2xl mb-6 pt-4 pr-4 pb-4 pl-4"
                style={{
                  boxShadow: '0 2.8px 2.2px rgba(0, 0, 0, 0.034), 0 6.7px 5.3px rgba(0, 0, 0, 0.048), 0 12.5px 10px rgba(0, 0, 0, 0.06), 0 22.3px 17.9px rgba(0, 0, 0, 0.072), 0 41.8px 33.4px rgba(0, 0, 0, 0.086), 0 100px 80px rgba(0, 0, 0, 0.12)'
                }}
              >
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <i className="fas fa-info text-blue-400 text-xs"></i>
                  </div>
                  <div className="text-sm">
                    <p className="font-medium mb-1">Prorated Billing</p>
                    <p className="opacity-80">You'll be charged <span className="font-semibold text-white">$31.50</span> today for the remaining 19 days. Next month: full $49.</p>
                  </div>
                </div>
              </div>

              {/* Payment Methods */}
              <div className="space-y-4 mb-6">
                <h3 className="font-medium text-white flex items-center gap-2">
                  <i className="fas fa-credit-card text-sm opacity-70"></i>
                  Payment Method
                </h3>
                
                <div className="space-y-3">
                  <label 
                    className={`flex items-center justify-between cursor-pointer rounded-xl pt-4 pr-4 pb-4 pl-4 transition-all ${
                      selectedPayment === 'visa' 
                        ? 'bg-purple-500/15 border-purple-500/50' 
                        : 'bg-white/8 border-white/15 hover:bg-white/12 hover:border-purple-400/40'
                    }`}
                    style={{
                      border: '1px solid',
                      borderColor: selectedPayment === 'visa' ? 'rgba(139, 92, 246, 0.5)' : 'rgba(255, 255, 255, 0.15)',
                      background: selectedPayment === 'visa' ? 'rgba(139, 92, 246, 0.15)' : 'rgba(255, 255, 255, 0.08)',
                      boxShadow: '0 2.8px 2.2px rgba(0, 0, 0, 0.034), 0 6.7px 5.3px rgba(0, 0, 0, 0.048), 0 12.5px 10px rgba(0, 0, 0, 0.06), 0 22.3px 17.9px rgba(0, 0, 0, 0.072), 0 41.8px 33.4px rgba(0, 0, 0, 0.086), 0 100px 80px rgba(0, 0, 0, 0.12)'
                    }}
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white text-[10px] font-bold">
                        VISA
                      </div>
                      <div>
                        <p className="font-medium">•••• •••• •••• 4582</p>
                        <p className="text-xs opacity-70">Expires 12/28</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-[10px] px-2 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Default</span>
                      <input 
                        type="radio" 
                        name="payment" 
                        value="visa"
                        checked={selectedPayment === 'visa'}
                        onChange={() => setSelectedPayment('visa')}
                        className="text-purple-500"
                      />
                    </div>
                  </label>

                  <label 
                    className={`flex items-center justify-between cursor-pointer rounded-xl pt-4 pr-4 pb-4 pl-4 transition-all ${
                      selectedPayment === 'mastercard' 
                        ? 'bg-purple-500/15 border-purple-500/50' 
                        : 'bg-white/8 border-white/15 hover:bg-white/12 hover:border-purple-400/40'
                    }`}
                    style={{
                      border: '1px solid',
                      borderColor: selectedPayment === 'mastercard' ? 'rgba(139, 92, 246, 0.5)' : 'rgba(255, 255, 255, 0.15)',
                      background: selectedPayment === 'mastercard' ? 'rgba(139, 92, 246, 0.15)' : 'rgba(255, 255, 255, 0.08)'
                    }}
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-8 bg-gradient-to-r from-red-500 to-yellow-500 rounded-lg flex items-center justify-center text-white text-[10px] font-bold">
                        MC
                      </div>
                      <div>
                        <p className="font-medium">•••• •••• •••• 8291</p>
                        <p className="text-xs opacity-70">Expires 09/27</p>
                      </div>
                    </div>
                    <input 
                      type="radio" 
                      name="payment" 
                      value="mastercard"
                      checked={selectedPayment === 'mastercard'}
                      onChange={() => setSelectedPayment('mastercard')}
                      className="text-purple-500"
                    />
                  </label>

                  <label 
                    className={`flex items-center justify-between cursor-pointer rounded-xl pt-4 pr-4 pb-4 pl-4 transition-all ${
                      selectedPayment === 'amex' 
                        ? 'bg-purple-500/15 border-purple-500/50' 
                        : 'bg-white/8 border-white/15 hover:bg-white/12 hover:border-purple-400/40'
                    }`}
                    style={{
                      border: '1px solid',
                      borderColor: selectedPayment === 'amex' ? 'rgba(139, 92, 246, 0.5)' : 'rgba(255, 255, 255, 0.15)',
                      background: selectedPayment === 'amex' ? 'rgba(139, 92, 246, 0.15)' : 'rgba(255, 255, 255, 0.08)'
                    }}
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-8 bg-gray-700 rounded-lg flex items-center justify-center text-white text-[10px] font-bold">
                        AMEX
                      </div>
                      <div>
                        <p className="font-medium">•••• •••• •••• 7739</p>
                        <p className="text-xs opacity-70">Expires 05/26</p>
                      </div>
                    </div>
                    <input 
                      type="radio" 
                      name="payment" 
                      value="amex"
                      checked={selectedPayment === 'amex'}
                      onChange={() => setSelectedPayment('amex')}
                      className="text-purple-500"
                    />
                  </label>
                </div>
              </div>

              <div 
                className="w-full mb-6"
                style={{
                  height: '1px',
                  backgroundImage: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3) 20%, rgba(255,255,255,0.5) 50%, rgba(255,255,255,0.3) 80%, transparent)'
                }}
              ></div>

              {/* Additional Benefits */}
              <div className="mb-6">
                <h3 className="font-medium text-white mb-4">What's included:</h3>
                <div className="space-y-3">
                  <div className="flex items-start gap-3 text-sm">
                    <i className="fas fa-star text-yellow-400 text-xs mt-1"></i>
                    <div>
                      <p className="font-medium">Advanced AI Models</p>
                      <p className="opacity-70 text-xs">Access to GPT-4, Claude, and more premium models</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 text-sm">
                    <i className="fas fa-users text-blue-400 text-xs mt-1"></i>
                    <div>
                      <p className="font-medium">Team Collaboration</p>
                      <p className="opacity-70 text-xs">Share projects and collaborate with team members</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 text-sm">
                    <i className="fas fa-chart-line text-green-400 text-xs mt-1"></i>
                    <div>
                      <p className="font-medium">Advanced Analytics</p>
                      <p className="opacity-70 text-xs">Detailed insights and usage analytics</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Fixed Action Buttons */}
            <div className="p-6 pt-0 border-t border-white/10">
              <div className="flex flex-col sm:flex-row gap-3">
                <button 
                  className="flex-1 px-6 py-3 rounded-xl font-medium bg-white/5 border border-white/20 hover:bg-white/10 transition-all"
                  style={{
                    backdropFilter: 'blur(8px)',
                    WebkitBackdropFilter: 'blur(8px)'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-1px)'}
                  onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0px)'}
                  onClick={() => navigate('/')}
                >
                  Cancel
                </button>
                <button 
                  className="flex-1 px-6 py-3 rounded-xl font-medium bg-purple-500/30 border border-purple-500/50 hover:bg-purple-500/40 transition-all flex items-center justify-center gap-2"
                  style={{
                    backdropFilter: 'blur(8px)',
                    WebkitBackdropFilter: 'blur(8px)'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-1px)'}
                  onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0px)'}
                  onClick={handleUpgrade}
                  disabled={isProcessing}
                >
                  {isProcessing ? (
                    <>
                      <i className="fas fa-spinner animate-spin"></i>
                      Processing...
                    </>
                  ) : (
                    <>
                      <i className="fas fa-rocket text-sm"></i>
                      {user ? 'Upgrade to Pro' : 'Login to Upgrade'}
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Font Awesome */}
      <link 
        rel="stylesheet" 
        href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" 
      />
    </div>
  );
};

export default SubscriptionUpgrade;