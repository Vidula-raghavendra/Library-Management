# How to Get Your Gemini API Key

## Quick Steps

1. **Visit Google AI Studio**
   - Go to: https://makersuite.google.com/app/apikey
   - Or: https://aistudio.google.com/app/apikey

2. **Sign In**
   - Use your Google account to sign in
   - If you don't have one, create a free Google account

3. **Create API Key**
   - Click "Create API Key" button
   - Choose "Create API key in new project" (recommended)
   - Or select an existing Google Cloud project

4. **Copy Your Key**
   - Your API key will be displayed
   - Click the copy icon to copy it
   - **IMPORTANT**: Save this key securely!

5. **Use in the App**
   - Go to the "OCR Scan" page in the app
   - Paste your API key in the "Gemini API Key" field
   - The key will be used only for that session
   - You'll need to enter it each time you use OCR

## Important Notes

- The Gemini API has a **free tier** with generous limits
- Your API key is private - never share it publicly
- The app doesn't store your API key
- You need to enter it each time you want to use OCR scanning

## Free Tier Limits

Gemini 1.5 Flash (used by this app):
- 15 requests per minute
- 1 million tokens per minute
- 1,500 requests per day

This is more than enough for typical library use!

## Security Tips

- Don't commit API keys to git repositories
- Don't share your API key in screenshots
- If you accidentally expose your key, delete it and create a new one
- Consider creating a separate Google Cloud project for this app

## Troubleshooting

**"Invalid API key" error**
- Make sure you copied the entire key
- Check for extra spaces at the beginning or end
- Verify the key is active in Google AI Studio

**"Quota exceeded" error**
- You've hit the free tier limit
- Wait a few minutes and try again
- Consider upgrading to a paid plan if needed

**"Model not found" error**
- Ensure you have access to Gemini 1.5 Flash
- Try creating a new API key

## Alternative: Environment Variable (Advanced)

If you're deploying this app, you can set the API key as an environment variable:

1. Add to your `.env` file:
   ```
   VITE_GEMINI_API_KEY=your_api_key_here
   ```

2. Update `src/pages/OCRScan.jsx` to use it by default:
   ```javascript
   const [geminiApiKey, setGeminiApiKey] = useState(
     import.meta.env.VITE_GEMINI_API_KEY || ''
   );
   ```

**WARNING**: Never commit `.env` files with real API keys to public repositories!

## Cost Information

- Free tier is sufficient for most library use cases
- If you need more, pricing is very affordable
- Check current pricing: https://ai.google.dev/pricing

## Support

For API-related questions:
- Gemini API Documentation: https://ai.google.dev/docs
- Google Cloud Support: https://cloud.google.com/support

Enjoy using OCR scanning in your library!
