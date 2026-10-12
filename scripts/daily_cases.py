"""Deterministic, synthetic fixtures inspired by the daily-task research.

Only files/web_files and phase prompts are supplied to an agent. Checks and
provenance stay on the reviewer side. No online user's private data is copied.
"""
from __future__ import annotations

import hashlib
import json

VARIANTS = ("normal", "update", "problem")
SOURCES = {
    "S01": "https://sajalsharma.com/posts/openclaw-experiments/",
    "S02": "https://guochengqian.github.io/blog/hermes-agent/",
    "S03": "https://kennytrinh.com/blog/from-chatbot-to-co-worker",
    "S04": "https://zejiantan.com/blog/personal-assistant",
    "S05": "https://www.reddit.com/r/AI_Agents/comments/1udd09j/ai_agents_feel_one_step_away_from_a_real_personal/",
    "S06": "https://www.reddit.com/r/ClaudeAI/comments/1rn9ojd/what_are_your_best_cowork_examples_use_cases/",
    "S07": "https://www.reddit.com/r/ClaudeAI/comments/1sjn6eu/i_spent_4_hours_getting_claude_cowork_to/",
    "S08": "https://www.reddit.com/r/ChatGPT/comments/1ma9c4n/ive_been_using_chatgpt_every_day_to_plan_my_meals/",
    "S09": "https://daveswift.com/hermes-road-trip/",
}
CATALOG = [
    ("D01", "Realistic daily schedule", "S01", "Supplied calendar and duration estimates; no live calendar"),
    ("D02", "Article capture", "S01", "Local synthetic HTTP articles; retrieval and saved notes, not open-web browsing"),
    ("D03", "Learning recall quiz", "S01", "Coverage and answer-key facts; pedagogical quality needs human review"),
    ("D04", "Research reading shortlist", "S02", "A frozen local feed; selection and freshness, not open-web discovery"),
    ("D05", "Blog drafting and revision", "S02", "Fact preservation and explicit edits; writing quality needs human review"),
    ("D06", "Meeting invitation changes", "S03", "Exported messages and local event records; no inbox/calendar integration"),
    ("D07", "Training review material", "S03", "Timestamped supplied transcript; no speech recognition"),
    ("D08", "Interview preparation", "S03", "Fictional CV and role; grounded coverage, not hiring decisions or question quality"),
    ("D09", "Evening handover", "S04", "Two fresh sessions sharing saved files; no live scheduling"),
    ("D10", "School-message action extraction", "S05", "Synthetic chat exports; no group-chat integration"),
    ("D11", "Meals and shopping", "S08", "Supplied recipes, pantry and prices; logistics, not nutrition or checkout"),
    ("D12", "Receipt expense report", "S06", "Supplied receipt text; no image OCR, PDF extraction or accounting advice"),
    ("D13", "Folder organization", "S07", "Copied local files; no cloud-drive integration"),
    ("D14", "Feasible trip itinerary", "S09", "Supplied travel times and opening hours; no live availability or booking"),
    ("D15", "Meeting preparation", "S06", "Supplied meeting notes; factual coverage, not subjective brief quality"),
]


def js(value):
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def phase(prompt, remove_before=(), provide_before=()):
    return {"prompt": prompt, "remove_before": list(remove_before), "provide_before": list(provide_before)}


def fixture(files, expected, prompt, *, phases=None, web=None, extra_checks=(), mutable=()):
    """The structured output is the objective contract, prose is also retained."""
    checks = [] if expected is None else [{"kind": "json", "path": "outputs/result.json", "expected": expected}]
    checks += [{"kind": "text", "path": "outputs/report.md", "min_chars": 80}, *extra_checks]
    return {"files": {p: v if isinstance(v, str) else js(v) for p, v in files.items()},
            "web_files": web or {}, "phases": phases or [phase(prompt)],
            "mutable_inputs": list(mutable), "checks": checks}


CONTRACT = """
Save the requested structured facts in outputs/result.json, as valid JSON with
exactly the documented fields. IDs refer to the supplied input records. Use
JSON null for unknown values; do not guess. Also save a useful human-readable
outputs/report.md (at least 80 characters). Check the final files before finishing.
The report's existence is checked, but its prose quality is not automatically scored.
"""


