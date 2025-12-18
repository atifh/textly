from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from ai_service import AIService
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this')

# Initialize AI service
ai_service = AIService()

@app.route('/')
def index():
    """Main page with text correction form"""
    return render_template('index.html')

@app.route('/correct', methods=['POST'])
def correct_text():
    """Handle text correction request"""
    try:
        # Get form data
        text = request.form.get('text', '').strip()
        provider = request.form.get('provider', 'openai')
        
        if not text:
            return {'error': 'Please enter some text to correct.'}, 400
        
        # Get corrected text from AI service
        corrected_text = ai_service.fix_text(text, provider)

        return {
            'success': True,
            'original_text': text,
            'corrected_text': corrected_text,
            'provider': provider
        }
    
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return {'status': 'healthy', 'ai_providers': ai_service.get_available_providers()}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)