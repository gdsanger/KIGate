# KIGate Dark Mode UI Theme

## Overview

KIGate features a modern, futuristic dark mode theme built on Bootstrap 5. The theme provides a sleek, elegant interface with technical precision and subtle color accents (Indigo/Violet) that reflect the character of the application.

## Design Philosophy

- **Exclusively Dark Mode**: Professional, modern appearance suitable for extended use
- **Futuristic Aesthetics**: Clean lines, gradients, and subtle glow effects
- **Technical Precision**: High contrast for readability and clarity
- **Consistent Experience**: Global color scheme applied across all components

## Color Palette

### Base Colors
| Element | Color | HEX | Description |
|---------|-------|-----|-------------|
| Body Background | Deep Anthracite | `#0F1116` | Main background surface |
| Surface (Cards, Panels) | Dark Gray | `#1A1D24` | Container backgrounds |
| Surface Hover | Lighter Gray | `#22252B` | Hover state for surfaces |
| Border / Divider | Dark Gray | `#2C2F36` | Lines and borders |

### Text Colors
| Element | Color | HEX | Description |
|---------|-------|-----|-------------|
| Primary Text | Almost White | `#E4E7EB` | Main text content |
| Muted Text | Medium Gray | `#9CA3AF` | Secondary text |
| Links | Violet | `#8B5CF6` | Hyperlinks |
| Link Hover | Light Violet | `#A78BFA` | Link hover state |

### Accent Colors
| Element | Color | HEX | Description |
|---------|-------|-----|-------------|
| Primary | Indigo | `#6366F1` | Active elements, primary buttons |
| Secondary | Violet | `#8B5CF6` | Hover states, secondary accents |
| Success | Green | `#22C55E` | Positive actions and states |
| Warning | Yellow | `#EAB308` | Warning messages |
| Danger | Red | `#EF4444` | Error states |
| Info | Indigo | `#6366F1` | Informational content |

### Form Inputs
| Element | Color | HEX | Description |
|---------|-------|-----|-------------|
| Input Background | Dark | `#1F2228` | Text fields, dropdowns |
| Input Border | Dark Gray | `#2C2F36` | Default border |
| Input Focus Border | Indigo | `#6366F1` | Focus state with glow |
| Input Text | Almost White | `#E4E7EB` | Input text color |
| Placeholder | Gray | `#6B7280` | Placeholder text |

## Component Styling

### Navigation & Sidebar
- **Background**: Dark gray (`#1A1D24`)
- **Links**: White text with violet hover effect
- **Active Links**: Indigo to violet gradient with glow effect
- **Borders**: Subtle dark gray dividers

### Buttons
- **Primary**: Indigo to violet gradient with shadow
- **Hover**: Enhanced gradient with increased glow
- **Outline**: Transparent with colored border
- **Success/Warning/Danger**: Solid colors with appropriate shading

### Cards
- **Background**: Dark gray (`#1A1D24`)
- **Border**: Subtle dark gray border
- **Border Radius**: 1rem for modern look
- **Shadow**: Soft black shadow with glow on hover
- **Header**: Semi-transparent background with bottom border

### Tables
- **Background**: Dark gray
- **Striped Rows**: Semi-transparent dark gray
- **Hover**: Lighter gray highlight
- **Headers**: Dark background with indigo bottom border

### Modals
- **Background**: Dark gray
- **Border**: Rounded corners (1rem)
- **Header/Footer**: Semi-transparent with borders
- **Close Button**: Inverted filter for visibility

### Forms
- **Controls**: Dark background with gray borders
- **Focus**: Indigo border with shadow glow
- **Labels**: White with medium weight
- **Checkboxes**: Indigo when checked

### Badges
- **Rounded**: 0.375rem border radius
- **Primary/Secondary**: Gradient backgrounds
- **Success/Warning/Danger**: Solid colors with appropriate contrast

### Alerts
- **Transparent Background**: 15% opacity of main color
- **Colored Border**: Full opacity border
- **Tinted Text**: Lighter shade of main color

### Tabs
- **Inactive**: Muted gray text
- **Active**: Violet text with bottom border
- **Hover**: Violet text color

## Special Features

### Gradients
Primary buttons and active elements use smooth gradients:
```css
background: linear-gradient(135deg, #6366F1, #8B5CF6);
```

### Glow Effects
Interactive elements feature subtle glow effects:
```css
box-shadow: 0 0 10px rgba(99, 102, 241, 0.4);
```

### Custom Scrollbar
Webkit browsers display a themed scrollbar:
- **Track**: Body background color
- **Thumb**: Indigo to violet gradient
- **Hover**: Enhanced gradient

### Transitions
All interactive elements have smooth 0.3s transitions for:
- Colors
- Shadows
- Transforms
- Background

## Bootstrap Integration

The theme is implemented using Bootstrap 5 CSS custom properties (`:root` variables), ensuring:

1. **Global Application**: Changes affect all Bootstrap components
2. **No Build Process**: Pure CSS override approach
3. **Easy Maintenance**: Update colors in one place
4. **Future-Proof**: Compatible with Bootstrap updates

## File Structure

```
/static/
  /css/
    custom-theme.css    # Main theme file
/templates/
  base.html             # Base template with theme link
```

## Implementation

The theme is automatically applied to all pages through the base template:

```html
<link href="/static/css/custom-theme.css" rel="stylesheet">
```

### Custom Properties Used

All colors are defined as CSS variables in `:root`:
- `--bs-body-bg`
- `--bs-body-color`
- `--bs-primary`
- `--bs-secondary`
- `--bs-success`
- `--bs-warning`
- `--bs-danger`
- And many more...

## Usage Examples

### Creating a Primary Button
```html
<button class="btn btn-primary">
    <i class="bi bi-plus-circle"></i> Action
</button>
```

### Creating a Card
```html
<div class="card">
    <div class="card-header">
        <h5>Card Title</h5>
    </div>
    <div class="card-body">
        <p>Card content with proper styling</p>
    </div>
</div>
```

### Creating an Alert
```html
<div class="alert alert-success">
    <i class="bi bi-check-circle"></i> Success message
</div>
```

## Browser Compatibility

The theme is tested and compatible with:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

### Custom Features Support
- **CSS Custom Properties**: All modern browsers
- **Gradients**: All modern browsers
- **Custom Scrollbar**: Webkit browsers only (Chrome, Safari, Edge)

## Customization

To modify the theme, edit `/static/css/custom-theme.css`:

1. **Change Colors**: Update `:root` variables at the top
2. **Modify Components**: Edit component-specific styles
3. **Add Effects**: Extend with new utility classes
4. **Adjust Transitions**: Change timing and easing functions

## Accessibility

The theme maintains high accessibility standards:

- **Contrast Ratio**: WCAG AA compliant for text
- **Focus States**: Clear indigo borders on interactive elements
- **Color Independence**: Information not conveyed by color alone
- **Screen Reader Friendly**: Semantic HTML maintained

## Performance

The theme is optimized for performance:

- **File Size**: ~13KB uncompressed CSS
- **No JavaScript**: Pure CSS implementation
- **CDN Assets**: Bootstrap and icons from CDN
- **Fast Loading**: Minimal HTTP requests

## Future Enhancements

Potential improvements to consider:

- [ ] Light mode variant (if needed)
- [ ] Additional color schemes
- [ ] Animation enhancements
- [ ] Custom icon set integration
- [ ] Dark mode toggle (if light mode added)

---

**Created by**: Christian Angermeier  
**Date**: October 2025  
**Contact**: ca@angermeier.net  
**Version**: 1.0.0