def schedule(v):
    moved = v == "update"
    events = [{"id": "E1", "start": "09:00", "end": "10:00"},
              {"id": "E2", "start": "10:30" if moved else "09:30", "end": "11:00" if moved else "10:30"},
              {"id": "E3", "start": "13:00", "end": "14:00"}]
    tasks = [{"id": "T1", "minutes": 150}, {"id": "T2", "minutes": 120},
             {"id": "T3", "minutes": None if v == "problem" else 60}]
    # E1+E2 union: normal 90, updated 90; E3 adds 60.
    expected = {"conflicts": [] if moved else [["E1", "E2"]], "available_minutes": 330,
                "known_task_minutes": 270 if v == "problem" else 330,
                "unknown_duration_ids": ["T3"] if v == "problem" else [],
                "over_capacity": False}
    # Problem case adds a fixed commitment to reveal a real capacity excess.
    if v == "problem":
        events.append({"id": "E4", "start": "15:00", "end": "17:00"})
        expected.update(available_minutes=210, over_capacity=True)
    return fixture({"inputs/calendar.json": events, "inputs/tasks.json": tasks}, expected,
        "Review the 09:00–17:00 working day. Overlaps occupy time only once. Report conflicts as pairs of event IDs, "
        "available_minutes, known_task_minutes, unknown_duration_ids, and over_capacity (known durations exceed available time). "
        "Do not invent durations. Explain how I should adjust my workload.")


def articles(v):
    days = 14 if v == "update" else 7
    web = {
        "/articles/backup.html": f"<h1>Backup routine</h1><p id='p1'>Keep {days} daily snapshots.</p><p id='p2'>Test a restore every 30 days.</p>",
        "/articles/reading.html": "<h1>Reading routine</h1><p id='p1'>Review notes after 2 days.</p><p id='p2'>Limit the reading inbox to 10 items.</p>",
    }
    expected = {"articles": [
        {"id": "backup", "url": "{{WEB}}/articles/backup.html", "snapshot_days": days,
         "restore_interval_days": 30, "citations": ["p1", "p2"]},
        {"id": "reading", "url": "{{WEB}}/articles/reading.html", "review_after_days": 2,
         "inbox_limit": 10, "citations": ["p1", "p2"]}],
        "failed_urls": ["{{WEB}}/articles/missing.html"] if v == "problem" else []}
    queue = ["{{WEB}}/articles/backup.html", "{{WEB}}/articles/reading.html", "{{WEB}}/articles/backup.html"]
    if v == "problem":
        queue.append("{{WEB}}/articles/missing.html")
    spec = ("Fetch each URL in inputs/queue.json. Save one Markdown note per successfully retrieved article under "
            "reading/notes/<id>.md and a reading/index.json using this shape: {\"entries\":[{\"id\":\"...\",\"path\":\"reading/notes/<id>.md\"}]}. "
            "Deduplicate by URL. outputs/result.json has articles (one object per successful URL, with the id, url, "
            "numerical facts and paragraph IDs from that page) and failed_urls. The backup article uses snapshot_days and "
            "restore_interval_days; reading uses review_after_days and inbox_limit; each uses citations. "
            "Never fill in an unavailable page from your knowledge.")
    result = fixture({"inputs/queue.json": queue, "reading/index.json": {"entries": []}}, expected, spec,
        phases=[phase(spec + CONTRACT), phase("Repeat the capture request from inputs/queue.json. Update existing notes without duplicating index entries. " + spec + CONTRACT)],
        web=web, extra_checks=[{"kind": "json", "path": "reading/index.json", "expected": {"entries": [
            {"id": "backup", "path": "reading/notes/backup.md"}, {"id": "reading", "path": "reading/notes/reading.md"}]}},
            {"kind": "text", "path": "reading/notes/backup.md", "min_chars": 40, "contains": ["{{WEB}}/articles/backup.html", str(days), "30"]},
            {"kind": "text", "path": "reading/notes/reading.md", "min_chars": 40, "contains": ["{{WEB}}/articles/reading.html", "2", "10"]}],
        mutable=["reading/index.json"])
    result["checks"].append({"kind": "retrieval", "path": "HTTP requests", "required": {
        "/articles/backup.html": 200, "/articles/reading.html": 200,
        **({"/articles/missing.html": 404} if v == "problem" else {})}})
    return result


