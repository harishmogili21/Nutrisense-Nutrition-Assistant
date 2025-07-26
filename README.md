# Nutrisense Nutrition Assistant

A comprehensive AI-powered nutrition and fitness assistant built with Streamlit, featuring personalized advice, restaurant search, food logging, and workout plans.

## 🌟 Features

### 🤖 AI-Powered Nutrition Advice
- **Personalized Recommendations**: Get nutrition advice tailored to your specific profile
- **Dietary Restrictions Support**: Handles vegetarian, vegan, gluten-free, and other dietary needs
- **Health Goals Integration**: Advice aligned with weight loss, muscle gain, or general wellness
- **Real-time AI Responses**: Powered by Mistral Agents API for intelligent, contextual advice

### 🍽️ Smart Restaurant Search
- **Location-based Search**: Find restaurants in your area
- **Dietary Preference Filtering**: Results filtered by your dietary restrictions
- **AI-Powered Recommendations**: Get personalized restaurant suggestions
- **Real-time Data**: Uses Exa API for current restaurant information

### 🍎 Advanced Food Logging
- **Natural Language Logging**: Log food directly in chat using natural language
  - Try: "I ate an apple", "Had grilled chicken for lunch", "Just drank a coffee"
- **AI Calorie Estimation**: Automatic calorie estimation for common foods
- **Daily Progress Tracking**: Monitor your progress toward calorie goals
- **Macro Tracking**: Optional protein, carbs, and fat logging
- **Meal Type Categorization**: Breakfast, lunch, dinner, and snack tracking

### 💪 Personalized Workout Plans
- **AI-Generated Plans**: Custom workout routines based on your fitness level
- **Nutrition Integration**: Pre and post-workout nutrition advice
- **Progression Tracking**: Structured plans for continuous improvement
- **Recovery Guidance**: Rest day activities and recovery tips

### 🎯 User Profile Management
- **Comprehensive Profiles**: Age, weight, height, activity level, and goals
- **Dietary Preferences**: Allergies, restrictions, and food preferences
- **Health Goals**: Weight loss, muscle gain, maintenance, or specific health targets
- **Persistent Storage**: All preferences saved in local SQLite database

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Mistral AI API key
- Exa API key (for restaurant search)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd nutrisense_nutrition_preferences_secure
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.template .env
   # Edit .env with your API keys
   ```

4. **Run the application**
   ```bash
   streamlit run app.py
   ```

## 📋 API Keys Setup

### Required API Keys

1. **Mistral AI API Key**
   - Get from: https://console.mistral.ai/api-keys
   - Used for: AI nutrition advice, food logging, workout plans
   - Format: 32-character alphanumeric string

2. **Exa API Key**
   - Get from: https://exa.ai/
   - Used for: Restaurant search functionality
   - Format: UUID format

### Environment Variables
Create a `.env` file in the project root:
```env
# Required API Keys
MISTRAL_API_KEY=your_mistral_api_key_here
EXA_API_KEY=your_exa_api_key_here

# Optional Configuration
DATABASE_URL=nutrisense_data.db
LOG_LEVEL=INFO
```

## 🎯 How to Use

### 1. Set Your Preferences
1. Go to "🎯 Set Preferences" in the sidebar
2. Enter your User ID (this links all your data)
3. Fill in your profile information:
   - Basic info (age, gender, weight, height)
   - Activity level and health goals
   - Dietary restrictions and allergies
4. Click "Save Preferences"

### 2. Get AI Nutrition Advice
1. Go to "💬 Nutrition Chat"
2. Enter the same User ID as in preferences
3. Ask nutrition questions like:
   - "What should I eat for breakfast?"
   - "How many calories should I eat to lose weight?"
   - "What are good protein sources for vegetarians?"

### 3. Food Logging
**Option A: Chat-based Logging (Recommended)**
- In the chat, simply say what you ate:
  - "I ate an apple"
  - "Had grilled chicken breast for lunch"
  - "Just drank a coffee"
  - "Ate oatmeal with berries for breakfast"

**Option B: Dedicated Food Logger**
1. Go to "🍎 Food Logger" in the sidebar
2. Fill in the food details manually
3. Click "Log Food"

### 4. Restaurant Search
1. In the chat, ask for restaurants:
   - "Find restaurants in Mumbai"
   - "Show me vegetarian restaurants in Delhi"
   - "Best healthy restaurants near me"

### 5. Workout Plans
1. In the chat, ask for workout advice:
   - "Create a workout plan for weight loss"
   - "Give me a strength training routine"
   - "How should I exercise for muscle gain?"

## 🏗️ Architecture

### Core Components
- **Streamlit Frontend**: Modern, responsive web interface
- **Mistral Agents API**: Advanced AI for nutrition advice and food logging
- **Exa API**: Real-time restaurant search and recommendations
- **SQLite Database**: User preferences and food logs storage
- **Session Management**: Persistent user state across interactions

### Key Features
- **Natural Language Processing**: Understands food logging in plain English
- **Personalized AI Responses**: Context-aware advice based on user profile
- **Real-time Data**: Live restaurant information and recommendations
- **Local Data Storage**: Privacy-focused with local SQLite database
- **Responsive Design**: Works on desktop and mobile devices

## 🔧 Troubleshooting

### Common Issues

1. **API Key Errors (401/403)**
   - Verify your API keys are correct
   - Check that keys are properly set in `.env` file
   - Ensure Mistral API key is 32-character alphanumeric
   - Test with: `python test_mistral.py`

2. **Environment Variables Not Loading**
   - Ensure `.env` file is in the same directory as `app.py`
   - Check file permissions
   - Test with: `python debug_env.py`

3. **Food Logging Not Working**
   - Make sure you've set a User ID in preferences
   - Use the same User ID in chat and food logger
   - Try natural language: "I ate [food name]"

### Testing
Run these test scripts to verify functionality:
```bash
python test_mistral.py          # Test Mistral API
python debug_env.py             # Test environment variables
python test_food_logging.py     # Test food logging
```

## 📊 Database Schema

### Tables
- **user_preferences**: User profile and dietary preferences
- **nutrition_logs**: Food intake tracking

### Key Fields
- **user_id**: Unique identifier linking all user data
- **food_item**: Name of the food consumed
- **calories**: Estimated calorie content
- **timestamp**: When the food was logged

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Mistral AI**: For providing the AI capabilities
- **Exa**: For restaurant search functionality
- **Streamlit**: For the web framework
- **SQLite**: For local data storage 