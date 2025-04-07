from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract as tess
import os
import logging
from google import genai
from google.genai import types
import json
from dotenv import load_dotenv
load_dotenv()


# Initialize Flask app
app = Flask(__name__)

app.config.update({
    'SECRET_KEY' : os.environ.get('SECRET_KEY'),
    'GEMINI_API_KEY': os.environ.get('GEMINI_API_KEY'),
    'UPLOAD_FOLDER': '/tmp',
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,
    'ALLOWED_EXTENSIONS': {'png', 'jpg', 'jpeg', 'gif', 'webp'},
    'TEMPLATES_AUTO_RELOAD': True,
})

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Initialize Gemini client
try:
    client = genai.Client(api_key=app.config['GEMINI_API_KEY'])
except Exception as e:
    logger.error(f"Failed to initialize Gemini client: {e}")
    raise RuntimeError("Failed to initialize Gemini client")

# Configure Tesseract path
if os.name == 'nt':
    tess.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'
else:
    tess.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

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

def analyze_with_gemini(text):
    if not text.strip():
        raise ValueError("No text provided for analysis")

    response_schema = genai.types.Schema(
        type=genai.types.Type.OBJECT,
        required=["safety_rating", "quick_overview", "diet_suitability", 
                 "allergen_warning", "harmful_ingredients", "ingredient_breakdown"],
        properties={
            "safety_rating": genai.types.Schema(
                type=genai.types.Type.OBJECT,
                required=["score", "summary"],
                properties={
                    "score": genai.types.Schema(
                        type=genai.types.Type.NUMBER,
                        description="Safety score from 0-10 based on ingredient analysis",
                    ),
                    "summary": genai.types.Schema(
                        type=genai.types.Type.STRING,
                        description="Detailed explanation of safety rating",
                    ),
                },
            ),
            "quick_overview": genai.types.Schema(
                type=genai.types.Type.STRING,
                description="Comprehensive product analysis with key highlights",
            ),
            "diet_suitability": genai.types.Schema(
                type=genai.types.Type.OBJECT,
                required=["vegan", "vegetarian", "keto", "diabetic_friendly", "gluten_free"],
                properties={
                    "vegan": genai.types.Schema(
                        type=genai.types.Type.STRING,
                        enum=["Yes", "No", "Maybe"],
                    ),
                    "vegetarian": genai.types.Schema(
                        type=genai.types.Type.STRING,
                        enum=["Yes", "No", "Maybe"],
                    ),
                    "keto": genai.types.Schema(
                        type=genai.types.Type.STRING,
                        enum=["Yes", "No", "Maybe"],
                    ),
                    "diabetic_friendly": genai.types.Schema(
                        type=genai.types.Type.STRING,
                        enum=["Yes", "No", "Maybe"],
                    ),
                    "gluten_free": genai.types.Schema(
                        type=genai.types.Type.STRING,
                        enum=["Yes", "No", "Maybe"],
                    ),
                    "details": genai.types.Schema(
                        type=genai.types.Type.STRING,
                        description="Additional diet-specific notes",
                    ),
                },
            ),
            "allergen_warning": genai.types.Schema(
                type=genai.types.Type.ARRAY,
                description="List of major allergens detected",
                items=genai.types.Schema(
                    type=genai.types.Type.STRING,
                ),
            ),
            "harmful_ingredients": genai.types.Schema(
                type=genai.types.Type.ARRAY,
                items=genai.types.Schema(
                    type=genai.types.Type.OBJECT,
                    required=["name", "concern", "severity"],
                    properties={
                        "name": genai.types.Schema(
                            type=genai.types.Type.STRING,
                        ),
                        "concern": genai.types.Schema(
                            type=genai.types.Type.STRING,
                        ),
                        "severity": genai.types.Schema(
                            type=genai.types.Type.STRING,
                            enum=["Low", "Medium", "High"],
                        ),
                    },
                ),
            ),
            "ingredient_breakdown": genai.types.Schema(
                type=genai.types.Type.ARRAY,
                items=genai.types.Schema(
                    type=genai.types.Type.OBJECT,
                    required=["ingredient", "purpose"],
                    properties={
                        "ingredient": genai.types.Schema(
                            type=genai.types.Type.STRING,
                        ),
                        "purpose": genai.types.Schema(
                            type=genai.types.Type.STRING,
                        ),
                        "safety_note": genai.types.Schema(
                            type=genai.types.Type.STRING,
                        ),
                    },
                ),
            ),
            "clean_ingredient_list": genai.types.Schema(
                type=genai.types.Type.ARRAY,
                description="Simplified ingredient list for display",
                items=genai.types.Schema(
                    type=genai.types.Type.STRING,
                ),
            ),
            "recommendations": genai.types.Schema(
                type=genai.types.Type.OBJECT,
                properties={
                    "healthier_alternatives": genai.types.Schema(
                        type=genai.types.Type.STRING,
                        description="Suggested healthier product alternatives",
                    ),
                    "consumption_tips": genai.types.Schema(
                        type=genai.types.Type.STRING,
                        description="Recommendations for healthier consumption",
                    ),
                },
            ),
            "nutritional_highlights": genai.types.Schema(
                type=genai.types.Type.STRING,
                description="Key nutritional facts and their implications",
            ),
        },
    )

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=text)],
        )
    ]

    generate_content_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=response_schema,
        system_instruction=[
            types.Part.from_text(text="""You are a food ingredients expert helping users understand food products. You will be given extracted text from an image, which may contain a list of ingredients or may sometimes be incomplete or inaccurate due to OCR issues.
            Please follow the structure below and handle all edge cases gracefully. Your tone should be friendly, clear, and helpful for everyday users.If the text appears unrelated to food or does not contain any recognizable ingredients, return a message saying:
            "We couldn't identify any ingredients from this image. Please try again with a clearer photo of the ingredients list on the package."
            If the OCR text is incomplete, garbled, or has spelling errors, attempt to intelligently autocorrect, autocomplete, or infer the intended ingredients using your knowledge of common food ingredients.
            Do not fabricate information. Only work with what's confidently present or can be reasonably inferred."""),
        ],
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=generate_content_config,
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise RuntimeError("Failed to analyze ingredients with Gemini")

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
                extracted_text = tess.image_to_string(processed_img)
                
                if not extracted_text.strip():
                    flash('No text could be extracted from the image. Please try another image.')
                    return redirect(request.url)
                
                analysis_result = analyze_with_gemini(extracted_text)
                
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
