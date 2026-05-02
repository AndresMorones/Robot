
try:
    loadboard_rate = float(input_data.get('loadboard_rate', 0) or 0)
    carrier_offer  = float(input_data.get('carrier_offer', 0) or 0)
    round_number   = int(input_data.get('round_number', 1) or 1)
    prior_offers   = input_data.get('prior_broker_offers') or []
    if not isinstance(prior_offers, list):
        prior_offers = []
    load_ref       = str(input_data.get('load_reference') or 'unknown')
    floor_pct      = float(input_data.get('negotiation_floor_pct', 0.10) or 0.10)
    max_rounds     = int(input_data.get('max_negotiation_rounds', 3) or 3)
    parse_ok = True
except (ValueError, TypeError):
    parse_ok = False

# ---------- 2. Edge-case branch ----------
if not parse_ok:
    output = {
        'action': 'ESCALATE',
        'counter_offer': None,
        'round_number_next': 1,
        'scripted_message': "Hold on a second while I double-check something with my team.",
        'rationale_code': 'INPUT_PARSE_ERROR'
    }
elif carrier_offer <= 0:
    # Carrier spoke but didn't state a number — agent should ask for one
    output = {
        'action': 'REQUEST_OFFER',
        'counter_offer': None,
        'round_number_next': round_number,
        'scripted_message': "I hear you — what number are you thinking? Give me a rate and I'll see what I can do on my end.",
        'rationale_code': 'NO_OFFER_PROVIDED'
    }
elif carrier_offer < 0 or loadboard_rate <= 0:
    output = {
        'action': 'ESCALATE',
        'counter_offer': None,
        'round_number_next': round_number,
        'scripted_message': "Hold on, let me double-check this load with my team real quick.",
        'rationale_code': 'INVALID_LOAD_OR_OFFER'
    }
elif carrier_offer > loadboard_rate * 3:
    # Likely LLM parse error (e.g., heard "twenty-four hundred" as 24000, or cents/dollars confusion)
    output = {
        'action': 'ESCALATE',
        'counter_offer': None,
        'round_number_next': round_number,
        'scripted_message': "Sorry, could you say that rate one more time? I want to make sure I caught the number right.",
        'rationale_code': 'OFFER_OUT_OF_RANGE'
    }
else:
    # ---------- 3. Normal negotiation logic ----------
    round_number = max(1, min(round_number, max_rounds))  # clamp defensively
    floor_rate   = loadboard_rate * (1 - floor_pct)
    round_discounts  = {1: 0.05, 2: 0.08, 3: floor_pct}
    current_discount = round_discounts.get(round_number, floor_pct)
    proposed_counter = int(round(loadboard_rate * (1 - current_discount)))

    if carrier_offer >= loadboard_rate:
        output = {
            'action': 'ACCEPT',
            'counter_offer': None,
            'round_number_next': round_number,
            'scripted_message': f"Perfect, we've got a deal at {int(round(carrier_offer))} dollars. Let me transfer you to our booking team to finalize.",
            'rationale_code': 'CARRIER_MET_ASK'
        }
    elif carrier_offer >= floor_rate:
        if round_number >= max_rounds or carrier_offer >= proposed_counter:
            output = {
                'action': 'ACCEPT',
                'counter_offer': None,
                'round_number_next': round_number,
                'scripted_message': f"Alright, I can make {int(round(carrier_offer))} work. Let me get you to our booking team.",
                'rationale_code': 'WITHIN_FLOOR_ACCEPT'
            }
        else:
            output = {
                'action': 'COUNTER',
                'counter_offer': proposed_counter,
                'round_number_next': round_number + 1,
                'scripted_message': f"I hear you, but the best I can come down to right now is {proposed_counter}. Does that work?",
                'rationale_code': 'WITHIN_FLOOR_COUNTER'
            }
    elif round_number >= max_rounds:
        output = {
            'action': 'REJECT',
            'counter_offer': None,
            'round_number_next': round_number,
            'scripted_message': "I appreciate you working with me, but I can't go that low on this one. Keep checking our postings — we get new loads up every day.",
            'rationale_code': 'ROUND_CAP_BELOW_FLOOR'
        }
    else:
        output = {
            'action': 'COUNTER',
            'counter_offer': proposed_counter,
            'round_number_next': round_number + 1,
            'scripted_message': f"That's a little tight for me. I can come in at {proposed_counter}. Can you make that work?",
            'rationale_code': 'BELOW_FLOOR_COUNTER'
        }