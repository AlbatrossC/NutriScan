from google import genai

SYSTEM_INSTRUCTION = """You are a certified food safety and nutrition expert. You'll be given a text block extracted from a packaged food label. Your task is to analyze this text and return a JSON object conforming strictly to the provided schema.

Important Guidelines:
1. Return only a valid JSON object with no markdown or explanations.
2. The sugar_content field must always be included, even if the sugar is not directly mentioned.
   a. If the percentage is not explicitly available, estimate it intelligently based on ingredients and general product knowledge.
   b. The value must be a number (int or float), representing percentage out of 100.
   c. The description should summarize in 2 lines whether the sugar content is too high or too low, and whether it's safe to consume.
3. If this is not a food product, respond with:
   { "error": "Wrong image uploaded. Please upload an ingredients image" }
4. If unable to analyze, respond with:
   { "error": "Unable to analyze" }
5. Avoid assumptions outside general food safety knowledge. Be factual and concise.
6. Analyze all ingredients carefully for potential health concerns, allergens, and dietary restrictions.
7. Provide actionable insights and recommendations for consumers.
8. Provide only the final structured JSON object in your response.
"""

RESPONSE_SCHEMA = genai.types.Schema(
    type=genai.types.Type.OBJECT,
    required=["safety_rating", "quick_overview", "diet_suitability", "allergen_warning", 
              "harmful_ingredients", "ingredient_breakdown", "sugar_content"],
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
        "sugar_content": genai.types.Schema(
            type=genai.types.Type.OBJECT,
            description="Analysis of sugar content",
            required=["percentage", "description"],
            properties={
                "percentage": genai.types.Schema(
                    type=genai.types.Type.NUMBER,
                    description="Estimated sugar content as a percentage of the product (0-100)",
                ),
                "description": genai.types.Schema(
                    type=genai.types.Type.STRING,
                    description="2-line summary of sugar level (e.g., too high/low, safe to consume or not)",
                ),
            },
        ),
    },
)