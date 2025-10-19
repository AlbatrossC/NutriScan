from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import json
from google import genai
from google.genai import types
from src.instructions import SYSTEM_INSTRUCTION, RESPONSE_SCHEMA
from src.logs import db_logger

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "flask-local-secret-key")


def analyze_with_gemini(extracted_text):
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            error_msg = "API key not configured"
            db_logger.log_analysis(extracted_text, error_type=error_msg)
            return {"error": error_msg}

        client = genai.Client(api_key=api_key)
        model = "gemini-2.0-flash-lite"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=extracted_text),
                ],
            ),
        ]

        generate_content_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
            system_instruction=[types.Part.from_text(text=SYSTEM_INSTRUCTION)],
        )

        # Collect the streaming response
        response_text = ""
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            response_text += chunk.text

        # Parse JSON response
        result = json.loads(response_text)

        # Log successful analysis
        db_logger.log_analysis(extracted_text, output_text=result)
        return result

    except json.JSONDecodeError as e:
        error_msg = "Invalid response format from AI"
        db_logger.log_analysis(extracted_text, error_type=f"JSONDecodeError: {str(e)}")
        return {"error": error_msg}

    except Exception as e:
        error_msg = f"Analysis failed: {str(e)}"
        db_logger.log_analysis(extracted_text, error_type=str(e))
        return {"error": error_msg}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json()
        extracted_text = data.get("text", "")
        image_data = data.get("image", "")

        if not extracted_text:
            return jsonify({"error": "No text provided"}), 400

        # Analyze with Gemini
        result = analyze_with_gemini(extracted_text)

        # Check if there's an error in the result
        if "error" in result:
            return jsonify(result), 400

        # Store the result and image in session
        session['analysisResult'] = result
        if image_data:
            session['imageUrl'] = image_data

        return jsonify(result), 200

    except Exception as e:
        db_logger.log_analysis("", error_type=f"Server error: {str(e)}")
        return jsonify({"error": "Server error occurred"}), 500


@app.route("/result")
def result():
    # Get the analysis result from session
    result_data = session.get('analysisResult')
    if not result_data:
        return redirect(url_for('index'))

    # Get the image URL if stored
    image_url = session.get('imageUrl', '')

    return render_template("result.html", result=result_data, image_url=image_url)


@app.route("/clear-session")
def clear_session():
    session.clear()
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(debug=True)
