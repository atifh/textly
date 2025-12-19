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

@app.route('/process', methods=['POST'])
def process_text():
    """Handle text processing request"""
    try:
        # Get form data
        text = request.form.get('text', '').strip()
        provider = request.form.get('provider', 'openai')
        mode = request.form.get('mode', 'fix')
        
        if not text:
            return {'error': 'Please enter some text to process.'}, 400
        
        # Process text using AI service
        processed_text = ai_service.process_text(text, mode, provider)

        # Determine the appropriate label based on mode
        mode_labels = {
            'fix': 'Corrected Text',
            'rewrite_formal': 'Formal Version',
            'rewrite_casual': 'Casual Version', 
            'summarize': 'Summary',
            'expand': 'Expanded Text',
            'sentiment': 'Sentiment Analysis'
        }

        return {
            'success': True,
            'original_text': text,
            'processed_text': processed_text,
            'provider': provider,
            'mode': mode,
            'mode_label': mode_labels.get(mode, 'Processed Text')
        }
    
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/correct', methods=['POST'])
def correct_text():
    """Handle text correction request (backward compatibility)"""
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
            'processed_text': corrected_text,  # For compatibility
            'provider': provider,
            'mode': 'fix',
            'mode_label': 'Corrected Text'
        }
    
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return {'status': 'healthy', 'ai_providers': ai_service.get_available_providers()}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)