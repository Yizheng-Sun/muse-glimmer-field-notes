# Real-world daily-task candidates for Muse Glimmer

Research date: **11 October 2026**. Status: **research and proposed experiments; no daily-task inference runs performed**.

This collection contains **15 tasks from nine firsthand blog posts and Reddit threads**. They cover personal administration, reading, learning, writing, household coordination, and occasional planning. Some recur weekly or when an event arises rather than every day.

The source descriptions below are short paraphrases of what their authors report. **Input sizes, prompts, acceptance checks, difficulty variations, priorities, and reader takeaways are our proposed adaptations.** The reports establish plausible user needs; they do not independently verify performance or establish that Glimmer can complete these tasks.

## How the sources were selected

- Prefer an author describing their own use, with a concrete task and output, over vendor lists of possible use cases.
- Include accounts of friction and failure, not only successful demos.
- Include several needs beyond the researcher's morning briefing and writing workflow already planned in this repository.
- Use completed or currently used workflows as origins. Sajal Sharma's apartment-hunting and career-monitoring ideas are explicitly future extensions, so they are not included as demonstrated workflows.
- Read both named sections of blog posts and the relevant original posts/comments in Reddit threads. A comment is attributed to its commenter rather than to the original poster.
- This is a targeted convenience sample, not a survey of task popularity. It does not establish which tasks most users want.

All nine source URLs were opened during this research. Dates below are publication dates shown on the page where available. Relative Reddit ages are retained as displayed; they are not converted into guessed calendar dates.

## Source ledger

