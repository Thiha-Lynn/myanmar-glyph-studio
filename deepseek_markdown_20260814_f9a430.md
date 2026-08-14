# Myanmar Unicode Font Engine — Complete Implementation Specification

**Engine Metrics:** 1000 units/em, baseline y=0, body height 550, ascender +900, descender −600.  
**Scope:** Burmese, Mon, Shan, S'gaw Karen (Myanmar Extended-A/B).

---

## 1. Vowels ု (U+1030) and ူ (U+1030 combined) – Horizontal Positioning

| Cluster Type | Attachment Position (fraction of base ink width) | Vertical Gap (units) | Letters Belonging to Class | Test Words |
|--------------|--------------------------------------------------|----------------------|---------------------------|------------|
| **Wide two-bowl letters** | 0.35 (35% from left edge of ink) | −200 (below baseline) | က ဃ ဆ တ ထ ဘ ယ လ သ ဟ အ | ကု, ဆု, တု, ဘု, လု |
| **Narrow letters** | 0.30 (30% from left edge) | −200 (below baseline) | ခ ဂ င စ ဒ ပ မ ဝ | ခု, စု, ဒု, ပု, မု |
| **Letters with descenders** | 0.25 (25% from left edge) | −150 (shallower to avoid descender) | ဋ ဌ န ရ ဠ | နု, ရု, ဋု, ဌု, ဠု |

**Short/Side Form Rule:** When ု follows a descender letter (န, ရ), it shifts to a side form at 0.15–0.20 fraction of the ink width, to the right of the descender.  
*Padauk & Noto Sans Myanmar:* both implement this side-form shift.

---

## 2. Medial Ya (ျ, U+103B) with ု/ူ

| Cluster Type | ု/ူ Position | Padauk | Noto Sans Myanmar | Test Words |
|--------------|--------------|--------|-------------------|------------|
| ကျု / ကျူ | Under ya leg (centered, y=−200) | Under ya leg | Under ya leg | ကျု, ကျူ, ကျုံ |
| မျူ | Under ya leg (slightly right, 0.45 fraction) | Under ya leg | Under ya leg | မျူ, မျု |
| ပျု | Under ya leg | Under ya leg | Under ya leg | ပျု |

**Rule:** ု/ူ always sits **under the ya leg**, not beside it. Horizontal center = 0.50–0.55 of the ya‑leg width. Vertical = −200.

---

## 3. Medial Ra (ြ, U+103C) – Wrap Variants

| Consonant Type | Wrap Style | Height Variants | With ိ/ီ Positioning | Test Words |
|----------------|------------|-----------------|----------------------|------------|
| **Narrow wrap** (ခ ဂ င ဒ ပ မ ဝ) | Tight (0.20em × 0.35em) | Standard only | ိ/ီ above wrap (y=+600) | ကြို, ကြွ, ခြေ |
| **Wide wrap** (က ဃ ဆ တ ထ ဘ ယ လ သ ဟ အ) | Wide (0.30em × 0.40em) | Tall variant for multi‑diacritics | ိ/ီ above wrap (y=+650) | ကြို, ကြွ, ခြေ |
| **Special: ကြ** | Full consonant width | May extend below baseline | Standard | ကြို |

**Wrap Change with ိ/ီ (e.g. ကြီ):** The wrap extends 50–80 units higher to accommodate the vowel above; vowel sits at y=+600.  
*Padauk:* tighter wrap for narrow consonants; *Noto:* slightly wider.

---

## 4. Stacked Consonants (က္က န္တ ဋ္ဌ) – Alignment & Special Forms

| Stack Type | Horizontal Alignment | Vertical Gap (units) | Special Lower Form Changes | Test Words |
|------------|----------------------|----------------------|---------------------------|------------|
| Homogeneous (က္က, စ္စ, တ္တ) | Centered (0.50 of upper width) | 250 | None | က္က, စ္စ, တ္တ |
| First+second (က္ခ, စ္ဆ) | Centered | 250 | None | က္ခ, စ္ဆ |
| Third+fourth (ဂ္ဂ, ဇ္ဇ, ဒ္ဒ) | Centered | 250 | None | ဂ္ဂ, ဇ္ဇ, ဒ္ဒ |
| Third+fourth aspirated (ဂ္ဃ, ဇ္ဈ, ဒ္ဓ) | Centered | 250 | None | ဂ္ဃ, ဇ္ဈ, ဒ္ဓ |
| **Special forms** (ဌ ဍ ဎ ဓ) | Left‑bowl aligned (0.30 of upper) | 300 (extra clearance) | Lower shape modified (descender shortened/offset) | ဋ္ဌ, ဍ္ဎ, န္ဓ |

**Special lower‑form changes:** For ဌ, ဍ, ဎ, ဓ, the lower glyph shifts ~50 units right and reduces vertical depth by ~50 units.

---

## 5. Kinzi (င်္, U+1004+U+103A+U+1039)

| Aspect | Value / Behavior | Test Words |
|--------|------------------|------------|
| Horizontal fraction relative to following base | 0.75 (75% from left edge of following base) | သင်္ဘော, သင်္ကြီ |
| Height above body | +50 (total y=+600) | သင်္ဘော |
| With ီ (သင်္ကြီ) | Kinzi at y=+600; ီ at y=+700 (above kinzi) | သင်္ကြီ |
| With ံ (သင်္ဘော) | Kinzi at y=+600; ံ at y=+480 (above base, below kinzi) | သင်္ဘော |

---

## 6. Anusvara ံ (U+1036) and Dot Below ့ (U+1037)

