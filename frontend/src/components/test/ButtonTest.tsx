import { useState } from 'react'
import { Button } from '../ui/Button'
import { Plus, Settings, LogOut } from 'lucide-react'

export function ButtonTest() {
  const [clickCount, setClickCount] = useState(0)
  const [lastClicked, setLastClicked] = useState('')

  const handleClick = (buttonName: string) => {
    console.log(`Button clicked: ${buttonName}`)
    setClickCount(prev => prev + 1)
    setLastClicked(buttonName)
    
    // Also test with alert to ensure it's truly working
    alert(`Button clicked: ${buttonName}`)
  }

  return (
    <div className="p-8 space-y-6">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h1 className="text-2xl font-bold mb-4">Button Interactivity Test</h1>
        
        <div className="mb-4 p-4 bg-gray-100 rounded">
          <p>Click Count: <strong>{clickCount}</strong></p>
          <p>Last Clicked: <strong>{lastClicked || 'None'}</strong></p>
        </div>

        <div className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold mb-2">Basic Buttons</h2>
            <div className="flex gap-4">
              <Button 
                variant="primary"
                onClick={() => handleClick('Primary Button')}
              >
                Primary Button
              </Button>
              
              <Button 
                variant="gradient"
                onClick={() => handleClick('Gradient Button')}
              >
                <Plus className="w-4 h-4 mr-2" />
                Gradient Button
              </Button>
              
              <Button 
                variant="ghost"
                onClick={() => handleClick('Ghost Button')}
              >
                Ghost Button
              </Button>
            </div>
          </div>

          <div>
            <h2 className="text-lg font-semibold mb-2">Icon Buttons</h2>
            <div className="flex gap-4">
              <Button 
                variant="primary"
                size="sm"
                onClick={() => handleClick('Settings')}
              >
                <Settings className="w-4 h-4" />
              </Button>
              
              <Button 
                variant="ghost"
                size="sm"
                onClick={() => handleClick('Logout')}
              >
                <LogOut className="w-4 h-4" />
              </Button>
            </div>
          </div>

          <div>
            <h2 className="text-lg font-semibold mb-2">Direct HTML Button</h2>
            <button 
              onClick={() => handleClick('HTML Button')}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Plain HTML Button
            </button>
          </div>

          <div>
            <h2 className="text-lg font-semibold mb-2">Debug Info</h2>
            <div className="text-sm text-gray-600 space-y-1">
              <p>Check browser console for click events</p>
              <p>All buttons should show an alert when clicked</p>
              <p>Counter should increment on each click</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}