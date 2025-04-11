from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from PIL import Image, ImageEnhance, ImageFilter
import os
import logging
from dotenv import load_dotenv
import json
from groq import Groq
import requests
from io import BytesIO

load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config.update({
    'SECRET_KEY': os.environ.get('SECRET_KEY'),
    'GROQ_API_KEY': os.environ.get('GROQ_API_KEY'),
    'OCR_API_KEY': os.environ.get('OCR_API_KEY'),
    'OCR_API_URL': 'https://api.ocr.space/parse/image',
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,
    'ALLOWED_EXTENSIONS': {'png', 'jpg', 'jpeg', 'gif', 'webp'},
    'TEMPLATES_AUTO_RELOAD': True,
})

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Groq client
client = Groq(api_key=app.config['GROQ_API_KEY'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def enhance_image_for_ocr(img):
    """Enhance image quality for better OCR results"""
    try:
        logger.info("Enhancing image for OCR...")
        # Convert to grayscale
        img = img.convert('L')
        # Increase contrast
        img = ImageEnhance.Contrast(img).enhance(2.0)
        # Adjust brightness
        img = ImageEnhance.Brightness(img).enhance(1.2)
        # Apply filters
        img = img.filter(ImageFilter.MedianFilter(size=3))
        img = img.filter(ImageFilter.SHARPEN)
        return img
    except Exception as e:
        logger.error(f"Image enhancement failed: {e}")
        raise

def extract_text_with_ocr(image_data):
    """Extract text using OCR.space API with enhanced image processing"""
    try:
        logger.info("Starting OCR process...")
        
        # Enhance the image first
        img = Image.open(BytesIO(image_data))
        enhanced_img = enhance_image_for_ocr(img)
        
        # Save enhanced image to BytesIO
        img_byte_arr = BytesIO()
        enhanced_img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        logger.info("Sending request to OCR.space API...")
        response = requests.post(
            app.config['OCR_API_URL'],
            files={'file': ('enhanced.png', img_byte_arr, 'image/png')},
            data={
                'apikey': app.config['OCR_API_KEY'],
                'language': 'eng',
                'isOverlayRequired': False,
                'scale': True,
                'OCREngine': 2
            }
        )
        
        logger.info(f"OCR API response status: {response.status_code}")
        result = response.json()
        
        if response.status_code != 200 or not result.get('ParsedResults'):
            error = result.get('ErrorMessage', 'OCR failed')
            logger.error(f"OCR error: {error}")
            raise RuntimeError(f"OCR failed: {error}")
            
        extracted_text = result['ParsedResults'][0]['ParsedText']
        logger.info(f"Extracted Text: {extracted_text}")
        
        return extracted_text.strip()
    except Exception as e:
        logger.error(f"OCR process failed: {str(e)}")
        raise RuntimeError(f"Failed to extract text: {str(e)}")

def analyze_with_groq(text):
    """Analyze extracted text with Groq API"""
    if not text.strip():
        logger.error("Empty text provided for analysis")
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
            },
            "sugar_content": {
                "type": "object",
                "description": "Analysis of sugar content",
                "properties": {
                    "percentage": {
                        "type": "number",
                        "description": "Estimated sugar content as a percentage of the product (0-100)",
                        "minimum": 0,
                        "maximum": 100
                    },
                    "description": {
                        "type": "string",
                        "description": "2-line summary of sugar level (e.g., too high/low, safe to consume or not)",
                        "maxLength": 300
                    }
                },
                "required": ["percentage", "description"]
            }
        },
        "required": [
            "safety_rating",
            "quick_overview",
            "diet_suitability",
            "allergen_warning",
            "harmful_ingredients",
            "ingredient_breakdown",
            "sugar_content"
        ]
    }

    system_instruction = f"""
    You are a certified food safety and nutrition expert. You'll be given a text block extracted from a packaged food label. Your task is to analyze this text and return a JSON object conforming strictly to this schema:

    {json.dumps(response_schema, indent=2)}

    Important Guidelines:
    1. Return only a valid JSON object with no markdown or explanations.
    2. The sugar_content field must always be included, even if the sugar is not directly mentioned.
       a. If the percentage is not explicitly available in the text, you must intelligently estimate it based on ingredients and general product knowledge.
       b. If necessary, imagine what a similar product's sugar level would be or search from common nutritional datasets.
       c. Value must be a number (int or float), representing percentage out of 100.
       d. The description should summarize in 2 lines whether the sugar content is too high or too low, and whether it's recommended to consume or avoid.
    3. If this is not a food product, respond with: {{ "error": "Wrong image uploaded. Please upload a ingredients image" }}
    4. If unable to analyze for any reason, respond with: {{ "error": "Unable to analyze" }}
    5. Avoid assumptions outside common food safety knowledge. Be factual and concise.

    Provide only the final structured JSON object in your response.
    """

    try:
        logger.info("Sending request to Groq API...")
        logger.debug(f"Request text: {text[:200]}...")

        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": text}
            ],
            temperature=0.6,
            max_tokens=4096,
            top_p=0.95,
            response_format={"type": "json_object"}
        )

        response_text = completion.choices[0].message.content
        logger.info("Received response from Groq API")
        logger.debug(f"Raw response: {response_text}")

        try:
            response_data = json.loads(response_text)
            if not isinstance(response_data, dict):
                raise ValueError("Response is not a JSON object")
            return response_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content: {response_text}")
            raise RuntimeError("Invalid JSON response from API")
        except ValueError as e:
            logger.error(f"Invalid response format: {e}")
            logger.error(f"Response content: {response_text}")
            raise RuntimeError("Invalid response format from API")

    except Exception as e:
        logger.error(f"Groq API error: {str(e)}")
        raise RuntimeError(f"Failed to analyze ingredients: {str(e)}")


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
            try:
                logger.info(f"Processing file: {file.filename}")
                file_data = file.read()
                
                # OCR text extraction
                extracted_text = extract_text_with_ocr(file_data)
                logger.info(f"Extracted text length: {len(extracted_text)}")
                
                if not extracted_text.strip():
                    flash('No text could be extracted from the image. Please try another image.')
                    return redirect(request.url)
                
                # Groq analysis
                analysis_result = analyze_with_groq(extracted_text)
                if 'error' in analysis_result:
                    flash(f"Analysis error: {analysis_result['error']}")
                    return redirect(request.url)
                
                session['analysis_result'] = analysis_result
                return redirect(url_for('show_result'))
                
            except RuntimeError as e:
                flash(f"Processing failed: {str(e)}")
                return redirect(request.url)
            except Exception as e:
                logger.exception("Unexpected error during processing")
                flash('An unexpected error occurred. Please try again.')
                return redirect(request.url)
        else:
            flash('Allowed file types are png, jpg, jpeg, gif, webp')
            return redirect(request.url)

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