# Component Usage Guide
## How to Use the Elegant UI Components

### Document Purpose
This guide provides practical examples and usage patterns for all UI components in the elegant design system. Follow these patterns to maintain consistency and achieve the same professional aesthetic throughout the application.

**Created**: October 12, 2025  
**Status**: ✅ **COMPLETE USAGE GUIDE**  
**Framework**: React + TypeScript + Tailwind CSS  
**Design System**: Elegant SaaS UI

---

## Core UI Components

### **Button Component**
```typescript
import { Button } from '../ui/Button'
import { Plus, Save, Trash2 } from 'lucide-react'

// Primary gradient button
<Button variant="gradient" size="lg" icon={<Plus size={18} />}>
  Create New
</Button>

// Secondary ghost button
<Button variant="ghost" className="group">
  <span className="gradient-text group-hover:from-primary-700 group-hover:to-accent-700">
    Secondary Action
  </span>
</Button>

// Loading state
<Button variant="primary" loading={isLoading} disabled={isLoading}>
  {isLoading ? 'Saving...' : 'Save Changes'}
</Button>

// Icon only button
<Button variant="ghost" size="sm">
  <Settings className="w-4 h-4" />
</Button>
```

### **Input Component**
```typescript
import { Input } from '../ui/Input'
import { Mail, Lock, Search } from 'lucide-react'

// Basic input with icon
<Input
  type="email"
  name="email"
  label="Email Address"
  placeholder="Enter your email"
  icon={<Mail size={18} />}
  variant="elegant"
  required
/>

// Input with error state
<div className="space-y-1">
  <Input
    name="password"
    label="Password"
    type="password"
    error={hasError}
    showPasswordToggle
    variant="elegant"
  />
  {hasError && (
    <p className="text-xs text-error-600 animate-slide-down">
      Password is required
    </p>
  )}
</div>

// Search input
<div className="relative">
  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
  <Input
    type="text"
    placeholder="Search..."
    className="pl-10"
  />
</div>
```

### **Card Component**
```typescript
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../ui/Card'

// Elegant card with glass effect
<Card variant="elegant" size="lg" className="relative backdrop-blur-fix">
  <CardHeader className="text-center space-y-4">
    <CardTitle className="text-2xl gradient-text-elegant">
      Card Title
    </CardTitle>
    <CardDescription>
      Card description with helpful information
    </CardDescription>
  </CardHeader>
  
  <CardContent className="space-y-6">
    <p>Card content goes here</p>
  </CardContent>
  
  <CardFooter>
    <Button variant="gradient" className="w-full">
      Action Button
    </Button>
  </CardFooter>
</Card>

// Stats card with hover effect
<Card className="group hover:shadow-elegant transition-all duration-300 hover:scale-105">
  <CardContent className="p-6">
    <div className="flex items-center space-x-3">
      <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center">
        <Icon className="w-6 h-6 text-primary-600" />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">1,234</p>
        <p className="text-sm text-gray-600">Total Users</p>
      </div>
    </div>
  </CardContent>
</Card>
```

---

## Layout Components

### **Navigation Component**
```typescript
import { Navigation } from '../layout/Navigation'

// Top navigation with user menu
<Navigation
  currentPage="dashboard"
  onPageChange={(page) => setCurrentPage(page)}
/>

// Sidebar navigation
import { SidebarNavigation } from '../layout/Navigation'

<div className="flex h-screen">
  <SidebarNavigation
    currentPage={currentPage}
    onPageChange={setCurrentPage}
    isCollapsed={isCollapsed}
    onToggleCollapse={() => setIsCollapsed(!isCollapsed)}
  />
  <main className="flex-1">
    {/* Main content */}
  </main>
</div>
```

### **Page Layout Pattern**
```typescript
// Full page with navigation
function MyPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-100">
      <Navigation currentPage="dashboard" />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-8">
          {/* Welcome section */}
          <div className="relative overflow-hidden animate-slide-up">
            <div className="absolute inset-0">
              <div className="absolute -top-20 -right-20 w-40 h-40 bg-gradient-to-br from-primary-400/10 to-accent-400/10 rounded-full blur-3xl animate-pulse-gentle" />
            </div>
            
            <div className="relative space-y-4">
              <h1 className="text-3xl font-bold text-gray-900">Page Title</h1>
              <p className="text-lg text-gray-600">Page description</p>
            </div>
          </div>

          {/* Content sections */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Main content */}
            <div className="lg:col-span-2">
              {/* Content */}
            </div>
            
            {/* Sidebar */}
            <div>
              {/* Sidebar content */}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
```

