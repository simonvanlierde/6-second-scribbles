# Mobile Canvas Improvements

## Overview
This document summarizes the mobile-friendly improvements made to the drawing canvas functionality.

## Changes Made

### 1. Fixed Coordinate Mapping (`src/composables/useDrawingCanvas.ts`)

**Problem**: Drawing coordinates were incorrectly mapped on smaller screens, causing cursor/touch misalignment.

**Solution**:
- Updated `getCoordinates()` function to work in CSS coordinate space
- The canvas uses `setTransform(dpr, 0, 0, dpr, 0, 0)` which means drawing happens in CSS space, not internal pixel space
- Added coordinate clamping to prevent drawing outside canvas bounds
- Ensured both mouse and touch events use the same coordinate calculation

**Code Changes**:
```typescript
function getCoordinates(event: MouseEvent | TouchEvent): { x: number; y: number } {
  if (!canvasRef.value) return { x: 0, y: 0 }

  const rect = canvasRef.value.getBoundingClientRect()
  const cssWidth = rect.width
  const cssHeight = rect.height

  // Extract client coordinates from event
  let clientX: number, clientY: number
  if (event instanceof MouseEvent) {
    clientX = event.clientX
    clientY = event.clientY
  } else {
    const touch = event.touches[0]
    if (!touch) return { x: 0, y: 0 }
    clientX = touch.clientX
    clientY = touch.clientY
  }

  // Convert to CSS space and clamp
  const x = Math.max(0, Math.min(clientX - rect.left, cssWidth))
  const y = Math.max(0, Math.min(clientY - rect.top, cssHeight))

  return { x, y }
}
```

### 2. Improved Touch Event Handling

**Changes**:
- Added proper `passive: false` option to touch event listeners to allow preventDefault
- Implemented preventDefault in touch handlers to prevent scrolling while drawing
- Removed duplicate touch event listeners for better performance

**Code Changes**:
```typescript
// Event listener setup with proper options
canvasRef.value.addEventListener('touchstart', handleTouchStart, { passive: false })
canvasRef.value.addEventListener('touchmove', handleTouchMove, { passive: false })

// Touch handlers with preventDefault
function handleTouchStart(event: TouchEvent) {
  event.preventDefault()  // Prevent scrolling
  startDrawing(event)
}

function handleTouchMove(event: TouchEvent) {
  event.preventDefault()  // Prevent scrolling
  draw(event)
}
```

### 3. Responsive Canvas Styling (`src/views/GameView.vue`)

Added comprehensive media queries for mobile devices:

**Tablet (≤768px)**:
- Stacked layout (category card above canvas)
- Reduced padding and font sizes
- Canvas min-height: 300px
- Added `touch-action: none` to prevent browser touch gestures

**Mobile (≤480px)**:
- Further reduced font sizes and spacing
- Canvas min-height: 250px
- Optimized tool controls for small screens
- Single-column guess grid

### 4. Shared Drawpad Mobile Optimization (`src/components/SharedDrawpad.vue`)

**Changes**:
- Added `touch-action: none` to prevent scrolling
- Implemented responsive height adjustments:
  - Desktop: 200px
  - Tablet: 180px
  - Mobile: 150px
- Added flex-wrap to tools for better mobile layout
- Optimized button and label sizes for mobile

### 5. Viewport Meta Tag Enhancement (`index.html`)

**Updated viewport settings**:
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
```

This prevents accidental zooming while drawing on mobile devices.

## Testing Recommendations

### Device Testing
1. **iOS devices**: iPhone SE, iPhone 14, iPad
2. **Android devices**: Various screen sizes (small, medium, large)
3. **Browsers**: Safari, Chrome, Firefox mobile

### Test Scenarios
- [ ] Drawing accuracy on different screen sizes
- [ ] Touch responsiveness and smoothness
- [ ] No accidental page scrolling while drawing
- [ ] Canvas sizing adapts properly to screen
- [ ] Tools remain accessible on small screens
- [ ] Multi-touch doesn't interfere with drawing
- [ ] Landscape and portrait orientations

## Benefits

1. **Accurate Drawing**: Cursor/touch now aligns perfectly with drawing position
2. **No Scrolling Issues**: Page doesn't scroll while drawing on mobile
3. **Responsive Layout**: UI adapts to all screen sizes from 320px to desktop
4. **Better UX**: Controls are accessible and appropriately sized for touch input
5. **Performance**: Removed duplicate event listeners and optimized event handling

## Future Considerations

The user asked: "should we just have separate app for mobile?"

### Current Approach (Responsive Web)
✅ Pros:
- Single codebase to maintain
- Works across all devices
- No app store submission needed
- Instant updates

❌ Cons:
- Limited by browser capabilities
- Can't use native device features
- Potential performance constraints

### Native Mobile App Approach
✅ Pros:
- Better performance
- Native gesture support
- Offline capabilities
- Access to device features (camera, etc.)

❌ Cons:
- Separate codebase to maintain
- App store approval process
- Update distribution complexity
- Higher development cost

**Recommendation**: Test the current responsive implementation thoroughly. If drawing performance is satisfactory and users can play comfortably on mobile browsers, continue with the responsive web approach. Only consider a native app if there are significant UX or performance issues that can't be solved with web technologies.

## Files Modified

1. `/src/composables/useDrawingCanvas.ts` - Core canvas coordinate and touch handling
2. `/src/views/GameView.vue` - Main game canvas responsive styles
3. `/src/components/SharedDrawpad.vue` - Waiting room canvas responsive styles
4. `/index.html` - Viewport meta tag
