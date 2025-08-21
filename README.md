# Candidate Summary Generator

AI-powered candidate summary generator that creates polished, decision-ready briefs by combining data from RecruitCRM, AlphaRun interviews, and job descriptions. Built with React, Material UI, and Google Gemini AI.

## Features

- 🔥 **Firebase Integration** - Authentication, Storage, and optional Firestore
- 🚀 **Vite** - Lightning fast builds and HMR
- 🎨 **Material UI Theme** - Customized MUI theme for consistent styling
- 💅 **Tailwind CSS v4** - Utility classes for additional styling flexibility
- 📊 **ECharts** - Powerful charting library with geographic map support
- 🔒 **Authentication** - Email/password and Google sign-in with protected routes
- 📱 **Responsive Design** - Mobile-friendly interface using MUI and Tailwind
- 🧩 **Component Structure** - Organized component architecture
- 🎭 **Custom Theme** - Pre-configured MUI theme with consistent styling

## Technologies

| Category           | Technology                                  |
|--------------------|---------------------------------------------|
| Framework          | React 19                                    |
| Build Tool         | Vite 6.2+                                   |
| UI Library         | Material UI 5.15+                           |
| CSS Framework      | Tailwind CSS v4                             |
| Backend API        | Flask (Python)                              |
| AI Generation      | Google Gemini 1.5 Flash                    |
| Authentication     | Firebase Authentication                      |
| Database (Optional)| Firestore                                   |
| File Storage       | Firebase Storage                            |
| Routing            | React Router v7                             |
| Charts             | ECharts                                     |

## Quick Start

### Frontend Setup
1. Clone this repository
2. Install dependencies:
   ```bash
   npm install
   ```
3. Configure environment:
   ```bash
   cp .env.example .env
   ```
4. Update Firebase configuration in `src/firebase.js`
5. Start development server:
   ```bash
   npm run dev
   ```

### Backend Setup
1. Install Python dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
2. Configure API keys:
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your API keys
   ```
3. Start backend server:
   ```bash
   python app.py
   ```

## Usage

1. **Navigate to Summary Generator**: Go to `/summary` route
2. **Input Data**:
   - Paste RecruitCRM candidate URL
   - Paste RecruitCRM job URL  
   - Enter AlphaRun interview ID
   - Add any additional context (optional)
3. **Generate**: Click "Generate Summary" to create AI-powered brief
4. **Review**: Preview the formatted HTML summary
5. **Regenerate**: Add more context and regenerate if needed
6. **Push**: Send directly to RecruitCRM candidate record

## API Integration

The app integrates with:
- **RecruitCRM API**: Fetches candidate and job data
- **AlphaRun API**: Retrieves interview assessments  
- **Google Gemini**: Generates structured HTML summaries

See `backend/README.md` for detailed API documentation.

## Project Structure

```
project-root/
├── src/
│   ├── components/
│   │   ├── auth/
│   │   │   ├── AuthContainer.jsx   # Auth wrapper component
│   │   │   ├── LoginComponent.jsx  # Login form
│   │   │   ├── RegisterComponent.jsx # Registration form
│   │   │   └── ProtectedRoute.jsx  # Route protection component
│   │   ├── common/
│   │   │   └── LinkBehaviour.jsx   # Custom link for MUI integration
│   │   ├── Chart.jsx               # ECharts component
│   │   └── Dashboard.jsx           # Main app dashboard
│   ├── contexts/
│   │   └── AuthContext.jsx         # Authentication context
│   ├── services/
│   │   └── authService.js          # Auth helper functions
│   ├── App.jsx                     # Main application component
│   ├── main.jsx                    # Application entry point
│   ├── firebase.js                 # Firebase configuration
│   ├── theme.js                    # MUI theme configuration
│   └── index.css                   # Global styles with Tailwind
├── public/
│   └── favicon.ico                 # App favicon
├── index.html                      # HTML template
├── package.json                    # Dependencies and scripts
├── tailwind.config.js              # Tailwind configuration
├── vite.config.js                  # Vite configuration
├── firebase.json                   # Firebase configuration
└── .firebaserc                     # Firebase project settings
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally
- `npm run lint` - Run ESLint to check code

