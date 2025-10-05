export async function analyzeBookImage(imageFile, geminiApiKey) {
  const formData = new FormData();
  formData.append('image', imageFile);

  try {
    const imageBase64 = await fileToBase64(imageFile);

    const requestBody = {
      contents: [{
        parts: [
          {
            text: `Analyze this library shelf image and extract book information.
For each book visible, provide:
1. Title (exact text from spine)
2. Row number (starting from 1 at top)
3. Column number (starting from 1 at left)

Return ONLY a valid JSON array in this exact format:
[{"title": "Book Title", "row": 1, "col": 1}]

If no books are clearly visible, return: []`
          },
          {
            inline_data: {
              mime_type: imageFile.type,
              data: imageBase64
            }
          }
        ]
      }]
    };

    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${geminiApiKey}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      }
    );

    if (!response.ok) {
      throw new Error(`Gemini API error: ${response.statusText}`);
    }

    const data = await response.json();
    const textResponse = data.candidates?.[0]?.content?.parts?.[0]?.text || '[]';

    let cleanedText = textResponse.trim();
    if (cleanedText.startsWith('```json')) {
      cleanedText = cleanedText.replace(/```json\n?/, '').replace(/```\n?$/, '');
    } else if (cleanedText.startsWith('```')) {
      cleanedText = cleanedText.replace(/```\n?/, '').replace(/```\n?$/, '');
    }

    const books = JSON.parse(cleanedText);
    return Array.isArray(books) ? books : [];
  } catch (error) {
    console.error('Error analyzing image with Gemini:', error);
    throw error;
  }
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => {
      const base64 = reader.result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = error => reject(error);
  });
}
