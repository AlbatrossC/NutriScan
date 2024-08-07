

# Create your views here.
from django.shortcuts import render
from .forms import ImageUploadForm
from .models import UploadedImage
from PIL import Image
import pytesseract as tess
import google.generativeai as genai
from django.conf import settings
from django.core.files.storage import default_storage
from django.conf import settings

# Configure the API key
api_key = settings.API_KEY
tess.pytesseract.tesseract_cmd = r'C:/Users/Soham/AppData/Local/Programs/Tesseract-OCR/tesseract.exe'
genai.configure(api_key=api_key)

generation_config = {
    "temperature": 2,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 16384,
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

def upload_image(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_image = form.save()
            img_path = uploaded_image.image.path

            img = Image.open(img_path)
            text = tess.image_to_string(img)

            chat_session = model.start_chat(
                history=[
                    {
                        "role": "user",
                        "parts": [
                            "Please provide a detailed list of ingredients along with their corresponding commercial product names. For each ingredient, identify the common name of any chemical compounds, assess whether the product is safe to consume or drink, and specify the recommended quantity or dosage for safe consumption. Please respond in plain text without bold letters.",
                        ],
                    },
                    {
                        "role": "model",
                        "parts": [
                            "Okay",
                        ],
                    },
                ]
            )

            response = chat_session.send_message(text)
            return render(request, 'result.html', {'response': response.text})
    else:
        form = ImageUploadForm()
    return render(request, 'upload.html', {'form': form})