| Source | Author and date | Firsthand account and limits |
| --- | --- | --- |
| S01 — [A week with a personal OpenClaw assistant](https://sajalsharma.com/posts/openclaw-experiments/) | Sajal Sharma; 16 February 2026 | Describes schedule reviews, article capture, and learning quizzes. Reports duplicate email handling and inconsistent workflow adherence after changing models. Value remains an open question in the account. |
| S02 — [Hermes for research and writing](https://guochengqian.github.io/blog/hermes-agent/) | Gordon Guocheng Qian; 18 May 2026 | Describes personalized reading briefs and iterative blog drafting with local saved outputs. A usage narrative, without independent outcome measurements. |
| S03 — [First month with Hermes](https://kennytrinh.com/blog/from-chatbot-to-co-worker) | Kenny Trinh and Kira; 14 June 2026 | Describes invite monitoring and converting recordings into learning material. Interview preparation began in Claude Projects. Material extraction required iteration rather than a perfect first output. |
| S04 — [A personal AI operations layer](https://zejiantan.com/blog/personal-assistant) | Zejian Tan; 18 July 2026 | Describes scheduled consolidation of rough task logs into an Obsidian daily note. The model in this setup uses an external provider; a local agent host does not establish local inference. |
| S05 — [Household coordination account](https://www.reddit.com/r/AI_Agents/comments/1udd09j/ai_agents_feel_one_step_away_from_a_real_personal/) | u/user_malex; displayed age 3 months | Describes collecting school/activity messages into a family calendar. The author also promotes their own product in a comment; treat this as a builder's self-report. |
| S06 — [Cowork users' practical workflows](https://www.reddit.com/r/ClaudeAI/comments/1rn9ojd/what_are_your_best_cowork_examples_use_cases/) | Original poster u/Marathon2021 and commenter u/artfuldawdg3r; displayed age 7 months | The original poster describes receipt collection and weekly expense reports. The commenter describes preparing meeting briefs from prior notes. These are separate user reports within one thread. |
| S07 — [Google Drive reorganization field report](https://www.reddit.com/r/ClaudeAI/comments/1sjn6eu/i_spent_4_hours_getting_claude_cowork_to/) | u/bigcowdanny; displayed age 6 months | Describes reorganizing 3,700 files and substantial filesystem/integration trouble, despite useful classification and planning. Claims are the author's assessment. |
| S08 — [Meal-planning user discussion](https://www.reddit.com/r/ChatGPT/comments/1ma9c4n/ive_been_using_chatgpt_every_day_to_plan_my_meals/) | u/repjerker; displayed age 1 year | The original poster describes weekly meal planning. A commenter reports a leftovers chronology mistake. Health and weight-loss claims are outside this experiment's scope. |
| S09 — [Planning a family road trip with Hermes](https://daveswift.com/hermes-road-trip/) | Dave Swift; 20 July 2026 | Describes itinerary revision around reservations and driving limits; the first plan was overpacked. The page discloses affiliate links, and its model calls use cloud APIs. |

## Candidate overview

Priority is our judgment about experiment feasibility and usefulness for a practical blog, not a measured popularity ranking. **First batch** identifies four complementary tasks. **Alternate** means a useful replacement or later extension. **Later** means more integration, subjective grading, or preparation.

| ID | Task | Frequency | Source | Proposed delivery | Priority |
| --- | --- | --- | --- | --- | --- |
| D01 | Check whether today's schedule is realistic | Daily | S01 | A conflict and capacity briefing | Alternate |
| D02 | Capture an article in a usable reading notebook | Per article | S01 | A source-linked Markdown note and index entry | First batch |
| D03 | Turn recent learning notes into a recall quiz | Weekly | S01 | Questions, answer key, and source pointers | Alternate |
| D04 | Find recent research worth reading for a specific interest | Daily/weekly | S02 | A short, dated reading shortlist | Later |
| D05 | Turn rough notes into a draft and apply editorial feedback | Per draft | S02 | A saved, revised blog draft | Alternate |
| D06 | Reconcile changed and cancelled meeting invitations | As messages arrive | S03 | Updated event records and a change summary | First batch |
| D07 | Turn a long training transcript into review materials | Per lesson | S03 | Topic notes and a review pack | Alternate |
| D08 | Prepare grounded interview questions | Per interview | S03 | A job-relevant question sheet | Later |
| D09 | Preserve unfinished work for the next day | Daily | S04 | Daily note, open tasks, and next-session handover | First batch |
| D10 | Extract school/activity actions from group messages | Daily | S05 | Events, preparation tasks, and conflicts | Alternate |
| D11 | Plan meals and consolidate a shopping list | Weekly | S08 | A practical meal schedule and grocery list | Alternate |
| D12 | Assemble an expense report from scattered receipts | Weekly | S06 original post | Itemized records, totals, and receipt references | First batch, with input-path preflight |
| D13 | Organize a messy folder without losing its contents | Periodically | S07 | Reorganized copied files and a move manifest | Alternate |
| D14 | Build and revise a feasible trip itinerary | Per trip | S09 | A reservation-aware itinerary | Later |
| D15 | Prepare for a meeting using earlier relevant notes | Per meeting | S06 comment | A concise preparation brief | Alternate |

## Proposed experiments

### D01 — A realistic daily schedule

**Origin:** S01, Productivity: the author checks calendar commitments and task workload.

**Our test:** Supply a calendar export, task list, durations, and available working hours. Ask Glimmer to save a briefing that identifies collisions and work exceeding available time, then suggests a feasible subset of tasks.

**Check:** Every commitment retains its actual time; known overlaps and capacity excesses are identified; proposed tasks fit around fixed events. Missing duration estimates remain explicit uncertainties.

**Variation:** Move an appointment or remove a duration estimate. **Setup:** Low with supplied files. **Reader takeaway:** How to prepare inputs for a useful capacity check.

### D02 — Article capture with durable notes

**Origin:** S01, Setup: the author sends articles to save and summarize.

**Our test:** Use three public articles on subjects you actually follow. For each, ask Glimmer to retrieve the content, save a short note with the source URL and supported takeaways, and update a reading index. Submit one URL twice.

**Check:** Claims match retrieved content; the note and index exist at the requested paths; the duplicate produces one logical index entry. Advice is extracted only when the source supports it.

**Variation:** An inaccessible page must produce an explicit retrieval failure. Supplying its text afterwards is a separately labelled adaptation. **Setup:** Low to medium, depending on retrieval tools. **Reader takeaway:** How to maintain a reading notebook without repeatedly filing the same article.

### D03 — Recall questions from learning notes

**Origin:** S01, Studying: the author receives recurring quizzes on material already studied.

**Our test:** Supply three short learning notes. Ask Glimmer to save six questions, a separate answer key, and file/section references supporting each answer. Answer the questions before opening the key.

**Check:** Answers are supported; questions cover more than one note; the questions do not reveal their own answers. Grade factual accuracy separately from your subjective assessment of learning value.

**Variation:** Correct one source note and regenerate the affected material. **Setup:** Low. **Reader takeaway:** How to turn passive reading into a reusable recall exercise.

### D04 — Research reading shortlist

**Origin:** S02, 8am briefing: the author wants source-linked reading selected for their research interests.

**Our test:** Define a topic, date window, and inclusion criteria. Ask Glimmer to find three relevant primary sources, save a dated shortlist, and explain each selection using the retrieved material.

**Check:** Links, dates, and titles are correct; items meet the topic and date constraints; explanations accurately describe their sources. Record the candidate set and rejected items so selection can be reviewed.

**Variation:** Add a popular but irrelevant item and an older item resurfaced recently. **Setup:** Medium; web/search availability matters. **Reader takeaway:** How to make a digest selective and verifiable. Frozen pages test synthesis; live search additionally tests discovery and freshness.

### D05 — Drafting and revision without changing the evidence

**Origin:** S02, Blogging: rough notes become a saved draft followed by editorial revision.

**Our test:** Supply your own rough notes, evidence links, and style preferences. Request a local draft. Then issue three concrete edits, including removing a claim that lacks support.

**Check:** Required points and evidence limits survive; all three edits appear in the final file; removed material is absent. Score factual preservation and requested edits objectively, with voice/readability judged separately.

**Variation:** Ask for a light polish after an earlier structural rewrite. **Setup:** Low. **Reader takeaway:** How to collaborate on a draft while preserving factual claims and intended voice.

### D06 — Meeting invitation changes

**Origin:** S03, Email and calendar monitoring: the author follows a narrow stream of invitations.

**Our test:** Supply exported messages and an initial event file. Include one new invitation, one time change, a cancellation, and a duplicate. Ask Glimmer to update a local event table and save a change summary.

**Check:** Events are matched by stable identifiers where available; the latest valid updates win; cancelled meetings are removed or marked cancelled; no duplicate remains. Preserve timezones and distinguish message arrival from event-update order.

**Variation:** Deliver a superseded invitation after its newer revision. **Setup:** Low with files; live inbox/calendar integration is a separate later stage. **Reader takeaway:** How to turn invitation changes into a reliable personal agenda.

### D07 — Training material from a long transcript

**Origin:** S03, Training material extraction: the author iteratively turns recordings into review resources.

**Our test:** Start with a timestamped transcript of material you can legally use. Ask Glimmer to create topic notes, a glossary, and review questions with timestamp references.

**Check:** Important concepts survive section boundaries; references point to the supporting passages; terminology is consistent; uncertain transcription is flagged rather than silently rewritten.

**Variation:** Include a concept explained across two transcript sections. **Setup:** Low with a supplied transcript; audio transcription is a separate tool stage. **Reader takeaway:** How to convert a recording transcript into navigable study material. This adaptation does not test speech recognition.

### D08 — Interview preparation from a CV and role

**Origin:** S03, Earlier workflow: the author used candidate documents to prepare interviews and follow-up reports.

**Our test:** Supply a fictional or consented CV and a role description. Request six questions linked to role requirements and specific claims or gaps in the documents.

**Check:** Each question is job-relevant and traceable; unsupported experience is not asserted; missing evidence is phrased as a question. The output is a preparation aid, with no hiring decision or ranking in the task.

**Variation:** Two similarly named projects with different responsibilities. **Setup:** Low for text input; requires careful human judgment of question quality. **Reader takeaway:** How to prepare evidence-based follow-up questions.

### D09 — Evening handover and next-day continuity

**Origin:** S04, Nightly workflow: rough task logs are consolidated into a durable daily note.

**Our test:** Give Glimmer a day of timestamped activity notes and an initial task file. Ask it to save completed work, decisions, open tasks, and tomorrow's starting point. Start a fresh session with only those saved records, then ask what to resume.

**Check:** Completed and unfinished items are classified correctly; superseded decisions are resolved; the next session recovers the actual open work. Inspect the saved files, not only the agent's final message.

**Variation:** A task changes from postponed to completed late in the day. **Setup:** Low; repeat across three days to observe state maintenance. **Reader takeaway:** How to preserve work context across sessions.

### D10 — Actions hidden in school and activity messages

**Origin:** S05, Original post and author's follow-up: multiple group chats contain household actions and calendar changes.

**Our test:** Use anonymized or clearly synthetic message exports modelled on this need. Include event announcements, chatter, required items, a deadline, a cancellation, and two conflicting family commitments. Ask Glimmer to save events and a preparation checklist with message references.

**Check:** All action-bearing messages are captured; chatter creates no invented tasks; cancellations replace earlier plans; conflicts are flagged. Relative dates use the supplied message date and timezone.

**Variation:** A follow-up changes a venue but not the time. **Setup:** Low with exports; live group monitoring is separate. **Reader takeaway:** How to extract practical obligations from noisy messages.

### D11 — Meals and shopping that fit available ingredients

**Origin:** S08, Original post: weekly meal planning reduces recipe-search effort. A thread reply describes leftovers being scheduled before they exist.

**Our test:** Supply pantry quantities, preferences, serving counts, available cooking time, and a fixed price list. Ask Glimmer to save a five-day plan and consolidated shopping list. Treat this as cooking logistics rather than medical or nutritional advice.

**Check:** Listed preferences and exclusions hold; portions and quantities reconcile; pantry items are deducted; total spend is calculated from supplied prices; leftovers appear after preparation.

**Variation:** An extra guest and a shorter cooking window on one day. **Setup:** Low with text. **Reader takeaway:** How to turn household constraints into a usable shopping plan. Provided prices do not test current supermarket pricing or checkout.

### D12 — Receipt-to-expense report

**Origin:** S06, u/Marathon2021's original post: receipts accumulate into a categorized weekly report.

**Our test:** Supply a small receipt folder, category rules, and a reporting period. Ask Glimmer to save itemized records and a summary with receipt references. Include a duplicate, an out-of-period receipt, and a partly unreadable field.

**Check:** Dates, merchants, currencies, and amounts match the receipts; duplicates are not double-counted; categories follow supplied rules; totals reconcile separately by currency; unreadable values remain unknown.

**Variation:** A negative refund and a mixed-currency receipt. **Setup:** Low with extracted text; medium with images/PDFs. Verify the deployed image/document tool path first. If external OCR or supplied extraction is used, name it and grade extraction separately. **Reader takeaway:** How to assemble an auditable expense report without trusting guessed numbers.

### D13 — Folder organization with a verifiable result

**Origin:** S07: file classification was useful, while actual filesystem execution caused trouble.

**Our test:** Copy 30–50 representative files into an experiment folder. Ask Glimmer to propose a grouping, implement it in the copy, and save a manifest linking original and final paths. Predefine category rules and an ambiguous-file holding folder.

**Check:** Every input file is accounted for; byte hashes are unchanged; names do not collide; placement follows the rules; the manifest matches the actual filesystem. Re-running should not create repeated nesting or new copies.

**Variation:** Duplicate filenames and a file whose contents contradict its name. **Setup:** Low to medium, depending on file readers. **Reader takeaway:** How to verify that folder cleanup preserves files. A copied local folder does not establish cloud-drive integration reliability.

### D14 — Feasible itinerary with reservations and revisions

**Origin:** S09: the author iterates on an overpacked road-trip plan around existing bookings.

**Our test:** Supply a short trip, reservation windows, selected stops, opening hours, travel-time estimates, and a maximum daily driving time. Ask Glimmer to save a feasible itinerary and revise it after one stop becomes unavailable.

**Check:** Fixed reservations survive; travel, activities, breaks, and check-in times fit; drive limits hold; the unavailable stop disappears. References distinguish supplied facts from live-checked information.

**Variation:** An attraction closes earlier than the proposed arrival. **Setup:** Low with a frozen fact pack; higher with live maps and availability. **Reader takeaway:** How to check itinerary feasibility. No purchase or booking is part of this experiment; supplied estimates do not establish live availability.

### D15 — Meeting preparation from prior notes

**Origin:** S06, comment by u/artfuldawdg3r: upcoming meetings are paired with relevant recent conversations.

**Our test:** Supply an upcoming meeting, attendee list, and six dated meeting notes, including irrelevant notes. Ask Glimmer to save a one-page brief with prior decisions, open commitments, changes, and suggested questions, each linked to supporting notes.

**Check:** Relevant context is selected; stale decisions are identified; open commitments have the correct owners; irrelevant or similarly named projects are excluded.

**Variation:** A later note reverses an earlier decision. **Setup:** Low with text files. **Reader takeaway:** How to recover meeting context without rereading every previous note.

## Recommended first batch

Start with **D02 article capture, D06 invitation changes, D09 evening handover, and D12 expense reports**. They produce artifacts a reader can use immediately and exercise different parts of an agent workflow: retrieval, updating structured state, continuity across sessions, and extraction/arithmetic. D06 and D10 overlap, so initially choose one rather than treating them as independent coverage of very different capabilities.

Use **D13 folder organization** in place of D12 if receipt extraction requires a tool path that is not ready. D01 is a natural later scheduled workflow; D04 and D14 introduce more external-data uncertainty. D05 is directly relevant to your blog but has a larger subjective-quality component.

This is a recommendation, not a change to the four W01–W04 workflows in `PLAN.md`. D01 corresponds broadly to W01, D02 to W02, D05 to W03, and D09 to W04. The D identifiers preserve the research candidate pool independently of whichever experiments you select.

## Small, repeatable evaluation protocol

1. **Prepare a normal case, an update case, and a problematic-input case for each selected task.** Use your own material where possible, anonymize the publishable example, and retain the original input snapshot privately. Label synthetic fixtures as synthetic; report a live user trial separately from controlled fixtures.
2. **Write the expected facts and success criteria before the model runs.** A useful final answer is insufficient if the requested output file is absent, outdated, or wrong.
3. **Freeze the working Glimmer/Hermes setup.** Record model artifact, quantization, runtime, tools, context, generation settings, and supported reasoning configuration. Begin with one configuration rather than another large tuning matrix.
4. **Reset the workspace for each attempt.** Start independent tasks in fresh sessions. For D09, deliberately preserve only the selected state files between days; do not carry an old chat transcript into the continuity test.
5. **Attempt each fixture twice from its initial state.** Four tasks × three fixtures × two attempts gives 24 controlled attempts. This is a small demonstration sample, not a general reliability estimate. Log all attempts and any assistance. Keep a three-day live-use diary alongside it if you want to write about daily usefulness.
6. **Use a fixed budget**, for example 15 minutes and a fixed recorded tool-iteration allowance. Keep autonomous success, assisted success, failed, and unavailable outcomes separate. A tool failure can explain an unsuccessful end-to-end run without becoming evidence of a model reasoning failure.
7. **Measure both usefulness and friction:** factual errors, omissions, correct saved artifacts, human interventions, active preparation/review/correction time, and elapsed agent time. Measure a manual baseline on comparable material and state any practice/order effects. Keep one-time setup and maintenance costs separate; show net active time saved after repeated input preparation and correction.
8. **For a model comparison**, use the same inputs, tools, state resets, and checks. Local-hosted agents using cloud models in the source accounts are not evidence of Glimmer's local performance.

The blog should let a reader reproduce a successful workflow or decide to avoid a workflow that still costs more effort than it saves. Publish the prompt, a permitted sample input, actual output, the checking method, and observed failures. A "How to" title is appropriate once the procedure works; a "Can it?" title fits mixed results.

## Example first request: D02

This is an original proposed prompt, not a copied source prompt. Replace the placeholders with prepared paths and an article you have chosen.

```text
Capture this article in my reading notebook: <URL>.

Read preferences.md and reading/index.md first. Retrieve the article,
then save a Markdown note under reading/notes/ containing its title,
source URL, a concise faithful summary, and useful takeaways supported
by the article. If it contains no practical advice, say so.

Update reading/index.md with a link to the saved note. If this URL is
already recorded, update the existing note instead of duplicating it.
If retrieval fails, record the failure and do not invent article content.

Verify that the saved note and index link exist. Report the paths and
anything I need to review.
```

Prepare the empty index and preferences file before running. The request tests retrieval and saved artifacts; a supplied-text fallback tests a narrower workflow and should receive its own result.
