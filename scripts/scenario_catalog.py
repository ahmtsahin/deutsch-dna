"""Scenario frames and small, reusable plans for real-life German goals."""

from __future__ import annotations

import copy
from typing import Any


SCENARIO_ALIASES = {
    "work": "arbeit", "doctor": "arzt", "housing": "wohnung", "everyday": "alltag",
    "interview": "bewerbung", "job-interview": "bewerbung", "presentation": "praesentation",
    "administration": "behoerde", "train": "bahnhof", "shopping": "einkaufen",
    "pharmacy": "apotheke", "phone": "telefon", "school": "schule", "customer-service": "kundenservice",
}


def scene(title: str, role: str, setting: str, opening: str, goal: str,
          example: str, variations: tuple[str, str], followups: tuple[str, str], **extra: Any) -> dict[str, Any]:
    return {"title": title, "assistant_role": role, "setting": setting, "opening": opening,
            "learner_goal": goal, "suggested_turns": 8, "example_request": example,
            "variations": list(variations), "followup_openings": list(followups), **extra}


SCENARIOS = {
    "alltag": scene("Everyday life", "a helpful neighbor", "A short everyday encounter in Germany",
        "Hallo! Wir haben uns lange nicht gesehen. Wie geht es dir?",
        "Keep a natural everyday exchange going and ask one follow-up question.",
        "A neighbor asks about your weekend, then invites you to a neighborhood event.",
        ("Ask for directions when the usual street is closed.", "Arrange a time to help a neighbor."),
        ("Leider bin ich am Samstag schon verabredet. Wann passt es dir sonst?", "Wie wäre es, wenn wir zusammen hingehen?")),
    "arbeit": scene("At work", "a colleague who needs a clear update", "A German workplace conversation",
        "Guten Morgen. Kannst du mir kurz sagen, wie der aktuelle Stand ist?",
        "Explain a status, a problem, and the next step politely.",
        "Explain a delayed task and agree on a realistic next step with a colleague.",
        ("Disagree politely about a deadline.", "Explain a technical problem to a nontechnical colleague."),
        ("Was können wir tun, wenn der Termin nicht zu halten ist?", "Kannst du das bitte für einen neuen Kollegen einfacher erklären?")),
    "arzt": scene("Doctor's appointment", "a doctor asking language-practice questions",
        "A fictional doctor's appointment for language practice only", "Guten Tag. Was kann ich heute für Sie tun?",
        "Describe symptoms, duration, and intensity, then answer follow-up questions.",
        "Describe a fictional headache and ask the doctor to repeat a question.",
        ("Explain when fictional symptoms started.", "Ask what an unfamiliar appointment word means."),
        ("Seit wann haben Sie diese Beschwerden?", "Können Sie mir das bitte noch einmal genauer beschreiben?"),
        safety_note="This is language practice, not medical advice or diagnosis."),
    "wohnung": scene("Housing", "a landlord or property manager", "A flat viewing or repair conversation",
        "Guten Tag. Möchten Sie zuerst die Wohnung besichtigen oder haben Sie eine Frage?",
        "Ask precise questions and explain one housing need or problem.",
        "View an apartment, ask about costs, and explain your moving date.",
        ("Report a broken heater and arrange a repair visit.", "Ask about noise and explain your working hours."),
        ("Der Einzug wäre erst einen Monat später möglich. Wie passt das für Sie?", "Wann könnten Sie für einen Handwerker zu Hause sein?")),
    "restaurant": scene("Restaurant", "a waiter in a busy restaurant", "A restaurant visit from arrival to payment",
        "Guten Abend. Haben Sie reserviert?", "Handle the reservation, order, one special request, and payment.",
        "Your reservation cannot be found. Explain it and ask for an alternative.",
        ("The dish you ordered is sold out.", "Ask politely to correct a mistaken order."),
        ("Das Gericht ist heute leider ausverkauft. Was darf es stattdessen sein?", "Möchten Sie zusammen oder getrennt bezahlen?")),
    "bewerbung": scene("Job interview", "a hiring manager", "A fictional German-language job interview",
        "Guten Tag. Schön, dass Sie da sind. Erzählen Sie uns bitte etwas über sich.",
        "Introduce yourself, support an answer with a concrete example, and handle a follow-up.",
        "Practise a job interview with questions about experience, a setback, and teamwork.",
        ("Explain a gap or change in your career without inventing personal facts.", "Discuss a disagreement at work."),
        ("Was haben Sie aus dieser Situation gelernt?", "Was würden Sie heute anders machen?")),
    "praesentation": scene("Presentation", "a colleague in the audience", "A short project presentation and questions",
        "Wir sind gespannt auf Ihr Projekt. Was ist das Ziel Ihrer Präsentation?",
        "Explain a project clearly, give reasons, and answer an unexpected question.",
        "Present a project, then answer a skeptical colleague's question.",
        ("Summarize your proposal in thirty seconds.", "Explain a technical term in plain language."),
        ("Was wäre Ihr Plan, wenn das Budget kleiner ausfällt?", "Welchen konkreten Nutzen hat das für unser Team?")),
    "behoerde": scene("Public office", "a public-office receptionist", "A fictional appointment at a municipal office",
        "Guten Tag. Haben Sie einen Termin und worum geht es?",
        "Explain the purpose of an appointment, ask for clarification, and agree on a next step.",
        "At a fictional public office, clarify which appointment you need and what to bring.",
        ("A fictional document is missing; ask what to do next.", "Ask for a slower explanation of an unfamiliar form."),
        ("In unserem Übungsfall fehlt noch ein Dokument. Wie möchten Sie weiter vorgehen?", "Passt Ihnen ein neuer Termin nächste Woche?")),
    "bahnhof": scene("Train station", "a railway service employee", "A fictional train journey with a disruption",
        "Guten Tag. Wohin möchten Sie fahren?", "Describe a travel problem and ask about an alternative connection.",
        "Your train is delayed and you may miss a connection. Ask for another route.",
        ("Check whether you need to change platforms.", "Explain that the ticket machine did not work."),
        ("Die direkte Verbindung fällt leider aus. Wäre ein Umstieg für Sie möglich?", "Wann müssen Sie spätestens ankommen?")),
    "einkaufen": scene("Shopping and returns", "a shop assistant", "A purchase or return in a fictional shop",
        "Guten Tag. Wie kann ich Ihnen helfen?", "Explain what you need, compare options, and resolve a purchase problem.",
        "Return a jacket that is the wrong size and ask about an exchange.",
        ("The requested size is unavailable.", "Explain a problem with a recently bought item."),
        ("Diese Größe haben wir leider nicht mehr. Wäre eine andere Farbe in Ordnung?", "Was genau funktioniert an dem Artikel nicht?")),
    "apotheke": scene("Pharmacy", "a pharmacist in a fictional language-practice scene",
        "A fictional pharmacy visit for language practice only", "Guten Tag. Was möchten Sie fragen?",
        "Describe a fictional request and ask for the meaning or repetition of a phrase.",
        "Practise explaining a fictional request and asking what an unfamiliar label means.",
        ("Ask the pharmacist to explain an unfamiliar German word.", "Ask for a fictional opening time or availability."),
        ("Welches Wort auf der Packung möchten Sie erklärt haben?", "Soll ich das bitte langsamer wiederholen?"),
        safety_note="Use fictional language practice. Do not recommend treatments, doses, or medication."),
    "telefon": scene("Phone appointment", "a receptionist on the phone", "A telephone appointment or rescheduling call",
        "Guten Tag. Sie sprechen mit der Anmeldung. Was kann ich für Sie tun?",
        "State the reason for calling, agree on a time, and confirm the details.",
        "Move an appointment because your original time no longer works.",
        ("The line is unclear; ask for repetition.", "The offered appointment conflicts with work."),
        ("Dieser Termin ist leider schon vergeben. Wann hätten Sie sonst Zeit?", "Können Sie die vereinbarte Uhrzeit bitte noch einmal bestätigen?")),
    "schule": scene("School conversation", "a teacher", "A fictional parent-teacher or student-teacher meeting",
        "Guten Tag. Worüber möchten Sie heute sprechen?", "Describe a concern, ask questions, and agree on a practical next step.",
        "Discuss a fictional classroom concern and ask how to help at home.",
        ("Ask for clarification about a homework task.", "Agree on a follow-up conversation."),
        ("Was haben Sie bisher zu Hause beobachtet?", "Welchen kleinen nächsten Schritt könnten wir gemeinsam versuchen?")),
    "hotel": scene("Hotel", "a hotel receptionist", "A fictional hotel check-in or room problem",
        "Guten Abend. Auf welchen Namen haben Sie gebucht?", "Check in, explain a booking detail, and resolve a room problem politely.",
        "Check into a hotel and explain that your room does not match the booking.",
        ("Ask about a late arrival.", "Explain that the room is too noisy."),
        ("Das gebuchte Zimmer ist gerade noch nicht fertig. Können Sie kurz warten?", "Wäre ein Zimmer auf einer anderen Etage für Sie in Ordnung?")),
    "kundenservice": scene("Customer service", "a customer-service representative", "A fictional billing or delivery complaint",
        "Guten Tag. Bitte schildern Sie mir kurz Ihr Anliegen.", "Explain a problem, state the desired resolution, and confirm the agreement.",
        "An order has not arrived. Explain the situation and agree on a solution.",
        ("Clarify a fictional unexpected charge.", "The first proposed solution does not meet your needs."),
        ("Die erste Lösung ist leider nicht möglich. Welche Alternative würde Ihnen helfen?", "Können Sie mir die Reihenfolge der Ereignisse noch einmal nennen?")),
}


