from django.shortcuts import render
from .forms import ImageUploadForm
from .models import UploadedImage
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract as tess
from groq import Groq
from django.conf import settings
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Configure the API key
api_key = settings.API_KEY

client = Groq(api_key=api_key)

# Determine the Tesseract path based on the environment
if os.name == 'nt':  # Windows environment
    tess.pytesseract.tesseract_cmd = r'C:/Users/Soham/AppData/Local/Programs/Tesseract-OCR/tesseract.exe'
else:  # Linux environment (PythonAnywhere)
    tess.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

def upload_image(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_image = form.save()
            img_path = uploaded_image.image.path

            try:
                # Open the image and preprocess
                img = Image.open(img_path)
                
                # Convert to grayscale
                img = img.convert('L')
                
                # Enhance contrast and brightness
                contrast_enhancer = ImageEnhance.Contrast(img)
                img = contrast_enhancer.enhance(2)  # Adjust contrast factor as needed
                
                brightness_enhancer = ImageEnhance.Brightness(img)
                img = brightness_enhancer.enhance(1.5)  # Adjust brightness factor as needed

                # Apply noise reduction filter
                img = img.filter(ImageFilter.MedianFilter())

                # Apply sharpening filter
                img = img.filter(ImageFilter.SHARPEN())

                # Extract text from the image
                text = tess.image_to_string(img)
                logger.info(f"Extracted text: {text}")

                task = "Please provide a brief one-line overview of each ingredient in the product, along with their corresponding commercial names. Assess the overall safety of the product for consumption and specify the recommended maximum intake per week. Also, include information on the amount of fats, calories, and carbohydrates present in the product."

                chat_completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": task + text,
                        }
                    ],
                    model="llama3-8b-8192",
                )

                response_text = chat_completion.choices[0].message.content
                return render(request, 'result.html', {'response': response_text})
            except Exception as e:
                logger.error(f"Error processing image: {e}")
                return render(request, 'error.html', {'message': 'There was an error processing the image.'})
    else:
        form = ImageUploadForm()
    return render(request, 'upload.html', {'form': form})



#SWITCH TO GEMINI-API KEY IN CASE OF GORQ ERRORS
# from django.shortcuts import render
# from .forms import ImageUploadForm
# from .models import UploadedImage
# from PIL import Image, ImageEnhance, ImageFilter
# import pytesseract as tess
# import google.generativeai as genai
# from django.conf import settings
# import os
# import logging

# # Configure logging
# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)

# # Configure the API key
# api_key = settings.API_KEY
# genai.configure(api_key=api_key)

# # Determine the Tesseract path based on the environment
# if os.name == 'nt':  # Windows environment
#     tess.pytesseract.tesseract_cmd = r'C:/Users/Soham/AppData/Local/Programs/Tesseract-OCR/tesseract.exe'
# else:  # Linux environment (PythonAnywhere)
#     tess.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# generation_config = {
#     "temperature": 2,
#     "top_p": 0.95,
#     "top_k": 64,
#     "max_output_tokens": 16384,
# }

# model = genai.GenerativeModel(
#     model_name="gemini-1.5-flash",
#     generation_config=generation_config,
# )

# def upload_image(request):
#     if request.method == 'POST':
#         form = ImageUploadForm(request.POST, request.FILES)
#         if form.is_valid():
#             uploaded_image = form.save()
#             img_path = uploaded_image.image.path

#             try:
#                 # Open the image and preprocess
#                 img = Image.open(img_path)
                
#                 # Convert to grayscale
#                 img = img.convert('L')
                
#                 # Enhance contrast and brightness
#                 contrast_enhancer = ImageEnhance.Contrast(img)
#                 img = contrast_enhancer.enhance(2)  # Adjust contrast factor as needed
                
#                 brightness_enhancer = ImageEnhance.Brightness(img)
#                 img = brightness_enhancer.enhance(1.5)  # Adjust brightness factor as needed

#                 # Apply adaptive thresholding (commented out example)
#                 # img = cv2.adaptiveThreshold(np.array(img), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

#                 # Apply noise reduction filter
#                 img = img.filter(ImageFilter.MedianFilter())

#                 # Apply sharpening filter
#                 img = img.filter(ImageFilter.SHARPEN())

#                 # Optional: Resize the image (for example, scale to 1.5x)
#                 # width, height = img.size
#                 # img = img.resize((int(width * 1.5), int(height * 1.5)))

#                 # Extract text from the image
#                 text = tess.image_to_string(img)
#                 logger.info(f"Extracted text: {text}")

#                 chat_session = model.start_chat(
#                     history=[
#                         {
#                             "role": "user",
#                             "parts": [
#                                 "Please provide an overview of ingredients along with their corresponding commercial product names. For each ingredient, identify the common name of any chemical compounds, assess whether the product is safe to consume or drink, and specify the recommended quantity or dosage for safe consumption. Please respond in plain text without bold letters.",
#                             ],
#                         },
#                         {
#                             "role": "model",
#                             "parts": [
#                                 "Okay",
#                             ],
#                         },
#                     ]
#                 )

#                 response = chat_session.send_message(text)
#                 return render(request, 'result.html', {'response': response.text})
#             except Exception as e:
#                 logger.error(f"Error processing image: {e}")
#                 return render(request, 'error.html', {'message': 'There was an error processing the image.'})
#     else:
#         form = ImageUploadForm()
#     return render(request, 'upload.html', {'form': form})

