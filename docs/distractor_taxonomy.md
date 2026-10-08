# Distractor Taxonomy & Semantic Failure Analysis

**Phase:** Phase 5 — Reliability Under Distribution Shift, Abstention & Generalization  
**Document Status:** FORMAL RESEARCH TAXONOMY  
**Date:** October 7, 2026  

---

## 1. Motivation

A core vulnerability of entity-grounded intent classifiers is **lexical anchoring**: the assumption that mentioning a domain-specific entity implies an intent to query that domain's operational database.

This taxonomy formalizes ten distinct classes of semantic distractors—inputs that contain domain keywords but express non-operational or unrelated user intents.

---

## 2. Taxonomy Classes

### 1. `DOMAIN_NOUN_ONLY`
- **Definition:** The input consists of a bare domain noun phrase or conversational fragment without a predicate or verb phrase.
- **Example:** *"The customer."* / *"Tickets please."*
- **What Makes It Difficult:** The entity parser sees 100% domain relevance but zero operational context.
- **Expected Behavior:** `DIRECT` or `ABSTAIN` (Prompt for clarification).
- **Risk if Misclassified:** Executes arbitrary default database query (`status=active`), returning unrequested PII.
- **Abstention Appropriate?** **Yes.** High ambiguity justifies asking the user what they want.

---

### 2. `DOMAIN_NOUN_WITH_SENTIMENT`
- **Definition:** The domain noun is the subject or object of an evaluative sentiment statement or praise.
- **Example:** *"Customer feedback was overwhelmingly positive during the product launch."*
- **What Makes It Difficult:** Contains technical tokens (`customer`, `feedback`), but the speech act is an informative observation, not a database query.
- **Expected Behavior:** `DIRECT` (Conversational response: *"That's great to hear! How can I assist further?"*).
- **Risk if Misclassified:** Triggers a CRM table scan and reports raw customer rows, breaking conversational flow.
- **Abstention Appropriate?** **Yes.** If uncertain whether it is a sentiment or query, abstaining prevents tool invocation.

---

### 3. `DOMAIN_NOUN_IN_STORY`
- **Definition:** Domain vocabulary appears within a personal narrative, past-tense anecdote, or travel story.
- **Example:** *"I bought a concert ticket for tomorrow night performance."*
- **What Makes It Difficult:** Polysemy of the word `ticket` (music/event ticket vs. IT support ticket) combined with past-tense narrative framing.
- **Expected Behavior:** `DIRECT`.
- **Risk if Misclassified:** Discloses internal IT support ticket queue data to a user asking about a concert.
- **Abstention Appropriate?** **Yes.**

---

### 4. `DOMAIN_NOUN_IN_COMPARISON`
- **Definition:** Domain nouns appear in an analogy, athletic comparison, or cultural contrast.
- **Example:** *"Our active volunteers did better than the customer support team at the 5k run."*
- **What Makes It Difficult:** High lexical density: contains `active`, `customer`, and `support` in one sentence!
- **Expected Behavior:** `DIRECT`.
- **Risk if Misclassified:** Triggers multiple contradictory tool calls or defaults to CRM/Support mistakenly.
- **Abstention Appropriate?** **Yes.**

---

### 5. `DOMAIN_NOUN_IN_UNRELATED_REQUEST`
- **Definition:** An imperative request is made, but it targets an external task rather than the assistant's internal database tools.
- **Example:** *"Can you order two movie tickets online for the eight o clock show"* / *"Help me draft an email to a customer"*
- **What Makes It Difficult:** It contains an imperative verb (`order`, `draft`) AND domain nouns (`tickets`, `customer`), but the operational domain is non-internal.
- **Expected Behavior:** `DIRECT` (Respond conversationally or explain tool limits).
- **Risk if Misclassified:** Executes `get_support_tickets` when the user asked to purchase cinema tickets.
- **Abstention Appropriate?** **Yes.**

---

### 6. `MULTIPLE_DOMAIN_TERMS`
- **Definition:** Mentions entities from multiple distinct tools simultaneously in a social or non-operational context.
- **Example:** *"Both the customer and the support agent attended the annual company gala."*
- **What Makes It Difficult:** Triggers multi-domain ambiguity detection or false tool selection cross-talk.
- **Expected Behavior:** `DIRECT`.
- **Risk if Misclassified:** Arbitrarily picks one domain over another.
- **Abstention Appropriate?** **Yes.**

---

### 7. `CROSS_DOMAIN_CONTEXT`
- **Definition:** Domain vocabulary is used in an entirely different industry or academic discipline (zoology, geology, psychology).
- **Example:** *"A support dog brings immense comfort to anxious hospital patients."* / *"The active volcano erupted yesterday."*
- **What Makes It Difficult:** `support dog` $\ne$ `support ticket`; `active volcano` $\ne$ `active customer`.
- **Expected Behavior:** `DIRECT`.
- **Risk if Misclassified:** Queries user databases in response to animal or geology discussions.
- **Abstention Appropriate?** **Yes.**

---

### 8. `IMPLICIT_OPERATION`
- **Definition:** The user expresses a speculative wish or vague contemplation without explicitly requesting action.
- **Example:** *"It would be wonderful to know what customers think about our branding."*
- **What Makes It Difficult:** Bridges the boundary between opinion and potential query.
- **Expected Behavior:** `DIRECT` or `ABSTAIN` (Suggest operational query: *"Would you like me to look up customer records?"*).
- **Risk if Misclassified:** Prematurely executes tools on mere musings.
- **Abstention Appropriate?** **Yes.**

---

### 9. `NON_OPERATIONAL_QUESTION`
- **Definition:** An explicit question asking for history, philosophy, or general knowledge about a domain concept.
- **Example:** *"What is the historical origin of customer loyalty programs?"*
- **What Makes It Difficult:** It is an interrogative question containing `customer`, but it seeks factual knowledge from the LLM, not records from the SQL connector.
- **Expected Behavior:** `DIRECT`.
- **Risk if Misclassified:** Replaces an informative LLM explanation with a tabular list of customer names.
- **Abstention Appropriate?** **Yes.**

---

### 10. `CONVERSATIONAL_STATEMENT`
- **Definition:** Idiomatic remarks, colloquialisms, or abstract praise.
- **Example:** *"She showed great enthusiasm for customer satisfaction."*
- **What Makes It Difficult:** Grammatically complete sentence with `customer` as an adjectival modifier.
- **Expected Behavior:** `DIRECT`.
- **Risk if Misclassified:** False positive tool invocation.
- **Abstention Appropriate?** **Yes.**