---

## Interactive Components

### **Modal Component**
```typescript
import { Modal, ConfirmationModal, LoadingModal } from '../ui/Modal'

// Basic modal
<Modal
  isOpen={isModalOpen}
  onClose={() => setIsModalOpen(false)}
  title="Modal Title"
  description="Optional description"
  size="lg"
>
  <div className="space-y-4">
    <p>Modal content goes here</p>
    <div className="flex justify-end space-x-3">
      <Button variant="ghost" onClick={() => setIsModalOpen(false)}>
        Cancel
      </Button>
      <Button variant="primary">
        Confirm
      </Button>
    </div>
  </div>
</Modal>

// Confirmation modal
<ConfirmationModal
  isOpen={showDeleteConfirm}
  onClose={() => setShowDeleteConfirm(false)}
  onConfirm={handleDelete}
  title="Delete Chatbot"
  message="Are you sure you want to delete this chatbot? This action cannot be undone."
  confirmText="Delete"
  cancelText="Cancel"
  type="danger"
/>

// Loading modal
<LoadingModal
  isOpen={isProcessing}
  title="Creating Chatbot"
  message="Please wait while we set up your new chatbot..."
/>
```

### **Toast Notifications**
```typescript
import { useToast } from '../ui/Toast'

function MyComponent() {
  const { showSuccess, showError, showWarning, showInfo } = useToast()

  const handleSuccess = () => {
    showSuccess(
      'Registration Successful!',
      'Your account has been created successfully.'
    )
  }

  const handleError = () => {
    showError(
      'Registration Failed',
      'Please check your information and try again.'
    )
  }

  const handleWarning = () => {
    showWarning(
      'Password Strength',
      'Please choose a stronger password for better security.'
    )
  }

  const handleInfo = () => {
    showInfo(
      'Feature Update',
      'New chat analytics are now available in your dashboard.'
    )
  }
}

// Wrap your app with ToastProvider
import { ToastProvider } from '../ui/Toast'

function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ToastProvider>
  )
}
```

### **Loading States**
```typescript
import { LoadingSpinner, LoadingOverlay, SkeletonLoader, CardSkeleton } from '../ui/LoadingSpinner'

// Simple spinner
<LoadingSpinner size="md" message="Loading..." />

// Elegant spinner with branding
<LoadingSpinner 
  size="lg" 
  variant="branded" 
  message="Initializing your dashboard..."
/>

// Full screen overlay
<LoadingOverlay 
  isLoading={isPageLoading}
  message="Setting up your workspace..."
  variant="elegant"
/>

// Skeleton loading for content
<div className="space-y-4">
  <SkeletonLoader lines={3} />
  <CardSkeleton />
</div>
```

---

## Form Patterns

### **Complete Form Example**
```typescript
function RegistrationForm() {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    firstName: '',
    lastName: ''
  })
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)

  return (
    <Card variant="elegant" size="lg" className="relative backdrop-blur-fix">
      <CardHeader className="text-center space-y-4">
        <div className="mx-auto w-16 h-16 bg-gradient-to-br from-accent-500 to-primary-500 rounded-2xl flex items-center justify-center shadow-lg shadow-accent-500/25 animate-bounce-gentle">
          <Sparkles className="w-8 h-8 text-white" />
        </div>
        
        <CardTitle className="text-3xl gradient-text-elegant">
          Create Account
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Error display */}
        {error && (
          <div className="bg-gradient-to-r from-error-50 to-error-100 border border-error-200 text-error-700 px-4 py-3 rounded-xl animate-slide-down">
            <div className="flex items-center space-x-2">
              <X size={16} className="text-error-500" />
              <span className="text-sm font-medium">{error}</span>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Name fields */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <Input
                name="firstName"
                label="First Name"
                placeholder="John"
                value={formData.firstName}
                onChange={handleChange}
                variant="elegant"
                icon={<User size={18} />}
                error={errors.firstName}
                disabled={loading}
              />
              {errors.firstName && (
                <p className="text-xs text-error-600 animate-slide-down">
                  {errors.firstName}
                </p>
              )}
            </div>
            
            <div className="space-y-1">
              <Input
                name="lastName"
                label="Last Name"
                placeholder="Doe"
                value={formData.lastName}
                onChange={handleChange}
                variant="elegant"
                icon={<User size={18} />}
                error={errors.lastName}
                disabled={loading}
              />
              {errors.lastName && (
                <p className="text-xs text-error-600 animate-slide-down">
                  {errors.lastName}
                </p>
              )}
            </div>
          </div>

          <Button
            type="submit"
            variant="gradient"
            size="lg"
            loading={loading}
            className="w-full"
            disabled={loading}
          >
            {loading ? 'Creating Account...' : 'Create Account'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
```