def quiz(v):
    facts = [("N1", "water freezing point in Celsius", 0), ("N2", "days in a non-leap year", 365),
             ("N3", "minutes in an hour", 60), ("N4", "sides of a hexagon", 6),
             ("N5", "millimetres in a centimetre", 10), ("N6", "hours in a day", 24)]
    if v == "update":
        facts[1] = ("N2", "days in a leap year", 366)
    notes = "\n".join(f"{i}: {name}: {value}." for i, name, value in facts)
    if v == "problem":
        notes += "\nN7: Number of attendees next week: not confirmed. Do not infer a number."
    expected = {"answers": [{"note_id": i, "answer": value} for i, _, value in facts],
                "unanswerable_ids": ["N7"] if v == "problem" else []}
    return fixture({"inputs/learning-notes.md": notes}, expected,
        "Create one recall question for each answerable numbered fact in inputs/learning-notes.md. Save questions.md "
        "and answer-key.md separately, each at least 80 characters; questions must not include the answers. "
        "The structured result has answers:[{note_id,answer:<number>}], and unanswerable_ids. Use only the notes.",
        extra_checks=[{"kind": "text", "path": "questions.md", "min_chars": 80},
                      {"kind": "text", "path": "answer-key.md", "min_chars": 80}])


def digest(v):
    pages = [
        ("R1", "2026-10-09", "local agents", "18", "Local assistant memory study"),
        ("R2", "2026-10-10", "local agents", "24", "On-device document agents"),
        ("R3", "2026-09-01", "local agents", "11", "An older local agent study"),
        ("R4", "2026-10-10", "gardening", "9", "Garden soil study"),
    ]
    if v == "update":
        pages.append(("R5", "2026-10-11", "local agents", "30", "Fresh local assistant study"))
    if v == "problem":
        pages.append(("R6", "unknown", "local agents", "20", "Undated assistant claim"))
    web = {f"/research/{i}.html": f"<h1>{title}</h1><p id='date'>Published: {date}</p><p id='topic'>Topic: {topic}</p><p id='sample'>Participants: {n}</p>"
           for i, date, topic, n, title in pages}
    web["/research/feed.html"] = "\n".join(f"<a href='{i}.html'>{title}</a>" for i, _, _, _, title in pages)
    selected = [p for p in pages if p[2] == "local agents" and p[1] != "unknown" and "2026-10-08" <= p[1] <= "2026-10-11"]
    expected = {"selected": [{"id": i, "published": date, "participants": int(n), "url": f"{{{{WEB}}}}/research/{i}.html"}
                             for i, date, topic, n, title in selected], "uncertain_date_ids": ["R6"] if v == "problem" else []}
    result = fixture({"inputs/request.md": "Topic: local agents. Inclusive publication window: 8–11 October 2026.\nFeed: {{WEB}}/research/feed.html"},
                   expected, "Read inputs/request.md and fetch the local feed and candidate pages. Select all and only sources "
                   "matching both topic and publication window. The result has selected:[{id,published,participants,url}] and "
                   "uncertain_date_ids. Save a linked reading shortlist and explain exclusions in the report.", web=web)
    result["checks"].append({"kind": "retrieval", "path": "HTTP requests", "required": {path: 200 for path in web}})
    return result


