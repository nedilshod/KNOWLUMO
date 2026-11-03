# CSCA Mathematics — proposed episode roadmap

**Working assumption:** CSCA = China Scholastic Competency Assessment. English-language channel; mathematics first, with physics and chemistry as separate future seasons. This is an independent learning resource, not affiliated with the exam organizer.

## Scope and sources

The four major modules below are a paraphrase of the **2025 Mathematics Examination Syllabus**. The individual episode titles and the breakdown into lessons are our teaching plan, not an official episode list, a promise of specific questions, or an official weighting. Verify the current syllabus and requirements for the intended university before publishing and again before the student's exam. The official PDF contains restrictions on reproduction; link to it rather than republishing it.

- Official syllabus, 2025 edition: https://csca.cn/files/CSCA%20Mathematics%20Examination%20Syllabus-2025.pdf (official site is outside this sandbox's outbound allowlist; we could not independently download it here).
- Secondary source explaining and linking the official document: https://csca.ai/blogs/csca-exam-mathematics-syllabus-2026 (accessed 2026-11-02).
- Additional syllabus summary: https://www.china-admissions.com/wp-content/uploads/2025/11/CSCA-Guidebook.pdf

Both summaries describe 48 single-answer questions in 60 minutes in Chinese or English, with 100 points total for mathematics. These details refer to the 2025 syllabus; confirm current rules. University and program requirements differ. There is no reliable basis here for promising a question distribution or guaranteeing a score.

## Season 1: Mathematics

### Module 1 — Sets and inequalities
1. Sets and notation: elements, membership, intersection and union **[pilot]**
2. Subsets, complements and Venn diagrams
3. Set-builder and interval notation
4. Inequality rules and number lines
5. Quadratic inequalities: roots and sign intervals
6. Rational inequalities: sign charts and excluded values
7. Mixed practice: sets and inequalities

### Module 2 — Functions
8. Functions: inputs, outputs and notation
9. Domain and range
10. Increasing and decreasing functions
11. Even and odd functions
12. Graphs and transformations (teaching support)
13. Power functions
14. Exponential functions
15. Logarithms and logarithmic functions
16. Exponential and logarithmic equations (practice)
17. Trigonometry: angles and the unit circle
18. Sine, cosine and tangent graphs
19. Trigonometric identities and equations (practice)
20. Arithmetic sequences: general term
21. Arithmetic sequences: sums
22. Geometric sequences: general term
23. Geometric sequences: sums
24. Derivatives: definition and rate of change
25. Derivatives: tangent slope and geometric meaning
26. Derivatives: simple applications and extrema
27. Mixed practice: functions and sequences

### Module 3 — Geometry and algebra
28. Coordinates, distance and lines
29. Line equations, parallel and perpendicular lines
30. Circle equations and properties
31. Ellipses: equations and properties
32. Hyperbolas: equations and properties
33. Parabolas: equations and properties
34. Vectors: coordinates and operations
35. Vectors: dot product and applications
36. Complex numbers: the imaginary unit and operations
37. Complex numbers: conjugates and modulus (practice)
38. Solid geometry: simple solids
39. Three-dimensional coordinates and distance
40. Mixed practice: geometry and algebra

### Module 4 — Probability and statistics
41. Classical probability and equally likely outcomes
42. Counting outcomes and probability practice
43. Mean and interpreting data
44. Variance and spread
45. Normal distribution: basic ideas
46. Mixed practice: probability and statistics

### Review
47. Mixed-topic timed practice, part 1
48. Mixed-topic timed practice, part 2 and common mistakes

Some lesson-level topics are helpful prerequisites or practice within broader syllabus headings; they are not individually guaranteed to appear. In particular, no specific calculus beyond the official broad description should be assumed without checking the current document. The order and number of lessons can change after feedback.

## Episode and design format

- 16:9 English narration. Start with a short learning goal; build intuition visually; work a concrete example; ask an original exam-style question; explain it; recap and point to the next lesson.
- Thumbnail system: dark navy background, teal episode number, short white topic title, gold accent; same layout for every episode. `render.py --cover-only --number 2 --title 'Subsets and Complements'` demonstrates the reusable cover generator.
- Episode 1 is a short **visual and voice pilot**, not a full-length complete lesson or a finished autonomous pipeline. It uses original examples, not official questions. The narration and visuals are arranged by scene rather than word-level timed captions.
- Human review before publication: mathematical correctness, readable formulas and audio, source dates, rights, and current exam rules. Do not imply affiliation or that the exercises are official.

## Production references investigated

- [OpenMontage](https://github.com/calesthio/OpenMontage): agent-guided production workflows with FFmpeg and composition options. AGPL-3.0. Reviewed documentation for workflow ideas; this pilot does not import or run OpenMontage code.
- [YouTube Automation Agent](https://github.com/darkzOGx/youtube-automation-agent): potential match for the requested YouTube agent; research, creation and review workflow. MIT. Requires setup and provider credentials for its full workflow. Reviewed documentation only; not installed, connected, run or used to publish. Ask for the exact repo link before integration.
- Repository branch `arena/4bf04829-youtube` has a Remotion speech-effects demo; other available branches include other projects. No branch called Isarina AI was found among the GitHub branches accessible on 2026-11-02. The intended project/branch needs clarification.
