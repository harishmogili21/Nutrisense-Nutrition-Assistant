# 🚀 Quick Setup Guide

## Getting Your API Keys

### 1. Mistral AI API Key (Required for AI Nutrition Advice)

1. Go to [Mistral AI Console](https://console.mistral.ai/)
2. Sign up or log in to your account
3. Navigate to "API Keys" section
4. Create a new API key
5. Copy the key (starts with `mistral-`)

### 2. Exa API Key (Required for Restaurant Search)

1. Go to [Exa AI](https://exa.ai/)
2. Sign up or log in to your account
3. Navigate to "API Keys" section
4. Create a new API key
5. Copy the key (starts with `exa-`)

## Setting Up Environment Variables

### Option 1: Using .env file (Recommended)

1. Copy the template:
```bash
cp .env.template .env
```

2. Edit the `.env` file and add your API keys:
```bash
# Replace with your actual API keys
MISTRAL_API_KEY=mistral-your-actual-key-here
EXA_API_KEY=exa-your-actual-key-here
```

### Option 2: Set Environment Variables Directly

#### On Windows (PowerShell):
```powershell
$env:MISTRAL_API_KEY="mistral-your-actual-key-here"
$env:EXA_API_KEY="exa-your-actual-key-here"
```

#### On macOS/Linux:
```bash
export MISTRAL_API_KEY="mistral-your-actual-key-here"
export EXA_API_KEY="exa-your-actual-key-here"
```

## Running the App

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the app:
```bash
streamlit run app.py
```

3. Open your browser to `http://localhost:8501`

## Testing Your Setup

1. Go to "🎯 Set Preferences" and set up your profile
2. Go to "💬 Nutrition Chat" and ask: "What should I eat for breakfast?"
3. If you see personalized advice, your Mistral API key is working!
4. Try asking: "Find vegetarian restaurants in Mumbai" to test Exa API

## Troubleshooting

### 401 Error (Unauthorized)
- Check that your API keys are correct
- Ensure no extra spaces or characters
- Verify the keys start with the correct prefix

### 403 Error (Forbidden)
- Check your API quota/credits
- Verify your account is active

### No Response from AI
- Check your internet connection
- Verify the API keys are set correctly
- Try restarting the app

## Free API Credits

- **Mistral AI**: Usually provides free credits for new users
- **Exa AI**: Offers free tier with limited searches

## Need Help?

If you're still having issues:
1. Check the console/logs for detailed error messages
2. Verify your API keys are working in the respective dashboards
3. Try the app with just one API key at a time to isolate issues 