### **Search and Filter Pattern**
```typescript
function SearchableList() {
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState('all')

  return (
    <div className="space-y-6">
      {/* Search and filters */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              type="text"
              placeholder="Search items..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 w-64"
            />
          </div>
          
          <select 
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Items</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>

        <Button variant="primary" icon={<Plus size={16} />}>
          Add New
        </Button>
      </div>

      {/* Results */}
      <div className="grid gap-4">
        {filteredItems.map((item) => (
          <Card key={item.id} className="group hover:shadow-elegant transition-all duration-300">
            {/* Card content */}
          </Card>
        ))}
      </div>
    </div>
  )
}
```

---

## Badge Components

### **Status and Performance Badges**
```typescript
import { Badge, StatusBadge, PlanBadge, PerformanceBadge } from '../ui/Badge'

// Basic badges
<Badge variant="primary">New</Badge>
<Badge variant="success" icon={<Check size={12} />}>
  Verified
</Badge>

// Status badges
<StatusBadge status="active" />
<StatusBadge status="training" />
<StatusBadge status="error" />

// Plan badges
<PlanBadge plan="pro" />
<PlanBadge plan="enterprise" />

// Performance badges
<PerformanceBadge score={95} />
<PerformanceBadge score={72} />
```

### **Custom Badge Usage**
```typescript
// Custom gradient badge
<Badge 
  variant="elegant" 
  className="bg-gradient-to-r from-accent-500 to-primary-500 text-white"
>
  Premium Feature
</Badge>

// Animated badge
<Badge 
  variant="success" 
  pulse={true}
  icon={<Sparkles size={12} />}
>
  Live
</Badge>
```

---

## Page Templates

### **Dashboard Page Template**
```typescript
import { Navigation } from '../layout/Navigation'
import { TopBar } from '../layout/Navigation'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'

function DashboardPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-100">
      <Navigation currentPage="dashboard" />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-8">
          {/* Welcome section with decorative background */}
          <div className="relative overflow-hidden animate-slide-up">
            <div className="absolute inset-0">
              <div className="absolute -top-20 -right-20 w-40 h-40 bg-gradient-to-br from-primary-400/10 to-accent-400/10 rounded-full blur-3xl animate-pulse-gentle" />
            </div>
            
            <div className="relative space-y-4">
              <div className="flex items-center space-x-3">
                <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
                <Badge variant="success" pulse>Online</Badge>
              </div>
              <p className="text-lg text-gray-600">
                Welcome back! Here's what's happening.
              </p>
            </div>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 animate-slide-up" style={{animationDelay: '0.1s'}}>
            {stats.map((stat) => (
              <StatCard key={stat.id} {...stat} />
            ))}
          </div>

          {/* Content grid */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-8 animate-slide-up" style={{animationDelay: '0.2s'}}>
            <div className="xl:col-span-2">
              {/* Main content */}
            </div>
            <div>
              {/* Sidebar content */}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
```

### **Modal Dialog Template**
```typescript
function CreateBotModal({ isOpen, onClose, onSuccess }) {
  const [formData, setFormData] = useState({ name: '', description: '' })
  const [loading, setLoading] = useState(false)

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Create New Chatbot"
      description="Set up your AI assistant"
      size="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        <Input
          name="name"
          label="Chatbot Name"
          placeholder="Customer Support Bot"
          value={formData.name}
          onChange={handleChange}
          variant="elegant"
          icon={<Bot size={18} />}
          required
        />

        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">
            Description
          </label>
          <textarea
            name="description"
            placeholder="Describe what your chatbot will help with..."
            value={formData.description}
            onChange={handleChange}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
          />
        </div>

        <div className="flex justify-end space-x-3">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button 
            type="submit" 
            variant="gradient" 
            loading={loading}
            disabled={loading}
          >
            {loading ? 'Creating...' : 'Create Chatbot'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
```

---