def blog(v):
    n = 12 if v == "update" else 8
    files = {"inputs/notes.md": f"Experiment A: {n} successes out of 16 attempts. Elapsed time 45 seconds. "
             "This is one synthetic experiment, not proof of universal reliability. Source: trial-A.\n",
             "inputs/editor.md": "Use the title 'A useful local workflow'. Remove the unsupported sentence 'It never makes mistakes'. "
             "Preserve the counts and elapsed time. Add a section headed 'Limitations'."}
    if v == "problem":
        files["inputs/notes.md"] += "An earlier scratch note says 99 successes; this was corrected and must not be used."
    expected = {"trial_id": "trial-A", "successes": n, "attempts": 16, "elapsed_seconds": 45,
                "unsupported_claim_removed": True}
    request = ("Revise the saved outputs/draft.md using every instruction in inputs/editor.md. "
                   "The structured result fields are trial_id, successes, attempts, elapsed_seconds, unsupported_claim_removed. "
                   "Do not add results from outside the notes.")
    return fixture(files, expected, request,
                   phases=[phase("Draft outputs/draft.md from inputs/notes.md. Preserve the experiment facts and qualification. "
                                 "Save at least 120 characters. Editorial feedback will arrive in a later session."),
                           phase(request + CONTRACT, provide_before=["inputs/editor.md"])],
                   extra_checks=[{"kind": "text", "path": "outputs/draft.md", "min_chars": 120, "phase": 1},
                                 {"kind": "text", "path": "outputs/draft.md", "min_chars": 120,
                                  "contains": ["A useful local workflow", "Limitations", str(n), "16", "45"],
                                  "absent": ["It never makes mistakes", "99"]}])


def invites(v):
    messages = [
        {"message_id": "M1", "event_id": "E1", "sequence": 1, "action": "invite", "start": "2026-10-12T10:00:00+01:00", "duration_minutes": 30},
        {"message_id": "M2", "event_id": "E2", "sequence": 1, "action": "invite", "start": "2026-10-12T11:00:00+01:00", "duration_minutes": 45},
        {"message_id": "M3", "event_id": "E1", "sequence": 2, "action": "update", "start": "2026-10-12T12:00:00+01:00", "duration_minutes": 30},
        {"message_id": "M4", "event_id": "E2", "sequence": 2, "action": "cancel"}]
    if v == "update":
        messages.append({"message_id": "M5", "event_id": "E1", "sequence": 3, "action": "update", "start": "2026-10-12T14:00:00+01:00", "duration_minutes": 60})
    if v == "problem":
        messages.extend([messages[0], messages[2], {"message_id": "M6", "event_id": "E3", "sequence": 1, "action": "invite", "start": "TBD", "duration_minutes": 30}])
    current = messages[4] if v == "update" else messages[2]
    expected = {"events": [{"id": "E1", "start": current["start"], "duration_minutes": current["duration_minutes"]}],
                "cancelled_ids": ["E2"], "needs_review_ids": ["E3"] if v == "problem" else []}
    return fixture({"inputs/messages.json": messages, "inputs/initial-events.json": []}, expected,
                   "Reconcile inputs/messages.json against initial-events.json. event_id and sequence determine which update is current, "
                   "not arrival order. Deduplicate repeated messages. Keep unknown starts for review. The result has events:[{id,start,duration_minutes}], "
                   "cancelled_ids, needs_review_ids. Explain the changes in your report.")


def training(v):
    delay = 15 if v == "update" else 10
    text = ("00:00 [P1] Topic: Seed storage. Label each packet with its harvest year.\n"
            "05:00 [P2] Topic: Sowing. Place one seed in each pot.\n"
            f"10:00 [P3] Topic: Sowing continued. Check the pots after {delay} days.\n"
            "15:00 [P4] Topic: Record keeping. Log the germination date.\n")
    if v == "problem":
        text += "20:00 [P5] Storage temperature: [inaudible]. Do not reconstruct the missing value.\n"
    expected = {"topics": [{"id": "storage", "paragraphs": ["P1"], "timestamp": "00:00"},
                            {"id": "sowing", "paragraphs": ["P2", "P3"], "timestamp": "05:00"},
                            {"id": "records", "paragraphs": ["P4"], "timestamp": "15:00"}],
                "check_after_days": delay, "uncertain_paragraphs": ["P5"] if v == "problem" else []}
    return fixture({"inputs/transcript.txt": text}, expected, "Turn the supplied transcript into outputs/study-notes.md. Group continued "
                   "sections with their topic. The JSON result has topics:[{id,paragraphs,timestamp}] with topic IDs storage, sowing, records, "
                   "check_after_days, and uncertain_paragraphs. Do not silently repair inaudible text.",
                   extra_checks=[{"kind": "text", "path": "outputs/study-notes.md", "min_chars": 120, "contains": ["00:00", "05:00", "15:00"]}])