INTERVIEW_STEPS = [
    {"id": "introduction", "label": "Sich vorstellen", "goal": "Introduce your actual role, relevant experience, and motivation.",
     "criteria": ["State your role or background", "Give one relevant example", "Connect your motivation to the opportunity"],
     "openings": ["Erzählen Sie uns bitte etwas über sich und Ihre Erfahrung.", "Welche Erfahrung bringen Sie für diese Stelle mit?", "Was sollten wir zuerst über Ihren beruflichen Hintergrund wissen?"], "difficulty": "foundation"},
    {"id": "difficult_questions", "label": "Schwierige Fragen", "goal": "Answer a difficult question with a situation, your action, and what you learned.",
     "criteria": ["Describe one concrete situation", "Explain your own action", "State the result or what you learned"],
     "openings": ["Erzählen Sie von einer schwierigen Situation bei der Arbeit. Wie sind Sie damit umgegangen?", "Wann mussten Sie einen Fehler korrigieren? Wie haben Sie reagiert?", "Wie sind Sie mit einer Meinungsverschiedenheit im Team umgegangen?"], "difficulty": "challenge"},
    {"id": "followup", "label": "Unerwartete Nachfrage", "goal": "Respond to an unexpected follow-up and ask for clarification when needed.",
     "criteria": ["Respond to the actual follow-up", "Give a specific reason or alternative", "Clarify an ambiguous question when needed"],
     "openings": ["Was würden Sie tun, wenn Ihre erste Lösung nicht funktioniert?", "Wie würden Sie vorgehen, wenn sich die Prioritäten plötzlich ändern?", "Was würden Sie heute an Ihrem Vorgehen ändern und warum?"], "difficulty": "transfer"},
]


