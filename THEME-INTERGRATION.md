# MUI Theme Integration Guide

This document explains how the Material UI theme has been integrated into the Firebase Vite template.

## What Changed

1. **Added Dependencies**:
    - Material UI core components
    - Emotion (MUI styling engine)

2. **Theme Configuration**:
    - Converted the TypeScript theme to JavaScript
    - Set up theme provider in App.jsx
    - Added font imports in index.css
    - Created LinkBehavior component for router integration

3. **Component Updates**:
    - Dashboard: Converted to use MUI components
    - AuthContainer: Updated with MUI form controls
    - Added ThemeProvider to App.jsx

## Using the Theme

### Colors

The theme provides a set of colors through the `CustomColors` object:

```jsx
import { CustomColors } from '../theme';

// In your component
<div style={{ backgroundColor: CustomColors.MidnightBlue }}>
  Content
</div>
```

### Typography

Use MUI Typography component with theme variants:

```jsx
import { Typography } from '@mui/material';

// Standard variants
<Typography variant="h3">Heading</Typography>
<Typography variant="body1">Regular text</Typography>

// Custom variants added in the theme
<Typography variant="body">Body text</Typography>
<Typography variant="bodySmall">Small body text</Typography>
<Typography variant="h7">Custom header size</Typography>
```

### Spacing

Use the spacing constants or theme.spacing():

```jsx
import { Spacing } from '../theme';
import { Box, useTheme } from '@mui/material';

function MyComponent() {
  const theme = useTheme();
  
  return (
    <>
      {/* Using constant */}
      <div style={{ margin: Spacing.Medium }}>Content</div>
      
      {/* Using theme.spacing */}
      <Box sx={{ margin: theme.spacing(2) }}>Content</Box>
    </>
  );
}
```

### Component Styling

Components are pre-styled in the theme. You can customize further with the `sx` prop:

```jsx
import { Button, TextField } from '@mui/material';

<Button 
  variant="contained" 
  color="primary" 
  sx={{ 
    borderRadius: 2,
    textTransform: 'uppercase'
  }}
>
  Custom Button
</Button>

<TextField
  label="Custom Input"
  variant="outlined"
  sx={{ 
    '& .MuiOutlinedInput-root': {
      borderRadius: 8
    }
  }}
/>
```

## Theme Extensions

The theme extends MUI's default theme with:

1. **Custom Typography Variants**:
    - body, bodySmall, bodyXSmall, bodyLarge, bodyXLarge, h7, caption2

2. **Custom Palette Colors**:
    - default, disabled, border, backgroundSecondary, backgroundGrey

3. **Custom Component Styles**:
    - MuiButton, MuiCard, MuiAlert, MuiChip, etc.

## Mixed Styling Approach

This template uses a mixed approach to styling:

1. **MUI Components & Theme**: Primary UI elements
2. **Tailwind CSS**: Utility classes for additional styling needs
3. **Custom CSS**: Available when needed through index.css

## Fonts

The theme uses:
- **Inter** as the primary font
- **Roboto** as the secondary font

These are loaded through Google Fonts in index.css.

## Customization

To customize the theme further:

1. Edit `src/theme.js` to change colors, typography, or component styles
2. Add new custom components in the `src/components/common` directory
3. Extend the theme with additional constants or helper functions as needed