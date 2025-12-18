# Textly

AI-powered text correction that preserves your unique writing style. A sleek Flask web application that fixes grammar and improves clarity while maintaining your original tone. Supports both OpenAI GPT and Anthropic Claude.

## Features

- 🔧 Grammar and spelling correction
- 🎯 Maintains original tone and style
- 🔄 Switch between OpenAI GPT and Anthropic Claude
- 📱 Responsive web interface
- 📋 Copy corrected text to clipboard
- 📊 Side-by-side comparison of original vs corrected text

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API Keys**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` file and add your API keys:
   - Get OpenAI API key from: https://platform.openai.com/api-keys
   - Get Anthropic API key from: https://console.anthropic.com/
   
   You need at least one API key for the app to work.

3. **Run the Application**
   ```bash
   python app.py
   ```
   
   The app will be available at: http://localhost:5000

## Usage

1. Open the web interface
2. Enter or paste your text in the textarea
3. Choose your preferred AI provider (OpenAI GPT or Anthropic Claude)
4. Click "Fix Grammar" to get the corrected version
5. Copy the result or compare with the original text

## Project Structure

```
textly/
├── app.py                  # Main Flask application
├── ai_service.py          # AI service layer (OpenAI/Claude)
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── templates/
│   └── index.html        # Main web interface
└── static/
    └── css/
        └── style.css     # Styles and responsive design
```

## Health Check

Visit `/health` endpoint to check the status and available AI providers.

## Notes

- The app preserves the original tone and writing style
- Only grammar and spelling errors are corrected
- Both AI providers use low temperature (0.1) for consistent results
- Responsive design works on mobile and desktop