def mission_steps(scenario: str) -> list[dict[str, Any]]:
    if scenario == "bewerbung":
        return copy.deepcopy(INTERVIEW_STEPS)
    template = SCENARIOS[scenario]
    return [
        {"id": "opening", "label": "Anliegen erklären", "goal": "Introduce the situation and make your first concrete request.",
         "criteria": ["State the purpose of the exchange", "Give relevant details", "Make one clear request"],
         "openings": [template["opening"], "Was möchten Sie heute genau klären?"], "difficulty": "foundation"},
        {"id": "main_task", "label": "Ziel verfolgen", "goal": template["learner_goal"],
         "criteria": ["Address the main task", "Give a reason or example", "Agree on a concrete next step"],
         "openings": [template["followup_openings"][0], template["opening"]], "difficulty": "challenge"},
        {"id": "followup", "label": "Auf eine Änderung reagieren", "goal": "Handle a new complication and confirm the resulting agreement.",
         "criteria": ["Respond to the changed situation", "Suggest or evaluate an alternative", "Confirm what happens next"],
         "openings": [template["followup_openings"][1], template["followup_openings"][0]], "difficulty": "transfer"},
    ]


def scenario_examples() -> list[dict[str, Any]]:
    return [{"id": key, **{field: value[field] for field in ("title", "opening", "learner_goal", "example_request", "variations")}}
            for key, value in SCENARIOS.items()]
