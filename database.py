from PIL import Image
import google.generativeai as genai

def extract_with_gemini(image):
    genai.configure(api_key="YOUR_API_KEY")  # Replace with your actual API key

    try:
        model = genai.GenerativeModel("gemini-pro-vision")

        response = model.generate_content(
            [image,  # PIL Image object
             "Extract text from the book spine exactly as it appears. "
             "Return only the raw text without any formatting or comments. "
             "Each book's title should be an element of a python list. And give no other content. "
             "Ex- ['Linux kernel development']"
            ]
        )

        return response.text.strip()

    except Exception as e:
        return f"Error: {str(e)}"

from PIL import Image
import google.generativeai as genai

def extract_with_gemini(image):
    genai.configure(api_key="")  # Replace with your actual API key

    try:
        model = genai.GenerativeModel("gemini-pro-vision")

        response = model.generate_content(
            [image,  # PIL Image object
             "Extract text from the book spine exactly as it appears. "
             "Return only the raw text without any formatting or comments. "
             "Each book's title should be an element of a python list. And give no other content. "
             "Ex- ['Linux kernel development']"
            ]
        )

        return response.text.strip()

    except Exception as e:
        return f"Error: {str(e)}"
from PIL import Image
import google.generativeai as genai

def extract_with_gemini(image):
    genai.configure(api_key="YOUR_API_KEY")  # Replace with your actual API key

    try:
        model = genai.GenerativeModel("gemini-pro-vision")

        response = model.generate_content(
            [image,  # PIL Image object
             "Extract text from the book spine exactly as it appears. "
             "Return only the raw text without any formatting or comments. "
             "Each book's title should be an element of a python list. And give no other content. "
             "Ex- ['Linux kernel development']"
            ]
        )

        return response.text.strip()

    except Exception as e:
        return f"Error: {str(e)}"
from PIL import Image
import google.generativeai as genai

def extract_with_gemini(image):
    genai.configure(api_key="YOUR_API_KEY")  # Replace with your actual API key

    try:
        model = genai.GenerativeModel("gemini-pro-vision")

        response = model.generate_content(
            [image,  # PIL Image object
             "Extract text from the book spine exactly as it appears. "
             "Return only the raw text without any formatting or comments. "
             "Each book's title should be an element of a python list. And give no other content. "
             "Ex- ['Linux kernel development']"
            ]
        )

        return response.text.strip()

    except Exception as e:
        return f"Error: {str(e)}"
from PIL import Image
import google.generativeai as genai

def extract_with_gemini(image):
    genai.configure(api_key="YOUR_API_KEY")  # Replace with your actual API key

    try:
        model = genai.GenerativeModel("gemini-pro-vision")

        response = model.generate_content(
            [image,  # PIL Image object
             "Extract text from the book spine exactly as it appears. "
             "Return only the raw text without any formatting or comments. "
             "Each book's title should be an element of a python list. And give no other content. "
             "Ex- ['Linux kernel development']"
            ]
        )

        return response.text.strip()

    except Exception as e:
        return f"Error: {str(e)}"
from PIL import Image
import google.generativeai as genai

def extract_with_gemini(image):
    genai.configure(api_key="YOUR_API_KEY")  # Replace with your actual API key

    try:
        model = genai.GenerativeModel("gemini-pro-vision")

        response = model.generate_content(
            [image,  # PIL Image object
             "Extract text from the book spine exactly as it appears. "
             "Return only the raw text without any formatting or comments. "
             "Each book's title should be an element of a python list. And give no other content. "
             "Ex- ['Linux kernel development']"
            ]
        )

        return response.text.strip()

    except Exception as e:
        return f"Error: {str(e)}"
from PIL import Image
import google.generativeai as genai

def extract_with_gemini(image):
    genai.configure(api_key="YOUR_API_KEY")  # Replace with your actual API key

    try:
        model = genai.GenerativeModel("gemini-pro-vision")

        response = model.generate_content(
            [image,  # PIL Image object
             "Extract text from the book spine exactly as it appears. "
             "Return only the raw text without any formatting or comments. "
             "Each book's title should be an element of a python list. And give no other content. "
             "Ex- ['Linux kernel development']"
            ]
        )

        return response.text.strip()

    except Exception as e:
        return f"Error: {str(e)}"