def interview(v):
    lead = "led" if v == "update" else "assisted"
    files = {"inputs/cv.md": f"[C1] Alex Morgan. Coordinated community events.\n[C2] Alex {lead} the Orchard inventory project.\n",
             "inputs/role.md": "[R1] Event coordination.\n[R2] Inventory project experience.\n[R3] Budget ownership.\n"}
    if v == "problem":
        files["inputs/cv.md"] += "[C3] The Orchard newsletter project involved editing, not inventory."
    expected = {"coverage": [{"requirement_id": "R1", "evidence_ids": ["C1"]}, {"requirement_id": "R2", "evidence_ids": ["C2"]},
                              {"requirement_id": "R3", "evidence_ids": []}], "inventory_responsibility": lead,
                "unsupported_requirement_ids": ["R3"]}
    return fixture(files, expected, "Prepare interview questions in outputs/questions.md from the fictional CV and role. "
                   "The JSON result has coverage:[{requirement_id,evidence_ids}], inventory_responsibility (the CV's verb), "
                   "and unsupported_requirement_ids. Missing experience should lead to a question, not an assertion or hiring recommendation.",
                   extra_checks=[{"kind": "text", "path": "outputs/questions.md", "min_chars": 120, "contains": ["R1", "R2", "R3"]}])


def handover(v):
    owner = "Morgan" if v == "update" else "Alex"
    log = f"09:00 [L1] T1 completed.\n10:00 [L2] T2 open; owner {owner}; due 2026-10-13.\n11:00 [L3] Decision: venue is North Hall.\n"
    if v == "problem":
        log += "14:00 [L4] T2 completed, replacing L2.\n15:00 [L5] Decision: venue is South Hall, replacing L3.\n"
    open_tasks = [] if v == "problem" else [{"id": "T2", "owner": owner, "due": "2026-10-13"}]
    day1 = {"completed_ids": ["T1", "T2"] if v == "problem" else ["T1"], "open_tasks": open_tasks,
            "venue": "South Hall" if v == "problem" else "North Hall"}
    final = {**day1, "open_tasks": open_tasks + [{"id": "T3", "owner": "Sam", "due": "2026-10-14"}]}
    first = "Read inputs/day1-log.md. Save outputs/day1.json with completed_ids, open_tasks:[{id,owner,due}], and venue. Later log entries supersede earlier ones. Save a readable handover too."
    second = ("It is the next day in a fresh session. Use your saved outputs/day1.json; yesterday's raw log is unavailable. "
              "New update: T3 is open, owner Sam, due 2026-10-14. Save outputs/result.json with completed_ids, open_tasks:[{id,owner,due}], "
              "and venue, preserving yesterday's still-current facts. Save tomorrow's starting point in outputs/report.md.")
    return fixture({"inputs/day1-log.md": log}, final, second,
                   phases=[phase(first), phase(second + CONTRACT, ["inputs/day1-log.md"])],
                   extra_checks=[{"kind": "json", "path": "outputs/day1.json", "expected": day1, "phase": 1}])


