# Professional Coaching Competency Rubric

This rubric guides consistent assessment of meeting performance across 7 executive competencies.

## Rating Levels

- **strong** (🟢): Demonstrated clearly and effectively; at or above expected level for role
- **developing** (🟡): Showed evidence but room to grow; needs refinement or consistency
- **not_observed** (⚪): Not relevant to this call type or not demonstrated

## Competencies

### 1. Strategic Thinking & Vision

**What to look for:**
- Connects dots across different initiatives/partnerships
- Sees implications beyond immediate problem
- References long-term goals or market trends
- Identifies patterns or opportunities others might miss

**Strong examples:**
- Connected pricing pressure to broader strategy shift
- Anticipated stakeholder objections before they surfaced
- Identified cross-functional implications proactively

**Developing examples:**
- Strategic insights present but not acted upon
- Sees patterns but doesn't translate to decisions
- Focuses on tactics without tying to broader vision

### 2. Executive Presence

**What to look for:**
- Confidence in delivery (even when uncertain)
- Credibility-building language
- Commands attention without dominating
- Handles pushback with composure

**Strong examples:**
- Reframed difficult conversation confidently
- Used data/examples to back assertions
- Stayed calm when challenged

**Developing examples:**
- Hedges too much ("I think maybe we could...")
- Defers to others' expertise when should lead
- Loses composure under pressure

### 3. Stakeholder Management

**What to look for:**
- Builds relationships intentionally
- Navigates competing interests
- Seeks win-win outcomes
- Demonstrates empathy for stakeholder perspectives

**Strong examples:**
- Recognized others' constraints without becoming defensive
- Proposed solutions that address multiple concerns
- Proactively managed expectations

**Developing examples:**
- Reactive rather than proactive communication
- Focuses on own goals without stakeholder perspective
- Misses cues about stakeholder priorities

### 4. Leading Through Ambiguity & Change

**What to look for:**
- Comfortable with incomplete information
- Decisive despite uncertainty
- Adapts plans when new info emerges
- Keeps team/stakeholders steady during flux

**Strong examples:**
- Made clear decision despite uncertainty
- Shifted approach mid-call when initial framing didn't land
- Communicated confidence even when path unclear

**Developing examples:**
- Paralyzed by uncertainty; waits for perfect info
- Indecisive or changes mind frequently
- Communicates anxiety rather than steadiness

**Not observed:**
- Routine status calls
- Conversations without ambiguity or change

### 5. Emotional Intelligence

**What to look for:**
- Self-awareness (recognizes own reactions/biases)
- Empathy (reads others' emotions accurately)
- Regulation (manages emotions constructively)
- Social skills (builds rapport, influences positively)

**Strong examples:**
- Acknowledged feeling defensive, then reframed productively
- Recognized others' energy shifts and pivoted accordingly
- Used empathy techniques authentically, not mechanically

**Developing examples:**
- Aware of emotions but doesn't manage them well
- Struggles to read others' cues
- Empathy present but doesn't translate to action

### 6. Decision-Making

**What to look for:**
- Clarity on decision criteria
- Weighs options explicitly
- Commits decisively (doesn't waffle)
- Explains rationale clearly
- Adjusts when new data emerges

**Strong examples:**
- Clear, articulated decision with rationale
- Evaluated options during call and committed
- Considered objections before deciding

**Developing examples:**
- Takes too long to decide
- Makes decision but can't explain why
- Reverses decisions without new information

### 7. Delegation & Accountability

**What to look for:**
- Delegates appropriately (not micromanaging, not abdicating)
- Clear ownership assignments
- Holds self/others accountable
- Follows through on commitments

**Strong examples:**
- Owned action items explicitly
- Delegated with clear deadline and owner
- Checked on status of prior action items

**Developing examples:**
- Delegates but doesn't check progress
- Takes on too much personally
- Vague ownership ("someone should...")

**Not observed:**
- 1:1 coaching calls (no delegation opportunity)
- Solo work sessions

## Assessment Guidelines

### When to mark "not_observed"

- Competency genuinely not relevant to call type
  - Example: Delegation in a 1:1 coaching call with no team
  - Example: Leading through ambiguity in a routine status sync

### When to mark "developing" vs "strong"

- **Strong**: You'd point to this as an example for others; clearly effective
- **Developing**: Present but needs work; you'd coach on it

### Avoid "all strong" or "all developing"

- Most calls will have a mix
- If everything is strong, you're likely grading on presence rather than excellence
- If everything is developing, you may be holding to an unrealistic bar

### Use notes to show your work

Always include a specific example from the call in the notes field:
- ✅ "Connected partnership opportunity to upcoming RFP positioning (00:12:34)"
- ❌ "Good strategic thinking"

## Example Assessments

### Interview Call (All Competencies Observable)

```json
{
  "strategic_thinking": {
    "observed": true,
    "rating": "strong",
    "notes": "Connected personal experience to interviewer's challenges; saw beyond role to ecosystem opportunity"
  },
  "executive_presence": {
    "observed": true,
    "rating": "developing",
    "notes": "Confident in discussing experience but hedged on future vision; could be more definitive"
  },
  "stakeholder_management": {
    "observed": true,
    "rating": "strong",
    "notes": "Built rapport with interviewer; asked about their priorities before pitching ideas"
  },
  "leading_through_ambiguity": {
    "observed": true,
    "rating": "strong",
    "notes": "Interviewer asked about hypothetical market shift; outlined clear approach despite incomplete info"
  },
  "emotional_intelligence": {
    "observed": true,
    "rating": "strong",
    "notes": "Read interviewer's energy shift when discussing partnerships; pivoted to deeper example"
  },
  "decision_making": {
    "observed": true,
    "rating": "developing",
    "notes": "Took long time to answer 'where do you see yourself in 3 years'; could be more decisive"
  },
  "delegation_accountability": {
    "observed": false,
    "rating": "not_observed",
    "notes": "No delegation opportunity in interview context"
  }
}
```

### 1:1 Coaching Call (Limited Scope)

```json
{
  "strategic_thinking": {
    "observed": true,
    "rating": "strong",
    "notes": "Connected immediate challenge to broader positioning strategy"
  },
  "executive_presence": {
    "observed": true,
    "rating": "developing",
    "notes": "Confident in coaching setting but could project more authority in difficult scenarios"
  },
  "stakeholder_management": {
    "observed": true,
    "rating": "strong",
    "notes": "Recognized others' constraints; sought collaborative solution rather than adversarial"
  },
  "leading_through_ambiguity": {
    "observed": false,
    "rating": "not_observed",
    "notes": "Coaching call had clear context; no ambiguity to navigate"
  },
  "emotional_intelligence": {
    "observed": true,
    "rating": "strong",
    "notes": "Showed vulnerability discussing challenge; practiced empathy technique authentically"
  },
  "decision_making": {
    "observed": true,
    "rating": "strong",
    "notes": "Clear decision to shift strategy; articulated action plan"
  },
  "delegation_accountability": {
    "observed": false,
    "rating": "not_observed",
    "notes": "No delegation opportunity in 1:1 coaching"
  }
}
```