## Animation Patterns

### **Entrance Animations**
```typescript
// Staggered entrance for lists
<div className="space-y-4">
  {items.map((item, index) => (
    <div 
      key={item.id}
      className="animate-slide-up"
      style={{ animationDelay: `${index * 0.1}s` }}
    >
      <Card>{/* Card content */}</Card>
    </div>
  ))}
</div>

// Page entrance
<div className="animate-fade-in">
  <div className="animate-slide-up">
    <h1>Main Title</h1>
  </div>
  <div className="animate-slide-up" style={{animationDelay: '0.1s'}}>
    <p>Subtitle content</p>
  </div>
</div>
```

### **Hover Interactions**
```typescript
// Card hover effects
<Card className="group hover:shadow-elegant transition-all duration-300 hover:scale-[1.02]">
  <CardContent>
    <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200">
      <Button variant="ghost" size="sm">
        <Edit className="w-4 h-4" />
      </Button>
    </div>
  </CardContent>
</Card>

// Button with icon animation
<Button className="group">
  <span>Learn More</span>
  <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
</Button>

// Icon scale on hover
<Button variant="ghost" className="group">
  <Plus className="w-4 h-4 mr-2 group-hover:scale-110 transition-transform" />
  <span>Add Item</span>
</Button>
```

---

## Error Handling Patterns

### **Form Error Display**
```typescript
// Field-level errors
<div className="space-y-1">
  <Input
    name="email"
    error={hasEmailError}
    // ... other props
  />
  {hasEmailError && (
    <p className="text-xs text-error-600 animate-slide-down">
      {emailError}
    </p>
  )}
</div>

// Form-level error
{formError && (
  <div className="bg-gradient-to-r from-error-50 to-error-100 border border-error-200 text-error-700 px-4 py-3 rounded-xl animate-slide-down">
    <div className="flex items-center space-x-2">
      <AlertTriangle size={16} className="text-error-500" />
      <span className="text-sm font-medium">{formError}</span>
    </div>
  </div>
)}
```

### **Loading Error States**
```typescript
function DataComponent() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  if (loading) {
    return (
      <div className="space-y-4">
        <SkeletonLoader lines={3} />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Card className="text-center py-8">
        <CardContent>
          <div className="space-y-4">
            <div className="w-16 h-16 mx-auto bg-error-100 rounded-full flex items-center justify-center">
              <AlertTriangle className="w-8 h-8 text-error-500" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Something went wrong</h3>
              <p className="text-gray-600 mt-2">{error}</p>
            </div>
            <Button variant="primary" onClick={retry}>
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div>
      {/* Render data */}
    </div>
  )
}
```

---

## Responsive Design Patterns

### **Grid Layouts**
```typescript
// Responsive card grid
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
  {items.map((item) => (
    <Card key={item.id}>
      {/* Card content */}
    </Card>
  ))}
</div>

// Responsive sidebar layout
<div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
  <div className="lg:col-span-3">
    {/* Main content */}
  </div>
  <div className="lg:col-span-1">
    {/* Sidebar */}
  </div>
</div>
```

### **Mobile-First Forms**
```typescript
// Stack on mobile, side-by-side on larger screens
<div className="space-y-4 sm:space-y-0 sm:grid sm:grid-cols-2 sm:gap-4">
  <Input label="First Name" />
  <Input label="Last Name" />
</div>

// Hide/show elements by screen size
<div className="hidden sm:block">
  {/* Desktop only content */}
</div>

<div className="sm:hidden">
  {/* Mobile only content */}
</div>
```

---

## Performance Best Practices

### **Component Optimization**
```typescript
// Memoize expensive components
const ExpensiveComponent = React.memo(({ data }) => {
  return <div>{/* Expensive rendering */}</div>
})

// Lazy load heavy components
const HeavyModal = React.lazy(() => import('./HeavyModal'))

function MyComponent() {
  return (
    <Suspense fallback={<LoadingSpinner variant="elegant" />}>
      {showModal && <HeavyModal />}
    </Suspense>
  )
}
```

### **Animation Performance**
```typescript
// Use transform and opacity for smooth animations
<div className="transform transition-transform duration-200 hover:scale-105">
  {/* Content */}
</div>

// Avoid animating layout properties
// ❌ Don't do this:
// .animate-width { animation: width 0.3s ease }

// ✅ Do this instead:
// .animate-scale { animation: scale 0.3s ease }
```