def school(v):
    location = "East Gym" if v == "update" else "Main Gym"
    messages = ["[S1] 2026-10-12 09:00 Europe/London: Football tomorrow at 17:00 for one hour, at Main Gym. Bring boots.",
                "[S2] 2026-10-12 09:10 Europe/London: School photo consent due Friday 16 October. Bring the form.",
                "[S3] 2026-10-12 10:00 Europe/London: Thanks everyone! Lovely weather.",
                "[S4] 2026-10-12 11:00 Europe/London: Judo on 14 October at 16:00 is cancelled."]
    if v == "update":
        messages.append("[S5] 2026-10-12 12:00 Europe/London: Football venue changed to East Gym. Same date and time.")
    if v == "problem":
        messages.append("[S6] 2026-10-12 12:00 Europe/London: Birthday party sometime next week, time and venue still unconfirmed.")
    expected = {"events": [{"id": "football", "start": "2026-10-13T17:00:00+01:00", "duration_minutes": 60, "venue": location}],
                "actions": [{"id": "boots", "due": "2026-10-13", "source_id": "S1"}, {"id": "consent", "due": "2026-10-16", "source_id": "S2"}],
                "cancelled_ids": ["judo"], "conflict_ids": ["football", "pickup"], "needs_review_ids": ["S6"] if v == "problem" else []}
    return fixture({"inputs/messages.txt": "\n".join(messages), "inputs/family-calendar.json": [{"id": "pickup", "start": "2026-10-13T17:30:00+01:00", "duration_minutes": 30}]},
                   expected, "Extract actionable school/activity messages; do not turn chatter into tasks. Use message dates to interpret tomorrow. "
                   "Result fields: events:[{id,start,duration_minutes,venue}], actions:[{id,due,source_id}], cancelled_ids, conflict_ids, needs_review_ids. "
                   "Use event IDs football, judo; action IDs boots, consent; existing calendar ID pickup. Flag conflicts with the supplied family calendar.")


def meals(v):
    recipes = [{"id": "rice-beans", "minutes": 20, "ingredients_per_serving": {"rice": 1, "beans": 1}},
               {"id": "pasta", "minutes": 15, "ingredients_per_serving": {"pasta": 1, "tomato": 1}},
               {"id": "rice-eggs", "minutes": 10, "ingredients_per_serving": {"rice": 1, "eggs": 1}}]
    days = [{"date": f"2026-10-{12+i:02d}", "servings": 3 if v == "update" and i == 2 else 2, "max_minutes": 10 if v == "problem" and i == 1 else 25} for i in range(5)]
    rules = {"recipes": recipes, "days": days, "pantry": {"rice": 4, "beans": 2, "pasta": 2, "tomato": 0, "eggs": 2},
             "unit_prices_cents": {"rice": 50, "beans": 60, "pasta": 50, "tomato": 40, "eggs": 30}, "budget_cents": 1200,
             "minimum_distinct_recipes": 2, "leftover_lunch_dates": ["2026-10-14", "2026-10-16"]}
    # A feasible reference is retained reviewer-side for checker self-tests only.
    choices = ["rice-beans", "rice-eggs", "pasta", "rice-eggs", "pasta"]
    quantities = {k: 0 for k in rules["pantry"]}
    dinners = []
    for day, recipe_id in zip(days, choices):
        servings = day["servings"] + (1 if day["date"] in {"2026-10-13", "2026-10-15"} else 0)
        dinners.append({"date": day["date"], "recipe_id": recipe_id, "servings": servings})
        recipe = next(r for r in recipes if r["id"] == recipe_id)
        for item, qty in recipe["ingredients_per_serving"].items():
            quantities[item] += qty * servings
    shopping = {item: max(0, qty - rules["pantry"].get(item, 0)) for item, qty in quantities.items()}
    reference = {"dinners": dinners, "leftover_lunches": [{"date": "2026-10-14", "from_dinner_date": "2026-10-13", "servings": 1},
                                                        {"date": "2026-10-16", "from_dinner_date": "2026-10-15", "servings": 1}],
                 "shopping": shopping, "cost_cents": sum(qty * rules["unit_prices_cents"][item] for item, qty in shopping.items())}
    result = fixture({"inputs/meal-rules.json": rules}, None,
                   "Plan five dinners and one-person leftover lunches on the two specified dates using meal-rules.json. "
                   "Each dinner must serve that day's diners plus any portions reserved for a later lunch. Lunches must use a previously cooked dinner. "
                   "Use at least minimum_distinct_recipes, obey daily cooking limits, subtract pantry quantities, and fit the budget. "
                   "Result shape: {dinners:[{date,recipe_id,servings}], leftover_lunches:[{date,from_dinner_date,servings}], "
                   "shopping:{<ingredient>:<units to buy, including zeros>}, cost_cents}. Any feasible plan is acceptable.",
                   extra_checks=[{"kind": "meals", "path": "outputs/result.json", "rules": rules}])
    result["reference_output"] = reference
    return result