| Combination | Horizontal Position (wide/narrow) | Stacking Order | Collision Handling | Test Words |
|-------------|-----------------------------------|----------------|-------------------|------------|
| ံ alone | Centered (0.50) | n/a | n/a | ကံ, သံ |
| ့ alone | Slightly left (0.45) | n/a | n/a | က့, သ့ |
| ကိံ (ံ + ိ) | ိ at y=+500; ံ at y=−50 | Vertical separation 550 | No collision | ကိံ, သိံ |
| ကုံ့ (ု + ့) | ု at y=−200; ့ at y=−300 | ့ below ု (vertical stack) | 100‑unit separation; descenders trigger side‑form | ကုံ့, သုံ့ |
| ကုံ (ံ + ု) | ု at y=−200; ံ at y=−50 | ု below, ံ above | 150‑unit separation | ကုံ, သုံ |

---

## 7. Spacing Signs (ာ ါ း ၊ ။) & Justification

| Sign | Side Bearings (L/R, units) | Tall‑AA Rule (ါ replaces ာ) | Test Words |
|------|----------------------------|-----------------------------|------------|
| ာ (U+102C) | 0 / 50 | Never | ကာ, သာ |
| ါ (U+102B) | 0 / 50 | For **tall‑AA letters**: ခ ဂ င ဒ ပ မ ဝ | ခါ, ငါ, မာ |
| း (U+1038) | 0 / 20 | n/a | ကား, သား |
| ၊ (U+104A) | 100 / 200 | n/a | punctuation |
| ။ (U+104B) | 100 / 200 | n/a | punctuation |

**Word‑space conventions (justification):**
- Standard inter‑word space: **250–300 units** (0.25–0.30 em)
- Minimum: **180 units**
- Maximum: **450 units**
- Diacritics stay fixed to their base consonants during justification.

---

## 8. 30 "Torture Test" Words (Simple → Hardest)

1. က  
2. ကံ  
3. က့  
4. ကု  
5. ခု  
6. နု (descender side‑form)  
7. ရု (descender side‑form)  
8. ကျု (medial ya + vowel under leg)  
9. မျူ  
10. ကြို (medial ra + ိ + ု)  
11. ကြွ (medial ra + wa)  
12. ခြေ  
13. ကြီ (tall wrap variant)  
14. က္က (homogeneous stack)  
15. က္ခ  
16. ဂ္ဂ  
17. ဂ္ဃ  
18. ဋ္ဌ (special lower form)  
19. န္ဓ (special lower form)  
20. သင်္ဘော (kinzi + anusvara)  
21. သင်္ကြီ (kinzi + ီ)  
22. ကိံ (anusvara + ိ stacking)  
23. သိံ  
24. ကုံ့ (ု + ့ stacking)  
25. ဗုဒ္ဓ (multiple stacks)  
26. မြွှေ (medial ra + wa + vowel)  
27. ကျွန်ုပ် (medial ya + kinzi + vowel)  
28. ကြိုး (medial ra + ု + tone)  
29. ကမ္ဘာ (stack + tall‑AA)  
30. သင်္ဃာ (kinzi + stack + tall‑AA)

---

## 9. Language‑Specific Differences (Burmese, Mon, Shan, S'gaw Karen)

| Feature | Burmese | Mon | Shan | S'gaw Karen |
|---------|---------|-----|------|-------------|
| **Vowel marks** | Standard UTN #11 | Same as Burmese | Different Shan vowel set (v_shan) | Different S'gaw Karen vowel set (v_sk) |
| **Medial signs** | `ျ` allowed after any consonant | `ျ` only after mon_con | `ျ` only after sh_con | `ျ` only after sk_con |
| **Kinzi (င်္)** | Standard `<U+1004, U+103A, U+1039>` | Special `S_Mon4` sequence | Not used | Not used |
| **Virama (`္`)** | Used for stacking | Must follow mon_con + be followed by mon_con | Not specified | Not specified |
| **Asat (`်`)** | Cannot follow medials except S_Sh4 | Not specified | Must follow sh_con | Must follow sk_con |
| **Tone marks** | Standard (`း`) | Same as Burmese | Shan‑specific tone signs | S'gaw Karen‑specific tone marks |
| **Digits** | ၀၁၂၃၄၅၆၇၈၉ | Same as Burmese | ႐႑႒႓႔႕႖႗႘႙ | Same as Burmese |
| **Punctuation** | Standard Myanmar | Same as Burmese | Shan‑specific | S'gaw Karen‑specific |

**Implementation advice:** Use language‑tagged shaping (e.g. `lang=my`, `lang=mnw`, `lang=shn`, `lang=ksw`) to switch between these behaviours. Padauk and Noto Sans Myanmar already support these extended blocks.

---

## 10. Final Implementation Checklist

- [ ] Vowel ု/ူ class‑based horizontal positioning (wide, narrow, descender)
- [ ] Side‑form for descender letters (နု, ရု)
- [ ] Medial ya: vowels go *under* the ya leg
- [ ] Medial ra: narrow vs wide wrap, tall variant for ိ/ီ
- [ ] Stacked consonants: centered alignment, +50‑unit right shift for special lower forms
- [ ] Kinzi: y=+600, 0.75× following‑base width
- [ ] Anusvara/dot‑below stacking order (vertical separation 100–150 units)
- [ ] Tall‑AA rule: ါ replaces ာ for ခ ဂ င ဒ ပ မ ဝ
- [ ] Word‑space: 250–300 units (min 180, max 450)
- [ ] Language overrides for Mon, Shan, S'gaw Karen

---

**References:** UTN #11, Microsoft Myanmar Script Spec, Padauk & Noto Sans Myanmar observed behaviour.