---

## Accessibility Guidelines

### **Semantic HTML**
```typescript
// Proper form labels
<label htmlFor="email" className="label-base">
  Email Address
</label>
<Input id="email" type="email" />

// Button semantics
<button type="submit" aria-describedby="error-message">
  Submit Form
</button>
{error && <p id="error-message" role="alert">{error}</p>}
```

### **Focus Management**
```typescript
// Focus trap for modals
import { useEffect, useRef } from 'react'

function Modal({ isOpen }) {
  const firstFocusableRef = useRef(null)

  useEffect(() => {
    if (isOpen && firstFocusableRef.current) {
      firstFocusableRef.current.focus()
    }
  }, [isOpen])

  return (
    <div>
      <input ref={firstFocusableRef} />
      {/* Modal content */}
    </div>
  )
}
```

---

## Quality Checklist

### **Before Using Components**
- [ ] ✅ **Props Defined**: All required props provided
- [ ] ✅ **Error States**: Error handling implemented
- [ ] ✅ **Loading States**: Loading indicators added
- [ ] ✅ **Responsive**: Works on all screen sizes
- [ ] ✅ **Accessible**: Proper semantics and focus management
- [ ] ✅ **Animations**: Smooth, performant transitions
- [ ] ✅ **Styling**: Follows design system patterns

### **Component Integration**
- [ ] ✅ **Type Safety**: TypeScript interfaces defined
- [ ] ✅ **Event Handling**: Proper event propagation
- [ ] ✅ **State Management**: Clean state updates
- [ ] ✅ **Side Effects**: useEffect cleanup implemented
- [ ] ✅ **Error Boundaries**: Graceful error handling

---

## Quick Reference

### **Color Classes**
```css
/* Primary colors */
bg-primary-50, bg-primary-100, bg-primary-500, bg-primary-600
text-primary-600, text-primary-700

/* Accent colors */
bg-accent-50, bg-accent-500, text-accent-600

/* Status colors */
bg-success-50, bg-success-500, text-success-700
bg-warning-50, bg-warning-500, text-warning-700
bg-error-50, bg-error-500, text-error-700
```

### **Common Animation Classes**
```css
animate-fade-in          /* Smooth fade entrance */
animate-slide-up         /* Slide up entrance */
animate-slide-down       /* Slide down entrance */
animate-scale-in         /* Scale in entrance */
animate-pulse-gentle     /* Subtle pulsing */
animate-bounce-gentle    /* Gentle bouncing */
animate-float           /* Floating motion */
```

### **Spacing Scale**
```css
space-y-1  /* 0.25rem spacing */
space-y-2  /* 0.5rem spacing */
space-y-4  /* 1rem spacing */
space-y-6  /* 1.5rem spacing */
space-y-8  /* 2rem spacing */
```

### **Shadow Classes**
```css
shadow-sm           /* Subtle shadow */
shadow-elegant      /* Elegant multi-layer shadow */
shadow-lg           /* Large shadow */
shadow-primary-500/25  /* Colored shadow with opacity */
```

---

## Examples in Action

### **Complete Registration Flow**
```typescript
function RegistrationFlow() {
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const { showSuccess, showError } = useToast()

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 bg-gradient-to-br from-gray-50 via-white to-gray-100" />
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-gradient-to-br from-primary-400/15 to-accent-400/15 rounded-full blur-3xl animate-float" />
      </div>

      <div className="relative z-10 min-h-screen flex items-center justify-center">
        <Card variant="elegant" size="lg" className="relative backdrop-blur-fix">
          <CardHeader className="text-center">
            <div className="mx-auto w-16 h-16 bg-gradient-to-br from-accent-500 to-primary-500 rounded-2xl flex items-center justify-center shadow-lg animate-bounce-gentle">
              <Sparkles className="w-8 h-8 text-white" />
            </div>
            <CardTitle className="text-3xl gradient-text-elegant">
              {step === 1 ? 'Create Account' : 'Complete Setup'}
            </CardTitle>
          </CardHeader>

          <CardContent>
            {step === 1 ? (
              <RegistrationForm onSuccess={() => setStep(2)} />
            ) : (
              <SetupForm onSuccess={onComplete} />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
```

---

**Status**: ✅ **COMPLETE COMPONENT USAGE GUIDE**

This guide provides everything needed to replicate the elegant UI style across all application components. Follow these patterns to maintain consistent, professional design quality.