def expenses(v):
    records = [("R1", "2026-10-12", "Stationery", "GBP", 1250), ("R2", "2026-10-13", "Rail", "GBP", 2400),
               ("R3", "2026-10-14", "Cafe", "EUR", 800), ("R4", "2026-10-09", "Stationery", "GBP", 500)]
    if v == "update":
        records.append(("R5", "2026-10-14", "Rail refund", "GBP", -600))
    if v == "problem":
        records.append(("R6", "2026-10-14", "Stationery", "GBP", None))
    files = {f"inputs/receipts/{i}.txt": f"Receipt ID: {i}\nDate: {date}\nMerchant: {merchant}\nCurrency: {currency}\nAmount in cents: {amount if amount is not None else '[unreadable]'}\n"
             for i, date, merchant, currency, amount in records}
    files["inputs/receipts/duplicate-R2.txt"] = files["inputs/receipts/R2.txt"]
    files["inputs/policy.md"] = "Report period: 2026-10-12 through 2026-10-16 inclusive. Stationery => supplies; Rail/Rail refund => travel; Cafe => meals. Separate currencies."
    included = [{"id": i, "date": date, "category": "travel" if merchant.startswith("Rail") else "supplies" if merchant == "Stationery" else "meals",
                 "currency": currency, "amount_cents": amount} for i, date, merchant, currency, amount in records if date >= "2026-10-12"]
    totals = {"GBP": 3650 - (600 if v == "update" else 0), "EUR": 800}
    expected = {"receipts": included, "totals_cents": totals, "excluded_ids": ["R4"], "review_ids": ["R6"] if v == "problem" else []}
    return fixture(files, expected, "Read every receipt and the policy. Produce an auditable expense report. "
                   "Result shape: {receipts:[{id,date,category,currency,amount_cents}], totals_cents:{GBP:<number>,EUR:<number>}, excluded_ids, review_ids}. "
                   "Deduplicate receipt IDs, exclude dates outside the period, preserve refunds, and flag unreadable amounts. "
                   "Known totals exclude unknown amounts; state that limitation in the report.")


def organize(v):
    originals = {"inbox/a.txt": "TYPE: receipt\nMerchant: Paper shop\n",
                 "inbox/b.txt": "TYPE: reading\nA note about library hours\n",
                 "inbox/c.txt": "TYPE: travel\nHotel check-in is at 15:00\n",
                 "inbox/sub/a.txt": "TYPE: receipt\nMerchant: Rail station\n"}
    if v == "update":
        originals["inbox/b.txt"] = "TYPE: travel\nA changed itinerary, despite its earlier name\n"
    if v == "problem":
        originals["inbox/ambiguous.txt"] = "Unlabelled fragment. No reliable category is present.\n"
    categories = {p: ("receipts" if "TYPE: receipt" in content else "reading" if "TYPE: reading" in content else "travel" if "TYPE: travel" in content else "review") for p, content in originals.items()}
    rules = {"original_sha256": {p: hashlib.sha256(content.encode()).hexdigest() for p, content in originals.items()}, "categories": categories}
    return fixture(originals, None, "Organize the copied inbox files by their TYPE label, not their filename. Move receipt files into organized/receipts/, "
                   "reading into organized/reading/, travel into organized/travel/, and unlabelled files into organized/review/. Preserve bytes and avoid name collisions. "
                   "Result shape: {moves:[{from:<original relative path>,to:<final relative path>}]}. Account for every file. Only inbox files may be moved; "
                   "do not change other inputs. The checker accepts any collision-free filenames within the correct folders.",
                   extra_checks=[{"kind": "organize", "path": "outputs/result.json", "rules": rules}], mutable=list(originals))


