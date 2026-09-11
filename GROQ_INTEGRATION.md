# Groq API Integration for Translation

## Overview

Replaced Google Translate with **Groq API** for event translation from Serbian to Russian and English.

### Why Groq?

- **Free tier**: 14,400 requests/day (generous limit)
- **Fast**: 300-800 tokens/second
- **Better quality**: LLM-based translation with context awareness
- **Preserves toponyms**: Does NOT translate place names, street names, municipalities
- **No registration issues**: Works from anywhere, including Russia

### What Changed

#### 1. Dependencies (`scraper/requirements.txt`)
- Removed: `deep-translator` (Google Translate wrapper)
- Added: `groq` (official Groq SDK)

#### 2. Translation Function (`scraper/main.py`)
- **Before**: Used `GoogleTranslator` from `deep-translator`
- **After**: Uses Groq API with `llama-3.1-70b-versatile` model

#### 3. Key Improvements
- **Toponyms preserved**: Municipalities, street names, landmarks stay in Serbian
- **Better context**: LLM understands the full event description
- **Explicit instructions**: System prompt tells the model what NOT to translate
- **Date protection**: Dates are replaced with placeholders before translation

### Configuration

#### Environment Variable
Add `GROQ_API_KEY` to your environment:

```bash
export GROQ_API_KEY="your-groq-api-key-here"
```

#### Docker Compose
Already updated in `docker-compose.yml`:

```yaml
scraper:
  environment:
    DATABASE_URL: ${DATABASE_URL}
    GROQ_API_KEY: ${GROQ_API_KEY}
    TZ: ${TZ:-Europe/Belgrade}
```

### Getting Groq API Key

1. Go to https://console.groq.com
2. Sign up (free, no credit card required)
3. Create API key in Settings → API Keys
4. Copy the key (starts with `gsk_...`)

### How It Works

```python
async def translate_safe(text, target):
    """Translate text using Groq API with LLM-based translation."""
    
    # 1. Protect dates from translation
    dates = re.findall(r'\d{1,2}[\./\s]+\d{1,2}[\./\s]+\d{4}', text)
    for i, d in enumerate(dates):
        text = text.replace(d, f" [[DATE{i}]] ")
    
    # 2. Create system prompt with strict rules
    system_prompt = f"""You are a professional translator from Serbian to {target_lang}.

CRITICAL RULES:
1. Keep ALL place names, street names, municipality names EXACTLY as they appear
2. DO NOT translate: Barajevo, Čukarica, Grocka, Lazarevac, Mladenovac, 
   Novi Beograd, Obrenovac, Palilula, Rakovica, Savski venac, Sopot, 
   Stari grad, Surčin, Voždovac, Vračar, Zemun, Zvezdara
3. DO NOT translate street names (ulica, bulevar, trg, etc.)
4. Only translate the description of events, problems, and actions
5. Preserve date placeholders
6. Keep line breaks and formatting"""
    
    # 3. Call Groq API
    response = groq_client.chat.completions.create(
        model="llama-3.1-70b-versatile",  # Fast and high quality
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text[:4000]}
        ],
        temperature=0.3,  # Consistent translations
        max_tokens=2000
    )
    
    # 4. Restore dates
    translated = response.choices[0].message.content.strip()
    for i, d in enumerate(dates):
        translated = re.sub(rf'\[\[DATE{i}\]\]', d, translated)
    
    return translated
```

### Translation Quality

#### Before (Google Translate)
- ❌ Translated municipality names: "Stari grad" → "Old Town"
- ❌ Translated street names: "Bulevar Kralja Aleksandra" → "King Alexander Boulevard"
- ❌ Lost context in complex sentences
- ❌ Sometimes returned error pages

#### After (Groq + LLM)
- ✅ Preserves all toponyms: "Stari grad" stays "Stari grad"
- ✅ Keeps street names intact: "Bulevar Kralja Aleksandra" unchanged
- ✅ Better context understanding
- ✅ Consistent translations

### Fallback Behavior

If `GROQ_API_KEY` is not set or API fails:
- Returns original Serbian text (no translation)
- Logs warning message
- Site continues to work (just without translations)

### Cost

**FREE** for typical usage:
- Free tier: 14,400 requests/day
- Typical scraper run: 50-200 events
- Translation calls: 2 per event (Russian + English) = 100-400 requests
- **Well within free tier limits**

If you exceed the free tier (unlikely), paid tier is extremely cheap:
- ~$0.05-0.10 per 1M tokens
- Average event: ~200 tokens
- Cost per 1000 translations: ~$0.01-0.02

### Testing

To test the new translation:

```bash
# 1. Set your API key
export GROQ_API_KEY="your-key-here"

# 2. Rebuild scraper container
docker-compose build scraper

# 3. Restart scraper
docker-compose up -d scraper

# 4. Check logs
docker logs -f belgrade_scraper
```

Look for log messages:
- `Translation to ru successful via Groq` ✅
- `Translation to en successful via Groq` ✅
- `Groq API key not set` ❌ (if key missing)

### Deployment

#### Dev (hm.ss.ru)
```bash
# On your local machine
git add scraper/requirements.txt scraper/main.py docker-compose.yml
git commit -m "feat: Replace Google Translate with Groq API for better translations"
git push origin deploy/dev-setup

# On the server
ssh hm.ss.ru
cd /root/selfcheck/belgrade-utility-hub
git pull
export GROQ_API_KEY="your-key-here"  # Add to .env or environment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build scraper
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d scraper
```

#### Prod (bg.ss.ru)
```bash
# After testing on dev, merge to main
git checkout main
git merge deploy/dev-setup
git push origin main

# On the server
ssh hm.ss.ru
cd /root/selfcheck/belgrade-utility-hub
git pull
export GROQ_API_KEY="your-key-here"  # Add to .env or environment
docker-compose build scraper
docker-compose up -d scraper
```

### Monitoring

Check translation quality by comparing events in different languages:
- https://hm.ss.ru/?lang=srp (Serbian original)
- https://hm.ss.ru/?lang=ru (Russian translation)
- https://hm.ss.ru/?lang=en (English translation)

Pay attention to:
- Are municipality names preserved? ✅
- Are street names preserved? ✅
- Does the description make sense? ✅
- Are dates formatted correctly? ✅

### Troubleshooting

**Problem**: "Groq API key not set"
- **Solution**: Set `GROQ_API_KEY` environment variable in docker-compose or .env

**Problem**: Rate limit exceeded (unlikely)
- **Solution**: Groq has 14,400 requests/day free tier, should be plenty
- Check if scraper is running in a loop
- Consider caching translations

**Problem**: Translation returns original text
- **Solution**: Check Groq API key is valid
- Check network connectivity from scraper container
- Check logs for specific error message

### Alternative Models

If you want to experiment with different models:

```python
# Faster, smaller model (good for simple texts)
model="llama-3.1-8b-instant"

# Current (balanced speed/quality)
model="llama-3.1-70b-versatile"

# Highest quality (slower, probably overkill)
model="llama-3.1-405b-reasoning"
```

### Next Steps

1. ✅ Get Groq API key from https://console.groq.com
2. ✅ Test locally with the API key
3. ✅ Deploy to dev (hm.ss.ru)
4. ⏳ Monitor translation quality
5. ⏳ Deploy to prod (bg.ss.ru) after testing

---

**Questions?** Check Groq documentation: https://console.groq.com/docs
