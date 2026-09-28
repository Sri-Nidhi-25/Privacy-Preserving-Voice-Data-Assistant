# Privacy Threat Model — Voice Obfuscation Layer

## 1. System Context & Assets

The Privacy-Preserving Voice Data Assistant allows enterprise employees to query internal databases (CRM, support tickets, usage analytics) via natural spoken voice.

### Protected Asset
- **Speaker Identity:** The acoustic identity, biometric voiceprint, and pitch/timbre characteristics of the human speaker submitting the voice query.

### Unprotected (Out of Scope) Assets
- **Semantic Disclosure:** If the user speaks their own name or unique identifiers (e.g., *"Hi, this is Alice from Accounting"*), acoustic voice obfuscation cannot prevent textual identification.
- **Transcript Content:** Content of the query itself is forwarded to the language model for database retrieval.

---

## 2. Adversary Profile & Threat Matrix

### Adversary A: Passive Audio Eavesdropper
- **Access:** Intercepts audio payloads transmitted over the internal network or stored in temporary processing caches.
- **Goal:** Extract biometric voice embeddings (e.g. via x-vectors or d-vectors) to identify the specific employee who submitted the query.
- **Capability:** Possesses reference voice samples of employees (e.g., from recorded public company all-hands meetings or video calls).

### Adversary B: Curious Internal Database / Infrastructure Administrator
- **Access:** Direct access to raw database query logs and temporary audio files.
- **Goal:** Correlate specific queries (e.g., looking up VIP customer records or executive support tickets) to a specific individual.

---

## 3. Defense Mechanism: Voice Obfuscation

The pipeline enforces voice obfuscation **before** any storage or downstream processing:
1. **Naive Pitch Shift (`VoiceObfuscator`):** Resamples and shifts fundamental frequency ($F_0$) by $\pm 2$ to $\pm 6$ semitones using standard phase-vocoder / sinc interpolation.
2. **Formant-Preserving Obfuscation (`FormantPreservingObfuscator`):** Uses the WORLD vocoder (`pyworld`) to decompose the speech signal into:
   - Fundamental frequency ($F_0$)
   - Spectral envelope ($SP$)
   - Aperiodicity ($AP$)
   It modifies $F_0$ with random semitone shifting and micro-pitch jitter while preserving the spectral envelope, altering perceived pitch and identity while retaining phoneme intelligibility for Whisper STT.

---

## 4. Privacy Metric Definition

To measure acoustic privacy without fabricating artificial scores:
- **Acoustic Pitch Distance ($\Delta F_0$):** Mean absolute shift in fundamental frequency $F_0$ voiced frames between original and obfuscated audio.
- **Formant / Spectral Envelope Distortion:** Measures acoustic divergence from reference speaker profile.
- **Empirical De-anonymization Resistance:** High $\Delta F_0$ and high acoustic distortion increase the Equal Error Rate (EER) of speaker verification classifiers, reducing the adversary's cosine similarity between obfuscated queries and enrollment voiceprints.

---

## 5. Security & Privacy Limitations

1. **No Cryptographic Guarantees:** Voice obfuscation is an acoustic perturbation technique; it does not provide differential privacy or cryptographic zero-knowledge guarantees.
2. **Reversibility Consideration:** If a deterministic, fixed pitch shift is used with a known constant semitone value, an adversary with knowledge of the exact parameter could attempt to invert the shift. To mitigate this, `FormantPreservingObfuscator` introduces random micro-jitter.
3. **Residual Acoustic Biometrics:** Heavy obfuscation degrades intelligibility (increasing WER). The objective of the privacy-utility study is to determine the Pareto-optimal configuration that maximizes identity dissimilarity while minimizing transcription error.