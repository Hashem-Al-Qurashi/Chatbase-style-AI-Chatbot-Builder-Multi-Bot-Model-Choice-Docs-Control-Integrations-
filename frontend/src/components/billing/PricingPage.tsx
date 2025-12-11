import React, { useState, useEffect } from 'react';
import { Check, X, Zap, Users, Database, Settings, Crown, AlertCircle } from 'lucide-react';

interface PlanFeature {
  name: string;
  included: boolean;
  limit?: string;
}

interface PricingPlan {
  id: string;
  name: string;
  description: string;
  price_monthly: number;
  price_yearly: number;
  message_credits: number;
  max_ai_agents: number;
  max_ai_actions: number;
  storage_limit_mb: number;
  max_seats: number;
  is_popular: boolean;
  features: {
    api_access: boolean;
    integrations: boolean;
    advanced_analytics: boolean;
    priority_support: boolean;
    custom_branding: boolean;
    unlimited_training_links: boolean;
    agents_persist: boolean;
  };
  special_notes?: string[];
}

interface Addon {
  id: string;
  name: string;
  description: string;
  price_monthly: number;
  addon_type: string;
}

const PricingPage: React.FC = () => {
  const [isYearly, setIsYearly] = useState(false);
  const [plans, setPlans] = useState<PricingPlan[]>([]);
  const [addons, setAddons] = useState<Addon[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Mock data matching Chatbase structure
    const mockPlans: PricingPlan[] = [
      {
        id: 'free',
        name: 'Free',
        description: 'Perfect for testing and personal projects',
        price_monthly: 0,
        price_yearly: 0,
        message_credits: 50,
        max_ai_agents: 1,
        max_ai_actions: 0,
        storage_limit_mb: 1,
        max_seats: 1,
        is_popular: false,
        features: {
          api_access: false,
          integrations: false,
          advanced_analytics: false,
          priority_support: false,
          custom_branding: false,
          unlimited_training_links: false,
          agents_persist: false,
        },
        special_notes: ['AI agents deleted after 14 days of inactivity', '400KB storage limit']
      },
      {
        id: 'hobby',
        name: 'Hobby',
        description: 'For solo founders and small projects',
        price_monthly: 40,
        price_yearly: 32,
        message_credits: 2000,
        max_ai_agents: 1,
        max_ai_actions: 5,
        storage_limit_mb: 40,
        max_seats: 1,
        is_popular: true,
        features: {
          api_access: true,
          integrations: true,
          advanced_analytics: false,
          priority_support: false,
          custom_branding: false,
          unlimited_training_links: true,
          agents_persist: true,
        }
      },
      {
        id: 'standard',
        name: 'Standard',
        description: 'For small teams and growing businesses',
        price_monthly: 150,
        price_yearly: 120,
        message_credits: 12000,
        max_ai_agents: 2,
        max_ai_actions: 10,
        storage_limit_mb: 33,
        max_seats: 3,
        is_popular: false,
        features: {
          api_access: true,
          integrations: true,
          advanced_analytics: false,
          priority_support: false,
          custom_branding: false,
          unlimited_training_links: true,
          agents_persist: true,
        }
      },
      {
        id: 'pro',
        name: 'Pro',
        description: 'For businesses needing advanced features',
        price_monthly: 500,
        price_yearly: 400,
        message_credits: 40000,
        max_ai_agents: 3,
        max_ai_actions: 15,
        storage_limit_mb: 33,
        max_seats: 5,
        is_popular: false,
        features: {
          api_access: true,
          integrations: true,
          advanced_analytics: true,
          priority_support: true,
          custom_branding: false,
          unlimited_training_links: true,
          agents_persist: true,
        }
      }
    ];

    const mockAddons: Addon[] = [
      {
        id: 'extra_credits',
        name: 'Extra Message Credits',
        description: '1,000 additional message credits per month',
        price_monthly: 12,
        addon_type: 'credits'
      },
      {
        id: 'auto_recharge',
        name: 'Auto-recharge Credits',
        description: 'Automatically adds 1,000 credits when you run low',
        price_monthly: 14,
        addon_type: 'credits'
      },
      {
        id: 'extra_agent',
        name: 'Additional AI Agent',
        description: 'Add one more AI agent to your account',
        price_monthly: 7,
        addon_type: 'agents'
      },
      {
        id: 'remove_branding',
        name: 'Remove Branding',
        description: 'Remove "Powered by [Brand]" from chatbots',
        price_monthly: 39,
        addon_type: 'branding'
      },
      {
        id: 'custom_domain',
        name: 'Custom Domain',
        description: 'Use your own domain for chat widgets',
        price_monthly: 59,
        addon_type: 'domain'
      }
    ];

    setPlans(mockPlans);
    setAddons(mockAddons);
    setLoading(false);
  }, []);

  const formatPrice = (price: number) => {
    return price === 0 ? 'Free' : `$${price}`;
  };

  const formatCredits = (credits: number) => {
    if (credits >= 1000) {
      return `${(credits / 1000).toFixed(0)}K`;
    }
    return credits.toString();
  };

  const getStorageDisplay = (mb: number) => {
    if (mb < 1) return '400KB';
    if (mb >= 1000) return `${(mb / 1000).toFixed(0)}GB`;
    return `${mb}MB`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Simple, Transparent Pricing
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Choose the perfect plan for your AI chatbot needs
          </p>
          
          {/* Billing Toggle */}
          <div className="flex items-center justify-center space-x-4">
            <span className={`${!isYearly ? 'text-gray-900' : 'text-gray-500'}`}>
              Monthly
            </span>
            <button
              onClick={() => setIsYearly(!isYearly)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                isYearly ? 'bg-blue-600' : 'bg-gray-300'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  isYearly ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
            <span className={`${isYearly ? 'text-gray-900' : 'text-gray-500'}`}>
              Yearly
            </span>
            <span className="text-sm bg-green-100 text-green-800 px-2 py-1 rounded-full">
              Save 20%
            </span>
          </div>
        </div>

        {/* Pricing Plans */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-16">
          {plans.map((plan) => {
            const price = isYearly ? plan.price_yearly : plan.price_monthly;
            
            return (
              <div
                key={plan.id}
                className={`relative bg-white rounded-2xl shadow-lg border-2 ${
                  plan.is_popular
                    ? 'border-blue-500 ring-2 ring-blue-200'
                    : 'border-gray-200 hover:border-gray-300'
                } transition-all duration-200 hover:shadow-xl`}
              >
                {plan.is_popular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <span className="bg-blue-600 text-white px-4 py-1 rounded-full text-sm font-medium flex items-center">
                      <Crown className="w-4 h-4 mr-1" />
                      Most Popular
                    </span>
                  </div>
                )}

                <div className="p-6">
                  <h3 className="text-2xl font-bold text-gray-900 mb-2">
                    {plan.name}
                  </h3>
                  <p className="text-gray-600 mb-6">
                    {plan.description}
                  </p>

                  <div className="mb-6">
                    <div className="flex items-baseline">
                      <span className="text-4xl font-bold text-gray-900">
                        {formatPrice(price)}
                      </span>
                      {price > 0 && (
                        <span className="text-gray-600 ml-2">
                          /{isYearly ? 'year' : 'month'}
                        </span>
                      )}
                    </div>
                    {isYearly && price > 0 && (
                      <div className="text-sm text-gray-500 mt-1">
                        ${plan.price_monthly}/month billed monthly
                      </div>
                    )}
                  </div>

                  {/* Key Metrics */}
                  <div className="space-y-4 mb-6">
                    <div className="flex items-center text-sm">
                      <Zap className="w-4 h-4 mr-2 text-blue-600" />
                      <span className="font-medium">
                        {formatCredits(plan.message_credits)} message credits
                      </span>
                    </div>
                    <div className="flex items-center text-sm">
                      <Settings className="w-4 h-4 mr-2 text-green-600" />
                      <span>
                        {plan.max_ai_agents} AI agent{plan.max_ai_agents > 1 ? 's' : ''}
                      </span>
                    </div>
                    <div className="flex items-center text-sm">
                      <Database className="w-4 h-4 mr-2 text-purple-600" />
                      <span>{getStorageDisplay(plan.storage_limit_mb)} per agent</span>
                    </div>
                    {plan.max_ai_actions > 0 && (
                      <div className="flex items-center text-sm">
                        <Zap className="w-4 h-4 mr-2 text-orange-600" />
                        <span>{plan.max_ai_actions} AI Actions per agent</span>
                      </div>
                    )}
                    {plan.max_seats > 1 && (
                      <div className="flex items-center text-sm">
                        <Users className="w-4 h-4 mr-2 text-indigo-600" />
                        <span>{plan.max_seats} seats</span>
                      </div>
                    )}
                  </div>

                  {/* Features */}
                  <div className="space-y-2 mb-6">
                    <div className="flex items-center text-sm">
                      <Check className="w-4 h-4 mr-2 text-green-600" />
                      <span>Embed on unlimited websites</span>
                    </div>
                    {plan.features.unlimited_training_links && (
                      <div className="flex items-center text-sm">
                        <Check className="w-4 h-4 mr-2 text-green-600" />
                        <span>Unlimited training links</span>
                      </div>
                    )}
                    {plan.features.api_access ? (
                      <div className="flex items-center text-sm">
                        <Check className="w-4 h-4 mr-2 text-green-600" />
                        <span>API access</span>
                      </div>
                    ) : plan.name === 'Free' && (
                      <div className="flex items-center text-sm">
                        <X className="w-4 h-4 mr-2 text-gray-400" />
                        <span className="text-gray-500">API access</span>
                      </div>
                    )}
                    {plan.features.integrations && (
                      <div className="flex items-center text-sm">
                        <Check className="w-4 h-4 mr-2 text-green-600" />
                        <span>Integrations</span>
                      </div>
                    )}
                    {plan.features.advanced_analytics && (
                      <div className="flex items-center text-sm">
                        <Check className="w-4 h-4 mr-2 text-green-600" />
                        <span>Advanced analytics</span>
                      </div>
                    )}
                    {plan.features.priority_support && (
                      <div className="flex items-center text-sm">
                        <Check className="w-4 h-4 mr-2 text-green-600" />
                        <span>Priority support</span>
                      </div>
                    )}
                  </div>

                  {/* Special Notes */}
                  {plan.special_notes && (
                    <div className="space-y-2 mb-6">
                      {plan.special_notes.map((note, index) => (
                        <div key={index} className="flex items-start text-sm text-amber-700 bg-amber-50 p-2 rounded">
                          <AlertCircle className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
                          <span>{note}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* CTA Button */}
                  <button
                    className={`w-full py-3 px-4 rounded-lg font-medium transition-colors ${
                      plan.is_popular
                        ? 'bg-blue-600 hover:bg-blue-700 text-white'
                        : plan.name === 'Free'
                        ? 'bg-gray-100 hover:bg-gray-200 text-gray-900'
                        : 'bg-gray-900 hover:bg-gray-800 text-white'
                    }`}
                  >
                    {plan.name === 'Free' ? 'Get Started' : 'Upgrade to ' + plan.name}
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Add-ons Section */}
        <div className="bg-white rounded-2xl shadow-lg p-8">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Add-ons & Extras
            </h2>
            <p className="text-gray-600">
              Enhance your plan with additional features and resources
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {addons.map((addon) => (
              <div
                key={addon.id}
                className="border border-gray-200 rounded-lg p-6 hover:border-gray-300 transition-colors"
              >
                <h3 className="font-semibold text-gray-900 mb-2">
                  {addon.name}
                </h3>
                <p className="text-gray-600 text-sm mb-4">
                  {addon.description}
                </p>
                <div className="flex items-center justify-between">
                  <span className="text-lg font-bold text-gray-900">
                    ${addon.price_monthly}/month
                  </span>
                  <button className="text-blue-600 hover:text-blue-700 text-sm font-medium">
                    Add
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* FAQ or Additional Info */}
        <div className="text-center mt-12">
          <p className="text-gray-600">
            Need custom limits or enterprise features?{' '}
            <a href="#" className="text-blue-600 hover:text-blue-700 font-medium">
              Contact us for Enterprise pricing
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default PricingPage;