from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import os
import logging
from dotenv import load_dotenv
import json
from groq import Groq

load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config.update({
    'SECRET_KEY': os.environ.get('SECRET_KEY'),
    'GROQ_API_KEY': os.environ.get('GROQ_API_KEY'),
    'UPLOAD_FOLDER': '/tmp',
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,
    'ALLOWED_EXTENSIONS': {'png', 'jpg', 'jpeg', 'gif', 'webp'},
    'TEMPLATES_AUTO_RELOAD': True,
})

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Groq client
client = Groq(api_key=app.config['GROQ_API_KEY'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def process_image(image_path):
    try:
        img = Image.open(image_path)
        img = img.convert('L')  # Grayscale
        img = ImageEnhance.Contrast(img).enhance(2.0)
        img = ImageEnhance.Brightness(img).enhance(1.5)
        img = img.filter(ImageFilter.MedianFilter())
        img = img.filter(ImageFilter.SHARPEN)
        return img
    except Exception as e:
        logger.error(f"Image processing failed: {e}")
        raise

def analyze_with_groq(text):
    if not text.strip():
        raise ValueError("No text provided for analysis")

    response_schema = {
        "type": "object",
        "properties": {
            "safety_rating": {
                "type": "object",
                "properties": {
                    "score": {
                        "type": "number",
                        "description": "Safety score from 0-10 based on ingredient analysis",
                        "minimum": 0,
                        "maximum": 10
                    },
                    "summary": {
                        "type": "string",
                        "description": "Detailed explanation of safety rating",
                        "maxLength": 600
                    }
                },
                "required": ["score", "summary"]
            },
            "quick_overview": {
                "type": "string",
                "description": "Comprehensive product analysis with key highlights",
                "maxLength": 1000
            },
            "diet_suitability": {
                "type": "object",
                "properties": {
                    "vegan": {"type": "string", "enum": ["Yes", "No", "Maybe"]},
                    "vegetarian": {"type": "string", "enum": ["Yes", "No", "Maybe"]},
                    "keto": {"type": "string", "enum": ["Yes", "No", "Maybe"]},
                    "diabetic_friendly": {"type": "string", "enum": ["Yes", "No", "Maybe"]},
                    "gluten_free": {"type": "string", "enum": ["Yes", "No", "Maybe"]},
                    "details": {
                        "type": "string",
                        "description": "Additional diet-specific notes",
                        "maxLength": 500
                    }
                },
                "required": ["vegan", "vegetarian", "keto", "diabetic_friendly", "gluten_free"]
            },
            "allergen_warning": {
                "type": "array",
                "description": "List of major allergens detected",
                "items": {
                    "type": "string",
                    "maxLength": 100
                }
            },
            "harmful_ingredients": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "maxLength": 100},
                        "concern": {"type": "string", "maxLength": 400},
                        "severity": {"type": "string", "enum": ["Low", "Medium", "High"]}
                    },
                    "required": ["name", "concern", "severity"]
                }
            },
            "ingredient_breakdown": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "ingredient": {"type": "string", "maxLength": 100},
                        "purpose": {"type": "string", "maxLength": 300},
                        "safety_note": {"type": "string", "maxLength": 200}
                    },
                    "required": ["ingredient", "purpose"]
                }
            },
            "clean_ingredient_list": {
                "type": "array",
                "description": "Simplified ingredient list for display",
                "items": {
                    "type": "string",
                    "maxLength": 100
                }
            },
            "recommendations": {
                "type": "object",
                "properties": {
                    "healthier_alternatives": {
                        "type": "string",
                        "description": "Suggested healthier product alternatives",
                        "maxLength": 500
                    },
                    "consumption_tips": {
                        "type": "string",
                        "description": "Recommendations for healthier consumption",
                        "maxLength": 500
                    }
                }
            },
            "nutritional_highlights": {
                "type": "string",
                "description": "Key nutritional facts and their implications",
                "maxLength": 800
            }
        },
        "required": [
            "safety_rating",
            "quick_overview",
            "diet_suitability",
            "allergen_warning",
            "harmful_ingredients",
            "ingredient_breakdown"
        ]
    }

    system_instruction = f"""
    You are a food ingredients expert. You will be given a text string containing food ingredients. Your task is to analyze these ingredients and provide a structured JSON response according to the following schema:

    {json.dumps(response_schema)}

    If the input is not food-related, return: {{"error": "Not food-related"}}.

    If you cannot confidently analyze the ingredients due to illegibility or lack of information, return: {{"error": "Unable to analyze"}}.

    Otherwise, *always* return a valid JSON object that conforms to the schema.
    """

    try:
        completion = client.chat.completions.create(
            model="qwen-2.5-32b",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": text}
            ],
            temperature=0.6,
            max_tokens=4096,
            top_p=0.95
        )
        
        response_text = completion.choices[0].message.content
        return json.loads(response_text)
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        raise RuntimeError("Failed to analyze ingredients with Groq")

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

        try:
            processed_img = process_image(filepath)
            # Use pytesseract to extract text directly from the processed PIL image
            extracted_text = pytesseract.image_to_string(processed_img, lang='eng')

            # Print the extracted text to the terminal
            print("Extracted Text from OCR:", extracted_text)
            # Alternatively, use logging:
            # logger.info(f"Extracted Text from OCR: {extracted_text}")

            if not extracted_text.strip():
                flash('No text could be extracted from the image. Please try another image.')
                return redirect(request.url)

            analysis_result = analyze_with_groq(extracted_text)

            # Store result in session and redirect
            session['analysis_result'] = analysis_result
            return redirect(url_for('show_result'))

        except Exception as e:
            logger.error(f"Error processing file: {e}")
            flash('Error processing your file. Please try again.')
            return redirect(request.url)
        finally:
            # Clean up the uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)

    return render_template('upload.html')

@app.route('/result')
def show_result():
    result = session.get('analysis_result')
    if not result:
        flash('No analysis result found. Please upload an image first.')
        return redirect(url_for('upload_file'))

    return render_template('result.html', result=result)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)