Read the file `src/EduMap.Api/Data/countries.json` and find all countries that have a `translations.sr-Cyrl.name` value. Randomly sample 20 of them (or all if fewer than 20 exist).

For each sampled country, evaluate the `translations.sr-Cyrl` block (name, capital, funFact if present) against this quality bar:

**Reviewer persona:** You're a native Serbian speaker checking text that will be read aloud by Una, a 7-year-old who reads Cyrillic fluently. The text should sound like something a parent or teacher would say — natural, warm, never robotic. She should be able to read it aloud without stumbling over the phrasing.

**Flag if any of these are true:**
- The text sounds like word-for-word machine translation (stiff phrasing, unnatural word order, dictionary-style)
- Any Latin characters appear in a Cyrillic field (script mixing is always a bug)
- A funFact contains vocabulary a 7-year-old Serbian speaker is unlikely to know
- A country name or capital uses an unusual/unfamiliar transliteration instead of the standard Serbian Cyrillic form

**Output format — for each flagged entry:**
`ISO2 | field | what's wrong | suggested rewrite`

**End with a summary:**
- Total reviewed
- Total flagged
- Overall quality: **Good** (≤10% flagged) / **Needs work** (10–30%) / **Poor** (>30%)

Be specific. A flag without a suggested rewrite is not actionable.
