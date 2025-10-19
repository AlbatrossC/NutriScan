# NutriScaner

**Live Demo**: [nutri-scaner.vercel.app](https://nutri-scaner.vercel.app)

## 🌟 Overview

NutriScaner is an intelligent food label analysis tool that bridges the gap between complex ingredient lists and consumer understanding. Simply snap a photo of any food label, and NutriScaner will decode the ingredients, explain their purposes, and provide safety information—making healthier food choices easier than ever.

## Features

- Upload images of food labels
- Extract text using OCR (Tesseract.js)
- Analyze ingredients with Google Gemini API
- View nutritional information in a clean format

## Tech Stack

- Python, Flask
- Tesseract.js (OCR)
- Google Gemini API
- PostgreSQL (optional logging)

## Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- A Google Gemini API key ([Get one here](https://aistudio.google.com/app/api-keys))

### 1. Clone the repository
```bash
git clone https://github.com/AlbatrossC/NutriScaner.git
cd NutriScaner
```

### 2. Create `.env` file
```env
# Required: Gemini API for ingredient analysis
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Database connection for activity logging
# Get from Neon (https://neon.tech) or Supabase (https://supabase.com)
DATABASE_LOGS_URL=your_database_connection_string
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the app
```bash
python app.py
```

Open `http://127.0.0.1:5000` in your browser.
