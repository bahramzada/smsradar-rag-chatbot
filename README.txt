SMSRadar RAG Chatbot

Bu layihə `all_questions_clean.csv` məlumat bazasından istifadə edən, OpenRouter üzərində işləyən və Azərbaycan dilində YHQ suallarına cavab verən RAG chatbotudur.

Əsas xüsusiyyətlər:
- OpenRouter embedding modeli: `openai/text-embedding-3-large`
- OpenRouter chat modeli: `openai/gpt-oss-120b`
- ChromaDB ilə vektor axtarışı
- Lokal fallback retrieval (vektor nəticəsi zəif olduqda)
- Rus jarqonu/translit normallaşdırma (`protiv` -> `əks yola`, `qirmizi` -> `qırmızı`)
- Xərc optimizasiyası üçün birbaşa cavab rejimi (uyğunluq yüksəkdirsə chat çağırışı etmir)
- Veb interfeysdə dark/light mode

İşə salma (lokal):
1) Virtual mühit yarat:
   - `python -m venv .venv`
   - `source .venv/bin/activate`
2) Paketləri qur:
   - `pip install -r requirements.txt`
3) Məlumatı təmizlə (yalnız `question` və `reply`, əlaqə nömrələri silinir):
   - `python -m scripts.clean_csv`
4) `.env` faylı hazırla:
   - `cp .env.example .env`
   - `OPENROUTER_API_KEY` daxil et
5) Vektor bazanı doldur:
   - `python -m scripts.ingest`
6) Serveri işə sal:
   - `uvicorn app.main:app --reload`
7) Brauzerdə aç:
   - `http://localhost:8000`

Vacib env dəyişənləri:
- `OPENROUTER_API_KEY` — OpenRouter açarı
- `EMBEDDING_MODEL`, `CHAT_MODEL` — modellər
- `CSV_PATH` — default: `all_questions_clean.csv`
- `INGEST_BATCH_SIZE` — ingest batch ölçüsü
- `TOP_K` — retrieval nəticə sayı
- `MAX_CONTEXT_CHARS` — LLM kontekst limiti
- `CHAT_MAX_TOKENS`, `CHAT_TEMPERATURE` — chat davranışı
- `VECTOR_MAX_DISTANCE` — vektor nəticə keyfiyyət həddi
- `LOCAL_FALLBACK_TOP_K` — lokal fallback nəticə sayı
- `USE_DIRECT_ANSWER`, `DIRECT_ANSWER_MIN_SCORE` — birbaşa cavab rejimi

Coolify deploy:
1) Repo-nu GitHub-a push et.
2) Coolify-da Application yarat və repo-nu seç.
3) Dockerfile ilə build et.
4) Env dəyişənlərini daxil et (`.env.example` əsas götür).
   - `CSV_PATH=all_questions_clean.csv` olmalıdır (köhnə `all_questions.csv` dəyərindən istifadə etməyin).
5) Persistent volume mount et: `/app/data/chroma`
6) İlk deploymentdan sonra Console-da bir dəfə:
   - `python -m scripts.ingest`
7) Sağlamlıq endpoint:
   - `/api/health`

Qeyd:
- `all_questions_clean.csv` yalnız sual-cavab mətnini saxlayır; əlaqə nömrələri təmizlənir.
- Chat cavabının altında istifadə olunan mənbələr görünür.
