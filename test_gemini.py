import google.generativeai as genai
import json

genai.configure(api_key="AIzaSyAPYgQwsSbyinHstrpf60aqNTvkA5qghkA")
generation_config = {
  "temperature": 0.7,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 1024,
  "response_mime_type": "application/json",
}
model = genai.GenerativeModel(
  model_name="gemini-flash-latest",
  generation_config=generation_config,
)

prompt = """
Respond ONLY with a valid JSON object matching exactly this schema:
{
  "condition": "Worry",
  "confidence": "High"
}
"""
try:
    response = model.generate_content(prompt)
    print("Raw text:")
    print(response.text)
    print("Parsed JSON:")
    print(json.loads(response.text))
except Exception as e:
    import traceback
    traceback.print_exc()
    print("Error:", e)