## Customization

### Theme Customization

You can customize the theme by modifying `src/theme.js`. The theme is built on Material UI's theming system, allowing you to:

- Change color palettes
- Adjust typography settings
- Modify component styles
- Update spacing and sizing

### Styling Approach

This template uses a hybrid approach to styling:

1. **MUI Components**: Styled through the theme system
2. **Tailwind CSS**: For utility-based styling needs
3. **CSS Modules**: Available for component-specific styles

### Authentication

The template includes both email/password and Google authentication. To customize:
- Edit `src/components/auth/` components
- Modify `src/services/authService.js` to add or remove auth providers

### Charts

ECharts is included for data visualization. Example usage is in `src/components/Chart.jsx`.
- Geographic maps support is available for visualizing global data
- Customize chart options in the Chart component

## Deployment

1. Install Firebase CLI: `npm install -g firebase-tools`
2. Login to Firebase: `firebase login`
3. Initialize Firebase: `firebase init` (select Hosting)
4. Build the project: `npm run build`
5. Deploy to Firebase: `firebase deploy`

## Security Considerations

- Always implement proper security rules in Firebase
- For Firestore, use rules based on user authentication
- For Storage, restrict access to authenticated users
- Consider adding Firebase Functions for server-side logic

## License

This template is MIT licensed.bash
npm install
   ```
3. Update Firebase configuration in `src/firebase.js` with your Firebase project details
4. Start the development server:
   ```bash
   npm run dev
   ```

## Firebase Setup

1. Create a Firebase project at [firebase.google.com](https://firebase.google.com)
2. Navigate to the Console and click "Add project"
3. Follow the setup wizard to configure your project
4. Once created, click on "Web" (</>) to add a web app to your project
5. Register your app with a nickname (e.g., "vite-template")
6. Copy the Firebase configuration object provided

### Setting up Authentication:

1. In the Firebase Console, navigate to "Authentication" > "Sign-in method"
2. Enable Email/Password and Google authentication providers
3. For Google, configure the OAuth consent screen if required

### Setting up Firestore (Optional):

1. Go to "Firestore Database" in the Firebase Console
2. Click "Create database"
3. Choose between production or test mode (test mode for development)
4. Select a location for your database

### Setting up Storage:

1. Go to "Storage" in the Firebase Console
2. Click "Get started"
3. Configure storage rules for your application

### Update Configuration

Replace the placeholder configuration in `src/firebase.js` with your actual Firebase config:

```javascript
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT_ID.appspot.com",
  messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
  appId: "YOUR_APP_ID"
};
```

## Theme Usage

This template comes with a pre-configured Material UI theme based on the Outstaffer design system. The theme includes:

- **Color System**: A comprehensive color palette with primary, secondary, and UI colors
- **Typography**: Font families, sizes, weights, and line heights
- **Spacing**: Consistent spacing scale
- **Component Styling**: Pre-styled MUI components
- **Responsive Design**: Mobile-first approach

### Using the Theme

The theme is automatically applied to all Material UI components. To use theme values in your components:

```jsx
import { useTheme } from '@mui/material/styles';
import { CustomColors } from '../theme';

function MyComponent() {
  const theme = useTheme();
  
  return (
    <div style={{ 
      backgroundColor: theme.palette.background.default,
      color: CustomColors.MidnightBlue,
      padding: theme.spacing(2)
    }}>
      Themed content
    </div>
  );
}
```

### Theme Constants

The theme exports several constants that can be imported and used:

```jsx
import { 
  CustomColors,
  FontSize, 
  Spacing, 
  BorderRadius 
} from '../theme';

// Usage example
<div style={{ 
  fontSize: FontSize.Large,
  padding: Spacing.Medium,
  borderRadius: BorderRadius.Rounded
}}>
  Content with theme constants
</div>
```