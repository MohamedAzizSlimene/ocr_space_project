# Solution Discussion: Handling Multiple Arabic ID Card Formats

## The Problem

Currently, `json_parsing.py` is hardcoded for **Tunisian national ID cards** only. It relies on specific Arabic keywords like:
- `اللقب` (last name)
- `الاسم` (first name)
- `بن` / `ابن` (father's name)
- `تاريخ الولادة` (date of birth)
- `مكانها` / `مكان الولادة` (place of birth)

But other Arabic-speaking countries have completely different card layouts and labels. For example, a **Moroccan national ID card** uses:
- `CARTE NATIONALE D'IDENTITE` (bilingual French/Arabic)
- `مزدادة بتاريخ` / `Née le` (date of birth)
- `البطاقة الوطنية للتعريف` (national identity card)
- No explicit labeled fields — names appear as standalone lines without keywords

### Example Moroccan Card OCR Output:
```json
{
  "parsed": {
    "date_of_birth": null,
    "document_number": "01234567",
    "father_name": null,
    "first_name": null,
    "last_name": null,
    "place_of_birth": null
  },
  "raw_text_lines": [
    "ROYAUME DU MAROC",
    "CARTE NATIONALE D'IDENTITE",
    "N 01234567",
    "EL ALAMI",
    "المملكة المغربية",
    "البطاقة الوطنية للتعريف",
    "العلمي",
    "زينب",
    "مزدادة بتاريخ",
    "ZAINEB",
    "Née le",
    "05/12/1983",
    "QUARZAZATE",
    "المدير العام للأمن الوطني",
    "Specimen",
    "عبد اللطيف حموشي",
    "ب ورزازات",
    "☆",
    "CAN 123457",
    "Valable jusqu'au 22/07/2029 صالحة إلى غاية"
  ]
}
```

The current parser fails because:
1. Fields are **not labeled with keywords** — names just appear as standalone lines
2. The card is **bilingual** (French + Arabic) with positional meaning
3. Different countries have **completely different structures**

---

## Possible Solutions

### Option 1: Rule-Based Multi-Country Parser (No LLM)

Create a separate parsing module per country/card type, with a **card type detector** that identifies which country's card it is based on header keywords.

**How it works:**
```
OCR Text → Card Type Detector → Country-Specific Parser → Structured Output
```

**Card detection keywords:**
| Country   | Detection Keywords                                      |
|-----------|---------------------------------------------------------|
| Tunisia   | `بطاقة التعريف الوطنية`, `الجمهورية التونسية`          |
| Morocco   | `المملكة المغربية`, `البطاقة الوطنية للتعريف`, `ROYAUME DU MAROC` |
| Algeria   | `الجمهورية الجزائرية`, `بطاقة التعريف الوطنية`         |
| Egypt     | `جمهورية مصر العربية`, `بطاقة الرقم القومي`            |
| Saudi     | `المملكة العربية السعودية`, `بطاقة الهوية الوطنية`     |

**Pros:**
- Fast (no external API or model needed)
- Deterministic and predictable
- No GPU/CPU overhead
- Works offline

**Cons:**
- Requires manual work for each new card type
- Fragile — OCR errors can break positional logic
- Doesn't generalize to unknown card formats
- Maintenance burden grows with each country added

---

### Option 2: LLM-Based Parsing (Ollama + Qwen)

Use a local LLM (Qwen via Ollama) to intelligently extract fields from raw OCR text regardless of format.

**How it works:**
```
OCR Text → LLM Prompt → Structured JSON Output
```

**Example prompt:**
```
You are an ID card parser. Given the following OCR text from an Arabic identity card, 
extract these fields as JSON: first_name, last_name, document_number, father_name, 
place_of_birth, date_of_birth.

If a field is not found, set it to null.

OCR Text:
{raw_text}

Return ONLY valid JSON.
```

**Pros:**
- Handles ANY card format without country-specific code
- Understands context and positional meaning
- Can handle OCR noise gracefully
- One solution for all countries
- Self-improving with better models

**Cons:**
- **SLOW on CPU** — Qwen 7B can take 10-30+ seconds per request on CPU
- Unpredictable output (may hallucinate or return malformed JSON)
- Requires Ollama running as a service
- Higher resource usage
- Not suitable for real-time/production without GPU

---

### Option 3: Hybrid Approach (Recommended) ⭐

Combine rule-based detection with LLM fallback:

```
OCR Text 
    │
    ▼
Card Type Detector (keyword-based)
    │
    ├── Known card type? → Country-Specific Rule Parser (fast)
    │
    └── Unknown card type? → LLM Fallback (Ollama/Qwen)
```

**How it works:**
1. First, try to detect the card type using header keywords
2. If detected (e.g., Tunisian, Moroccan), use a fast rule-based parser
3. If unknown or rule-based parser returns too many nulls, fall back to LLM

**Pros:**
- Fast for known card types (no LLM needed)
- Graceful fallback for unknown formats
- LLM only called when necessary (saves CPU time)
- Can progressively add rule-based parsers for common cards
- Best of both worlds

**Cons:**
- More complex architecture
- Still slow when LLM fallback is triggered on CPU

---

### Option 4: Smaller/Faster Model or API-Based LLM

Instead of running Qwen on CPU, consider:

| Alternative              | Speed     | Cost       | Notes                                    |
|--------------------------|-----------|------------|------------------------------------------|
| Qwen 0.5B / 1.5B        | Faster    | Free/Local | Less accurate but much faster on CPU     |
| TinyLlama                | Very fast | Free/Local | May struggle with Arabic                 |
| Groq API (free tier)     | Very fast | Free       | Cloud-based, fast inference              |
| OpenAI GPT-4o-mini       | Fast      | ~$0.15/1M  | Very accurate, cheap                     |
| Google Gemini Flash      | Fast      | Free tier  | Good Arabic support                      |

**Note:** If you're already using ocr.space (a cloud API), adding another cloud API for parsing might be acceptable. The free tiers of Groq or Gemini could handle the parsing step very quickly without CPU concerns.

---

## Performance Comparison

| Approach                    | Speed (per card) | Accuracy | Maintenance | Scalability |
|-----------------------------|------------------|----------|-------------|-------------|
| Rule-based (per country)    | <100ms           | High*    | High        | Low         |
| LLM on CPU (Qwen 7B)       | 10-30s           | High     | Low         | High        |
| LLM on CPU (Qwen 0.5B)     | 2-5s             | Medium   | Low         | High        |
| Hybrid (rules + LLM)       | <100ms / 10-30s  | High     | Medium      | High        |
| Cloud LLM API (Groq/Gemini)| 1-3s             | Very High| Low         | High        |

*High accuracy only for cards with explicit keyword labels

---

## My Recommendation

### For your situation (CPU-only deployment):

**Go with Option 3 (Hybrid)** with this priority:

1. **Immediately:** Add a Moroccan parser (rule-based) since you already have a sample
2. **For the Moroccan card specifically:** The structure is positional — names appear after the document number, date appears after `مزدادة بتاريخ` or `Née le`, place appears after the date
3. **For unknown cards:** Use Qwen 0.5B or 1.5B (much faster on CPU than 7B) as fallback
4. **Long term:** If latency matters, consider Groq free API (very fast, free, good Arabic)

### Moroccan Card Parsing Logic (Rule-Based):

```python
# Detection: "المملكة المغربية" or "ROYAUME DU MAROC" in text
# Document number: line starting with "N " followed by digits
# Last name: first name-like line after document number (French, uppercase)
# First name: Arabic name line OR French name line after last name
# Date of birth: line matching date pattern after "Née le" or "مزدادة بتاريخ"
# Place of birth: line after date of birth (city name)
```

---

## Questions to Decide Before Implementation

1. **How many countries do we need to support initially?** (Tunisia + Morocco + ?)
2. **Is 10-30s acceptable for unknown card types?** (LLM fallback on CPU)
3. **Would you accept a cloud API for the parsing step?** (Groq is free and fast)
4. **Should we use Qwen 0.5B instead of 7B for faster CPU inference?**
5. **Do we need to handle cards that are not identity cards?** (driver's license, passport, etc.)

---

## Next Steps (Once We Agree)

- [ ] Refactor `json_parsing.py` into a modular parser system
- [ ] Add card type detection logic
- [ ] Implement Moroccan ID card parser
- [ ] Add LLM fallback integration (Ollama API call)
- [ ] Update `app.py` to use the new parser system
- [ ] Test with multiple card samples