def itinerary(v):
    options = [{"id": "museum", "open": "10:00", "close": "17:00", "minutes": 60},
               {"id": "garden", "open": "09:00", "close": "16:00", "minutes": 45},
               {"id": "gallery", "open": "10:00", "close": "17:00", "minutes": 45}]
    required = ["museum", "gallery" if v == "update" else "garden"]
    unavailable = ["garden"] if v == "update" else []
    if v == "problem":
        options[1].update(close="12:00")
    travel = {"hotel": {"museum": 30, "garden": 20, "gallery": 20},
              "museum": {"hotel": 30, "garden": 20, "gallery": 20},
              "garden": {"hotel": 20, "museum": 20, "gallery": 15},
              "gallery": {"hotel": 20, "museum": 20, "garden": 15}}
    rules = {"date": "2026-10-13", "departure": "09:00", "hotel_return_by": "15:00", "max_drive_minutes": 90,
             "attractions": options, "required_ids": required, "unavailable_ids": unavailable, "travel_minutes": travel,
             "fixed_reservation": {"id": "museum", "arrival": "10:00"}}
    reference = {"date": rules["date"], "stops": [{"id": "museum", "arrival": "10:00", "departure": "11:00"},
                                                 {"id": required[1], "arrival": "11:20", "departure": "12:05"}],
                 "hotel_return": "12:25"}
    if v == "problem":
        rules["departure"] = "08:30"
        options[1]["minutes"] = 30
        reference.update(stops=[{"id": "garden", "arrival": "09:00", "departure": "09:30"},
                                {"id": "museum", "arrival": "10:00", "departure": "11:00"}], hotel_return="11:30")
    result = fixture({"inputs/trip.json": rules}, None, "Plan a feasible day using trip.json, visiting every required attraction once, preserving the museum reservation. "
                     "Account for travel from the hotel and back, opening hours, activity durations, driving limits and hotel return time. "
                     "Result shape: {date,stops:[{id,arrival:<HH:MM>,departure:<HH:MM>}],hotel_return:<HH:MM>}. "
                     "Stops must be in chronological order. Any feasible itinerary is acceptable.",
                     extra_checks=[{"kind": "itinerary", "path": "outputs/result.json", "rules": rules}])
    result["reference_output"] = reference
    return result


def meeting(v):
    owner = "Morgan" if v == "update" else "Alex"
    notes = {"inputs/notes/01.md": "[N1] 2026-10-08 Project Orchard: use North Hall. T1: Alex to send invitation, open.",
             "inputs/notes/02.md": f"[N2] 2026-10-10 Project Orchard: venue changed to South Hall. T1 now owned by {owner}, still open.",
             "inputs/notes/03.md": "[N3] 2026-10-11 Project Harbor: use West Hall. T9: Pat to send invoice, open."}
    if v == "problem":
        notes["inputs/notes/04.md"] = "[N4] 2026-10-11 Orchard newsletter (a different project): publication is in West Hall."
    notes["inputs/meeting.md"] = "Prepare for Project Orchard's community-event planning meeting on 2026-10-12."
    expected = {"project": "Orchard", "venue": "South Hall", "decision_source_id": "N2",
                "open_commitments": [{"id": "T1", "owner": owner, "source_id": "N2"}], "irrelevant_note_ids": ["N3", "N4"] if v == "problem" else ["N3"]}
    return fixture(notes, expected, "Read the upcoming meeting and earlier notes. Distinguish projects, prefer latest decisions, and save a preparation brief. "
                   "Result shape: {project,venue,decision_source_id,open_commitments:[{id,owner,source_id}],irrelevant_note_ids}. "
                   "Do not import commitments from unrelated projects.")


BUILDERS = dict(zip([row[0] for row in CATALOG], [schedule, articles, quiz, digest, blog, invites, training,
                interview, handover, school, meals, expenses, organize, itinerary, meeting]))


def build_cases():
    result = {}
    for case_id, title, source_id, scope in CATALOG:
        variants = {}
        for variant in VARIANTS:
            item = BUILDERS[case_id](variant)
            if len(item["phases"]) == 1:
                item["phases"][0]["prompt"] += CONTRACT
            variants[variant] = item
        result[case_id] = {"schema_version": 1, "case_id": case_id, "title": title,
                           "provenance": {"kind": "synthetic_inspired_by_firsthand_report", "source_id": source_id,
                                          "source_url": SOURCES[source_id], "researched_on": "2026-10-11"},
                           "scope": scope, "variants": variants}
    return result
