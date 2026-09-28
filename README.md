# Meeting Prep Agent

An agent that remembers every meeting you've had with a contact and briefs
you before the next one — powered by [Hindsight](https://hindsight.vectorize.io)
for persistent memory.

Without memory, an AI meeting assistant is generic. With memory, it recalls
exactly what was discussed last time, what promises are still open, and the
tone of the relationship — before you even ask.

## How it works

- Each contact gets their own Hindsight **memory bank**.
- Logging a meeting calls `retain()` — Hindsight extracts facts, entities,
  and builds up a knowledge graph automatically.
- "Prep me" calls `reflect()` — Hindsight reasons over everything it knows
  about that contact and writes a natural-language briefing.
- The "Memory timeline" panel calls `recall()` directly so you can *see* the
  raw memories accumulating — this is the part to point at during the demo,
  since it makes the memory layer visible rather than a black box.

## Setup

1. **Get a Hindsight Cloud account**: sign up at
   [ui.hindsight.vectorize.io](https://ui.hindsight.vectorize.io/signup) and
   apply promo code `MEMHACK99` in billing for $50 in free credits.
2. Grab your API key and base URL from the Hindsight Cloud dashboard.
3. Clone/copy this project, then:

   ```bash
   cd meeting-prep-agent
   python -m venv venv && source venv/bin/activate   # optional but recommended
   pip install -r requirements.txt
   cp .env.example .env
   # edit .env and paste in your HINDSIGHT_BASE_URL and HINDSIGHT_API_KEY
   python app.py
   ```

4. Open **http://localhost:5050**

That's it — no separate LLM key needed. Hindsight Cloud runs its own LLM for
fact extraction and reflection, so you don't have to wire up Groq/OpenAI
yourself. (If you later self-host Hindsight instead of using Cloud, note
that Groq's *free* tier is too rate-limited for Hindsight's retain calls —
you'd need a paid Groq tier or another provider; see Hindsight's
[Models docs](https://hindsight.vectorize.io/developer/models).)

## Demo script (for judges)

1. Add a contact, e.g. "Priya Shah."
2. Log a first meeting: *"First call with Priya. She's evaluating us against
   Vendor X. Budget is tight this quarter — she asked for a discount. I said
   I'd check with finance and get back to her by Friday."*
3. Click **Prep me** — with only one meeting logged, the agent should say
   this is your first interaction and summarize what you know so far.
4. Log a second meeting a few days later: *"Follow-up with Priya. Told her
   finance approved a 10% discount. She seemed relieved. She mentioned her
   team is also looking at a Q3 timeline for rollout."*
5. Click **Prep me** again — now the briefing should reference the discount
   promise being fulfilled, the Q3 timeline, and the overall trajectory of
   the relationship. This is the "before/after" moment: the second briefing
   is visibly more specific and useful than the first, because memory
   compounded.
6. Open the **Memory timeline** panel to show judges the raw extracted facts
   behind the briefing — this is where "memory is the star" becomes literal
   and visible, not just a claim.

## Project structure

```
meeting-prep-agent/
├── app.py                 # Flask routes
├── hindsight_service.py   # Hindsight client wrapper (retain/recall/reflect)
├── requirements.txt
├── .env.example
├── templates/index.html
└── static/
    ├── style.css
    └── app.js
```

## Notes for extending

- `hindsight_service.py` is the only file that talks to Hindsight — that's
  the "explanation of how Hindsight memory is used" the hackathon asks for.
- Contacts are tracked locally in `data/contacts.json` just so the UI has a
  list to show; Hindsight itself is the source of truth for what's actually
  remembered per contact.
- To make the "before/after" demo even sharper, you could add a toggle that
  calls `reflect()` with an empty/generic bank vs. the real one, to show a
  side-by-side generic-vs-personalized answer.
