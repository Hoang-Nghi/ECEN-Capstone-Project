# Personalized Financial Advisor App for Students

**ECEN 403/404 Capstone Project - Team 27**  
Texas A&M University

## Table of Contents
- [Project Overview](#project-overview)
- [Repository Structure](#repository-structure)
- [Frontend Structure](#frontend-structure)
- [Backend Structure](#backend-structure)
- [How to Use This Code](#how-to-use-this-code)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Design Philosophy](#design-philosophy)

## Project Overview

The Personalized Financial Advisor App for Students is a gamified financial literacy mobile application designed to teach money management through positive reinforcement. The app connects to users' real bank accounts via Plaid API and provides educational minigames and analytics to help students develop better financial habits.

**Key Innovation**: Unlike traditional budgeting apps that penalize users for mistakes or insufficient data, Student Savings uses positive reinforcement to reward good financial behaviors and maintain educational value even with limited transaction history.

## Repository Structure

This repository contains both the **frontend** (React Native/Expo mobile app) and **backend** (Python Flask API) components of the Student Savings application.
```
ECEN-Capstone-Project/
│
├── app/                              # Frontend - React Native/Expo Router app
│   ├── (tabs)/                       # Tab-based navigation screens
│   │   ├── games/                    # Minigame screens
│   │   │   ├── _layout.tsx           # Games navigation layout
│   │   │   ├── index.tsx             # Games home/selection
│   │   │   ├── connections.tsx       # [Game screen]
│   │   │   ├── spend-detective.tsx   # Spend Detective game
│   │   │   ├── trivia.tsx            # Smart Saver Quiz
│   │   │   ├── trivia-test.tsx       # Quiz testing interface
│   │   │   └── xp-context.tsx        # XP state management
│   │   ├── _layout.tsx               # Main tab layout
│   │   ├── home.tsx                  # Dashboard/home screen
│   │   ├── analysis.tsx              # Analytics screen
│   │   ├── education.tsx             # Educational content
│   │   ├── connect-bank.tsx          # Plaid bank connection
│   │   ├── settings.tsx              # User settings
│   │   ├── loadingscreen.tsx         # Loading states
│   │   └── api-debug.tsx             # API debugging interface
│   ├── assets/                       # Static assets
│   │   ├── logo.png                  # App logo
│   │   ├── loading.gif               # Loading animation
│   │   ├── teacher-popup.png         # Educational popup
│   │   └── placeholder-logo.jpg      # Placeholder images
│   ├── hooks/                        # Custom React hooks
│   │   ├── useAuth.tsx               # Authentication hook
│   │   ├── graph.tsx                 # Chart/graph hooks
│   │   ├── piechart.tsx              # Pie chart visualization
│   │   ├── spending.tsx              # Spending data hooks
│   │   ├── purchases.tsx             # Transaction hooks
│   │   ├── notifications.tsx         # Notification management
│   │   ├── educationlist.tsx         # Educational content
│   │   └── logout.tsx                # Logout functionality
│   ├── services/                     # API service layer
│   │   └── plaidApi.tsx              # Plaid API integration
│   ├── utils/                        # Utility functions
│   │   ├── firebaseConfig.tsx        # Firebase configuration
│   │   ├── getIdToken.tsx            # Auth token retrieval
│   │   └── _layout.tsx               # Utility layout helpers
│   ├── index.tsx                     # App entry point
│   ├── signin.tsx                    # Sign in screen
│   ├── signup.tsx                    # Sign up screen
│   ├── verify-email.tsx              # Email verification
│   └── +not-found.tsx                # 404 error screen
│
├── Backend/                          # Python Flask API
│   ├── firebase/                     # Firebase integration
│   │   ├── credentials/              # Service account keys (gitignored)
│   │   ├── rules/                    # Firestore security rules
│   │   ├── schema/                   # Database schema definitions
│   │   ├── seed/                     # Seed data scripts
│   │   ├── tools/                    # Firebase utility scripts
│   │   ├── __init__.py
│   │   └── service.py                # Firebase service layer
│   ├── plaid_integration/            # Plaid API integration
│   │   ├── __init__.py
│   │   ├── client.py                 # Plaid client configuration
│   │   └── plaid_recovery.txt        # Recovery documentation
│   ├── routes/                       # API route handlers
│   │   ├── __init__.py
│   │   ├── analytics.py              # Analytics endpoints
│   │   ├── auth.py                   # Authentication routes
│   │   ├── plaid.py                  # Plaid connection routes
│   │   ├── plaid_webhook.py          # Plaid webhook handler
│   │   └── ml.py                     # Machine learning endpoints
│   ├── services/                     # Business logic services
│   │   ├── minigame_service/         # Minigame logic
│   │   │   ├── __init__.py
│   │   │   ├── smart_saver_quiz.py   # Quiz game logic
│   │   │   ├── spend_detective.py    # Detective game logic
│   │   │   ├── financial_categories.py # Categories game logic
│   │   │   ├── progression.py        # XP and rank system
│   │   │   ├── routes.py             # Minigame API routes
│   │   │   └── utils.py              # Game utilities
│   │   ├── __init__.py
│   │   ├── analytics.py              # Analytics service
│   │   ├── firebase.py               # Firebase service
│   │   └── plaid_store.py            # Secure token storage
│   ├── __pycache__/                  # Python cache (gitignored)
│   ├── .pytest_cache/                # Pytest cache (gitignored)
│   ├── .vscode/                      # VS Code settings
│   ├── requirements.txt              # Python dependencies
│   └── [other configuration files]   # .env, Dockerfile, etc.
│
└── README.md                         # This file
```

## Frontend Structure (Expo Router + TypeScript)

The frontend uses **Expo Router** with TypeScript for file-based routing and type safety.

### Key Directories:

**`/app/(tabs)/`** - Tab Navigation Screens
- Uses Expo Router's tab layout pattern
- Main tabs: Home, Games, Analysis, Education, Settings
- Each tab has its own screen and nested routes

**`/app/(tabs)/games/`** - Minigame Screens
- `index.tsx` - Game selection interface
- `trivia.tsx` - Smart Saver Quiz (100+ questions)
- `spend-detective.tsx` - Spending anomaly detection
- `connections.tsx` - [Connection-based game]
- `xp-context.tsx` - Global XP state management

**`/app/hooks/`** - Custom React Hooks
- `useAuth.tsx` - Firebase authentication
- `graph.tsx` & `piechart.tsx` - Data visualization
- `spending.tsx` & `purchases.tsx` - Transaction data
- `notifications.tsx` - Push notification management
- `educationlist.tsx` - Educational content management

**`/app/services/`** - API Integration
- `plaidApi.tsx` - Plaid API client with async methods

**`/app/utils/`** - Utilities
- `firebaseConfig.tsx` - Firebase SDK initialization
- `getIdToken.tsx` - Authentication token management

**Authentication Screens:**
- `signin.tsx` - User login
- `signup.tsx` - New user registration
- `verify-email.tsx` - Email verification flow

## Backend Structure (Flask + Modular Services)

The backend follows a modular architecture with clear separation of concerns.

### Key Directories:

**`/Backend/firebase/`** - Firebase Integration
- `service.py` - Main Firebase service class
- `credentials/` - Service account keys (not committed)
- `schema/` - Firestore schema definitions
- `seed/` - Database seeding scripts
- `tools/` - Firebase CLI utilities

**`/Backend/plaid_integration/`** - Plaid API
- `client.py` - Plaid client configuration and initialization
- Handles OAuth flow and token exchange
- Manages sandbox vs. production environments

**`/Backend/routes/`** - API Endpoints
- `auth.py` - Authentication and user management
- `plaid.py` - Bank connection and transaction sync
- `plaid_webhook.py` - Real-time Plaid webhooks
- `analytics.py` - Spending analytics and trends
- `ml.py` - Machine learning model endpoints

**`/Backend/services/minigame_service/`** - Game Logic
- `smart_saver_quiz.py` - Financial literacy quiz engine
- `spend_detective.py` - Anomaly detection algorithms
- `financial_categories.py` - Transaction categorization
- `progression.py` - Unified XP and ranking system
- `routes.py` - Minigame-specific API endpoints
- `utils.py` - Shared game utilities

**`/Backend/services/`** - Core Services
- `analytics.py` - Transaction aggregation and analysis
- `firebase.py` - Firestore database operations
- `plaid_store.py` - Encrypted token storage (Fernet/AES)

**`requirements.txt`** - Python Dependencies
```
Flask==3.0.0              # Web framework
flask-cors==4.0.0         # CORS support for mobile app
firebase-admin==6.3.0     # Firebase SDK
python-dotenv==1.0.0      # Environment variable management
plaid-python==18.0.0      # Plaid API client
requests==2.31.0          # HTTP client
cryptography==41.0.7      # Token encryption
gunicorn==21.2.0          # Production WSGI server
```

## How to Use This Code

### Prerequisites
- Node.js 16+ and npm/yarn (for frontend)
- Python 3.9+ (for backend)
- Expo CLI (`npm install -g expo-cli`)
- Firebase project with Firestore enabled
- Plaid developer account (free sandbox)
- Google Cloud Platform account (for deployment)

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure Firebase**
   - Create a Firebase project at https://console.firebase.google.com
   - Enable Authentication (Email/Password and Google Sign-In)
   - Enable Firestore Database
   - Download `google-services.json` (Android) and `GoogleService-Info.plist` (iOS)
   - Add configuration to `src/config/firebase.js`

4. **Start the development server**
   ```bash
   npm start
   # or
   expo start
   ```

5. **Run on device/simulator**
   - Press `a` for Android emulator
   - Press `i` for iOS simulator
   - Scan QR code with Expo Go app on physical device

### Backend Setup

1. **Navigate to backend directory (repository root)**
   ```bash
   cd ..  # If in frontend directory
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Activate (Windows)
   venv\Scripts\activate
   
   # Activate (Mac/Linux)
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   
   Create a `.env` file in the root directory:
   ```env
   # Firebase
   FIREBASE_CREDENTIALS_PATH=path/to/serviceAccountKey.json
   
   # Plaid
   PLAID_CLIENT_ID=your_plaid_client_id
   PLAID_SECRET=your_plaid_secret_sandbox
   PLAID_ENV=sandbox  # or 'development' or 'production'
   
   # Encryption
   ENCRYPTION_KEY=your_generated_fernet_key
   
   # Google Cloud
   GOOGLE_CLOUD_PROJECT=your-project-id
   ```

5. **Generate encryption key**
   ```python
   from cryptography.fernet import Fernet
   print(Fernet.generate_key().decode())
   ```

6. **Run the development server**
   ```bash
   python app.py
   ```
   
   Server runs on `http://localhost:5000`

7. **Test API endpoints**
   ```bash
   # Health check
   curl http://localhost:5000/api/health
   
   # Get quiz questions (requires auth)
   curl -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
        http://localhost:5000/api/games/quiz
   ```

### Database Setup

**Firestore Collections:**

The backend automatically creates these collections:
- `users` - User profiles and XP data
- `transactions` - Bank transaction data
- `plaid_tokens` - Encrypted Plaid access tokens (per user)
- `games` - Game history and results (subcollections per user)
  - `quiz_history` - Quiz game results
  - `detective_history` - Detective game results
  - `categories_history` - Categories game results

**Initial Data:**
- Game questions are stored in code (not database)
- No seed data required
- User data is created on first login

### Deployment

**Backend to Google Cloud Run:**
```bash
# Build and deploy
gcloud run deploy student-savings-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

**Frontend to Expo:**
```bash
cd frontend
expo build:android  # For Android
expo build:ios      # For iOS
```

## Features

### Educational Minigames

**Smart Saver Quiz**
- 100+ financial literacy questions
- 5 difficulty levels (Beginner to Expert)
- Topics: budgeting, saving, investing, credit, taxes
- Adaptive difficulty based on performance
- 10-50 XP per question

**Spend Detective**
- Identify spending anomalies in transaction sets
- Statistical anomaly detection using Z-scores and IQR
- Real-world spending scenarios
- Weekly play restriction (encourages consistency)
- 20-100 XP per game

**Financial Categories**
- Learn to categorize transactions correctly
- Based on Plaid's Personal Finance Categories
- Reduced "Other" category from 50% to 15%
- Real transaction data from user's bank account
- 15-30 XP per correct categorization

### Analytics Dashboard

- **Spending Trends**: Time-series visualization of spending patterns
- **Category Breakdown**: Pie chart of spending by category
- **Budget Progress**: Comparison to previous month's spending
- **Transaction History**: Searchable and filterable transaction list
- **Anomaly Detection**: Flags for unusual spending patterns

### Gamification System

- **Unified XP**: Single XP pool across all minigames
- **Streak Tracking**: Consecutive days playing games
- **Weekly Restrictions**: Detective game limited to once per week
- **Detailed History**: Complete game history with timestamps

## Tech Stack

### Frontend
- **Framework**: React Native 0.71 with Expo SDK 48
- **Navigation**: React Navigation 6
- **State Management**: React Context API
- **UI Library**: React Native Paper
- **Charts**: react-native-chart-kit
- **Authentication**: Firebase Authentication SDK
- **HTTP Client**: Axios

### Backend
- **Framework**: Flask 3.0
- **Database**: Google Cloud Firestore (NoSQL)
- **Authentication**: Firebase Admin SDK
- **Banking API**: Plaid API v2022-09-15
- **Encryption**: Cryptography (Fernet/AES)
- **Deployment**: Google Cloud Run (containerized)
- **Server**: Gunicorn (production)

### DevOps & Tools
- **Version Control**: Git & GitHub
- **CI/CD**: Google Cloud Build
- **Monitoring**: Google Cloud Logging
- **API Testing**: Postman
- **Mobile Testing**: Expo Go

## Design Philosophy

The app follows a **positive reinforcement** approach:

1. **Reward Good Behaviors**: XP awarded for financial literacy learning
2. **No Penalties**: Incorrect answers don't reduce XP or rank
3. **Educational Focus**: Games teach real financial concepts
4. **Graceful Degradation**: Limited transaction data still provides full educational value
5. **Privacy First**: All data encrypted, no third-party data sharing

**Key Principle**: When users have limited spending data, the system awards full XP rather than treating insufficient data as a failure. This maintains motivation and educational value for all users regardless of their transaction history.

## Team Members

- **Student Developer**: Camille Embree, Hoang-Nghi Nguyen
- **Course**: ECEN 403/404 Capstone Design
- **Institution**: Texas A&M University
- **Team**: Team 27

## Instructors & Teaching Assistants

This project is supervised by:
- **Instructors**: Prof. Kevin Nowka, Prof. John Lusher II, P.E., Prof. Wonhyeok Jang, Prof. Prasad Enjeti, Prof. Stavros Kalafatis 
- **Teaching Assistant**: Sabyasachi Gupta

## License

This project is developed for educational purposes as part of the ECEN 403/404 Capstone course at Texas A&M University.

## Additional Resources

- [Plaid API Documentation](https://plaid.com/docs/)
- [Firebase Documentation](https://firebase.google.com/docs)
- [React Native Documentation](https://reactnative.dev/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
