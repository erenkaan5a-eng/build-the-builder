"""Negotiation runtime: the dialogue model turns the customer's words into structured events; code keeps the state,
decides the next offer, binds the confirmation to one read-back version, records through engine-run calls and
closes. Every value comes from CFG (built from policy.json); the code holds no brief values.

Event/transition table (one product p unless product_id is "all"):
  pays_today      -> agreed(today, current amount) if today is a valid date, else the date rules apply
  refuses         -> the pending offer is refused; next ladder attempt if attempts remain and it is not a repeat, else p refused
  too_much        -> floor offered once (with the 'rest stays overdue' sentence); after that it counts as refuses
  proposes(d,a)   -> amount below floor: floor offered once, then refuses; date: ok / next business day offered /
                     after deadline: deadline offered (or, for a shared date on several products when the brief says so,
                     recorded on that product's own deadline) / past: ask again / 'vague': ask for the exact day once, then deadline
                     A proposal is never a refusal.
  accepts         -> the pending offer becomes agreed
  confirms        -> only valid for the read-back version just presented: phase 'record'
  changes(d,a)    -> like proposes; the earlier confirmation is void
  hardship        -> no persuasion for p; the support offer is read; declines_support -> p hardship
  dispute / paid  -> p dispute / paid
  stop            -> every open product refused once the brief's count of such statements is reached (CFG stop_close,
                     default 1); an earlier one is handled as refuses
When no product is open: agreed products -> read-back (new version) ; none -> finish.
Recording: rec_next sends one create_promise per agreed product through an engine-run node, judges each attempt from the
node's success/failure counters and the response's success field, retries up to CFG['retries'] times (single layer).
Finish: outcome from recorded promises / transfer / product statuses; notes (if the brief uses them, never after a transfer);
the goodbye line is spoken, then notes, then exactly one close_call.
"""
import json

HELPERS = r'''
import json, datetime, re, math
CFG = json.loads(r"""__CFG__""")
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
class Safe(dict):
    def __missing__(self, k):
        return ''
def say(key, **kw):
    t = CFG['say'].get(key) or ''
    return t.format_map(Safe(kw)).strip()
def sp(d):
    return DAYS[d.weekday()] + ' ' + str(d.day) + ' ' + MONTHS[d.month - 1]
def money(x):
    return '%.2f' % float(x)
def isbd(d):
    return d.weekday() not in CFG['weekend_days'] and d.isoformat() not in CFG['holidays']
def nbd(d):
    d = d + datetime.timedelta(days=1)
    while not isbd(d):
        d = d + datetime.timedelta(days=1)
    return d
def last_bd(monday):
    best = None
    for i in range(7):
        x = monday + datetime.timedelta(days=i)
        if isbd(x):
            best = x
    return best
def today():
    raw = str(vars.get(CFG['now_var']) or '')
    return datetime.datetime.strptime(raw[:10], '%Y-%m-%d').date()
def D(s):
    return datetime.date.fromisoformat(str(s)[:10])
def load():
    s = vars.get('neg_state')
    if isinstance(s, str) and s:
        return json.loads(s)
    prods = json.loads(vars.get('products_json'))
    st = dict(phase='first_ask', version=0, rb_version=-1, seen=[], rec_pending=None, rec_sc=0, rec_fc=0, products=[])
    for p in prods:
        st['products'].append(dict(id=p['id'], name=p['name'], full=p['past_due'], floor=p['floor'], deadline=p['deadline'],
                                   allowed=int(p.get('attempts') or 0), used=0, too_much=False, floor_offered=False, below_offered=False,
                                   initial_refused=False, status='open', offer=None, agreed=None, refused=[], vague=0, clamped=False, rec_attempts=0))
    return st
def save(st):
    vars['neg_state'] = json.dumps(st)
def package(st):
    return [[p['id'], money(p['agreed']['amount']), p['agreed']['date']] for p in st['products'] if p['status'] == 'agreed' and p.get('agreed')]
def can_confirm(st):
    pkg = package(st)
    return st['phase'] == 'readback' and st['rb_version'] == st['version'] and bool(pkg) and st.get('rb_pkg') == pkg
def transferred():
    return str(vars.get('transfer_to_agent_response.data.' + CFG['ok']) or '').strip().lower() == 'true'
'''

ENGINE = HELPERS + r'''
def ladder_offer(p, k, t):
    step = CFG['ladder'][k - 1]
    if step['amount'] == 'floor' and p['floor'] is not None:
        amt = p['floor']
    elif step['amount'] == 'full_or_floor_if_too_much' and p['too_much'] and p['floor'] is not None:
        amt = p['floor']
    else:
        amt = p['full']
    if step['date'] == 'deadline':
        d = D(p['deadline'])
    elif step['date'] == 'this_week_last_business_day_or_next_week_if_today':
        mon = t - datetime.timedelta(days=t.weekday())
        d = last_bd(mon)
        if d is None or d <= t:
            d = last_bd(mon + datetime.timedelta(days=7))
    elif step['date'] == 'next_business_day':
        d = nbd(t)
    else:
        d = t
    return amt, d
def offer(p, amt, d, kind, out, named):
    p['offer'] = dict(amount=float(amt), date=d.isoformat(), kind=kind)
    p['status'] = 'offered'
    key = {'floor_too_much': 'floor_offer', 'below_floor': 'below_floor'}.get(kind, 'offer')
    txt = say(key, amount=money(amt), date=sp(d), name=p['name'])
    if named and key == 'offer':
        txt = say('offer_named', amount=money(amt), date=sp(d), name=p['name'])
    out.append(txt)
def next_attempt(p, t, out, named):
    if p.get('hs'):
        # A32: after a hardship no persuasion attempt is made; a refusal closes the product as hardship
        p['status'] = 'hardship'
        p['offer'] = None
        return
    while p['used'] < min(p['allowed'], len(CFG['ladder'])):
        p['used'] += 1
        amt, d = ladder_offer(p, p['used'], t)
        if [round(float(amt), 2), d.isoformat()] in p['refused']:
            continue
        offer(p, amt, d, 'attempt', out, named)
        return
    p['status'] = 'refused'
    p['offer'] = None
def refuse(p, t, out, named):
    if p['offer']:
        p['refused'].append([round(p['offer']['amount'], 2), p['offer']['date']])
    p['offer'] = None
    next_attempt(p, t, out, named)
def judge_date(p, d, t):
    dl = D(p['deadline'])
    if d < t:
        return 'past', None
    if d > dl:
        return 'after', dl
    if not isbd(d):
        return 'not_bd', nbd(d)
    return 'ok', d
def current_amount(p):
    if p.get('pending_amount') is not None:
        return p['pending_amount']
    if p['offer']:
        return p['offer']['amount']
    return p['full']
def propose(p, date_s, amt_s, t, out, named, shared):
    amt = None
    if amt_s not in (None, ''):
        amt = float(amt_s)
        if not math.isfinite(amt):
            raise ValueError('amount not finite')
        if p['floor'] is not None and amt < p['floor'] - 0.005:
            if not p['below_offered']:
                p['below_offered'] = True
                d0 = t if isbd(t) else nbd(t)
                if date_s not in (None, '', 'vague') and re.match(r'^\d{4}-\d{2}-\d{2}$', str(date_s)):
                    v, dd = judge_date(p, D(date_s), t)
                    if v == 'ok':
                        d0 = dd
                offer(p, p['floor'], d0, 'below_floor', out, named)
            else:
                refuse(p, t, out, named)
            return
        amt = min(amt, p['full'])
    ds = str(date_s or '').strip().lower()
    if ds == '':
        if amt is None:
            out.append(say('error'))
            return
        d0 = D(p['offer']['date']) if p['offer'] else (t if isbd(t) else nbd(t))
        offer(p, amt, d0, 'amount_only', out, named)
        return
    if ds == 'vague' or not re.match(r'^\d{4}-\d{2}-\d{2}$', ds):
        if amt is not None:
            p['pending_amount'] = float(amt)
        p['vague'] += 1
        if p['vague'] <= int(CFG['vague_asks']):
            out.append(say('ask_exact'))
        else:
            offer(p, amt if amt is not None else current_amount(p), D(p['deadline']), 'vague_deadline', out, named)
            out[-1] = say('vague_deadline', deadline=sp(D(p['deadline'])), amount=money(p['offer']['amount']), name=p['name'])
        return
    v, dd = judge_date(p, D(ds), t)
    a = amt if amt is not None else current_amount(p)
    if v == 'ok':
        p['agreed'] = dict(amount=float(a), date=dd.isoformat())
        p['status'] = 'agreed'
        p['offer'] = None
        p['pending_amount'] = None
    elif v == 'past':
        out.append(say('past', day=sp(D(ds))))
    elif v == 'not_bd':
        offer(p, a, dd, 'next_bd', out, named)
        out[-1] = say('not_business_day', day=sp(D(ds)), next=sp(dd), amount=money(a), name=p['name'])
    else:
        if shared and CFG['shared_date_clamps']:
            p['agreed'] = dict(amount=float(a), date=dd.isoformat())
            p['status'] = 'agreed'
            p['clamped'] = True
            p['offer'] = None
            p['pending_amount'] = None
        else:
            offer(p, a, dd, 'after_deadline', out, named)
            out[-1] = say('after_deadline', deadline=sp(dd), amount=money(a), name=p['name'])
out, phase_note = [], ''
try:
    st = load()
    t = today()
    named = len(st['products']) > 1
    evs = params.get('events') if isinstance(params, dict) else None
    if isinstance(evs, dict):
        evs = [evs]
    if not isinstance(evs, list) or not evs:
        raise ValueError('no events')
    turn = str(sum(int(float(vars.get(k) or 0)) for k in CFG['turn_vars']))
    # one customer message is judged as a whole: a proposal is never a refusal (A29); 'not today' + 'too much' is one
    # floor offer (A26/A30); a confirmation given together with any change is not a confirmation (A35, B7)
    E = [dict(e, type=str(e.get('type') or '').strip().lower(), product_id=str(e.get('product_id') or '').strip()) for e in evs if isinstance(e, dict)]
    def touches(a, b):
        return a in ('all', '*') or b in ('all', '*') or a == b
    keep = []
    for e in E:
        kinds = set(x['type'] for x in E if x is not e and touches(x['product_id'], e['product_id']))
        if e['type'] in ('refuses', 'too_much') and kinds & set(['proposes', 'changes', 'pays_today', 'accepts']):
            continue
        if e['type'] == 'refuses' and 'too_much' in kinds:
            continue
        if e['type'] == 'confirms' and [x for x in E if x['type'] != 'confirms']:
            continue
        keep.append(e)
    evs = keep
    # A32: a hardship (named in this message, or mentioned anywhere earlier in the call = extracted flag) is answered once,
    # before any persuasion: the brief's sympathy + support offer is the only reply of that turn (code owns the sentence).
    # The customer's own date/amount said together with it is kept and handled under the date/amount rules after the
    # support offer is answered (one question per turn); 'no' in that turn answered the payment question, not the offer.
    hs_flag = 'yes' in (str(vars.get('hardship_seen') or '').strip().lower(), str(vars.get('hardship_early') or '').strip().lower())
    kinds = [e['type'] for e in evs]
    if not st.get('hardship_handled') and 'declines_support' not in kinds and ('hardship' in kinds or (hs_flag and not set(kinds) & set(['accepts', 'confirms']))):
        props = [e for e in evs if e['type'] in ('proposes', 'pays_today', 'changes')]
        if props:
            st['held'] = props
        # a hardship is the customer's, not a product's: it covers every open product of the call
        evs = [dict(product_id='all' if len(st['products']) > 1 else st['products'][0]['id'], type='hardship')] \
            + [e for e in evs if e['type'] in ('dispute', 'paid')]
    # a dict, not a rebound name: the platform runs this code inside a function, where 'global' fails (chat C2, 11 Oct)
    said = dict(hardship=bool(st.get('hardship_handled')) or str(vars.get('hardship_done') or '') == 'yes')
    hardship_turn = bool([e for e in evs if e['type'] in ('hardship', 'declines_support')]) or bool([p for p in st['products'] if p['status'] == 'hardship_offer'])
    if hardship_turn:
        st['hardship_handled'] = True
        vars['hardship_done'] = 'yes'
    ids = [p['id'] for p in st['products']]

    def handle(e, dedupe=True):
        typ = e['type']
        pid = e['product_id']
        key = '|'.join([turn, pid, typ, str(e.get('date') or ''), str(e.get('amount') or '')])
        if dedupe:
            if key in st['seen']:
                return
            st['seen'].append(key)
        if pid in ('all', '*', ''):
            # a date/amount the customer names after a hardship is still handled (A32 last sentence)
            # and an answer to the open support offer reaches the products it was made for
            ok_st = ('open', 'offered', 'agreed') + (('hardship', 'hardship_offer') if typ in ('proposes', 'changes', 'pays_today') else
                                                     ('hardship_offer',) if typ in ('declines_support', 'refuses', 'stop', 'too_much') else ())
            scope = [p for p in st['products'] if p['status'] in ok_st]
            if pid == '' and len(st['products']) > 1:
                raise ValueError('product not named')
        elif pid in ids:
            scope = [p for p in st['products'] if p['id'] == pid]
        else:
            raise ValueError('unknown product ' + pid)
        shared = len(scope) > 1
        if typ == 'stop':
            # A45 counts the statements ('says twice'); an earlier one is a non-answer to the offer (A30), not a close
            st['stops'] = int(st.get('stops') or 0) + 1
            if st['stops'] < int(CFG.get('stop_close') or 1):
                typ = 'refuses'
        if typ in ('proposes', 'changes', 'accepts', 'refuses', 'too_much', 'pays_today') and st['phase'] == 'readback':
            st['phase'] = 'negotiate'
            st['version'] += 1
        if typ == 'confirms':
            if st['phase'] == 'readback':
                whole = pid in ('all', '*') or [x[0] for x in package(st)] == [pid]
                if whole and can_confirm(st):
                    st['phase'] = 'record'
                    st['confirmed_pkg'] = package(st)
                else:
                    out.append(say('confirm_question'))
                return
            typ = 'accepts'
        for p in scope:
            if typ in ('pays_today', 'proposes', 'changes') and p['status'] in ('hardship', 'hardship_offer'):
                p['status'] = 'open'
                p['hs'] = True
            if typ == 'pays_today':
                propose(p, t.isoformat(), None, t, out, named, shared)
            elif typ in ('proposes', 'changes'):
                d_in, a_in = e.get('date'), e.get('amount')
                if p['status'] == 'agreed' and p.get('agreed'):
                    prev = p['agreed']
                    d_in = d_in if d_in not in (None, '') else prev['date']
                    a_in = a_in if a_in not in (None, '') else prev['amount']
                    p['status'] = 'open'
                    p['agreed'] = None
                    p['clamped'] = False
                propose(p, d_in, a_in, t, out, named, shared)
            elif typ == 'accepts':
                if p['offer'] and p['status'] == 'offered':
                    p['agreed'] = dict(amount=p['offer']['amount'], date=p['offer']['date'])
                    p['status'] = 'agreed'
                    p['offer'] = None
                    p['pending_amount'] = None
            elif typ == 'refuses':
                if p['status'] == 'hardship_offer':
                    p['status'] = 'hardship'
                    continue
                if st['phase'] == 'first_ask' and not p['offer']:
                    p['initial_refused'] = True
                    continue
                if p['status'] in ('open', 'offered'):
                    refuse(p, t, out, named)
            elif typ == 'too_much':
                p['too_much'] = True
                if p.get('hs'):
                    next_attempt(p, t, out, named)
                elif not p['floor_offered'] and p['floor'] is not None:
                    p['floor_offered'] = True
                    if p['used'] == 0 and len(CFG['ladder']) > 0 and p['allowed'] > 0:
                        p['used'] = 1
                        amt, d0 = ladder_offer(p, 1, t)
                    else:
                        d0 = D(p['offer']['date']) if p['offer'] else (t if isbd(t) else nbd(t))
                    offer(p, p['floor'], d0, 'floor_too_much', out, named)
                else:
                    refuse(p, t, out, named)
            elif typ == 'hardship':
                p['hs'] = True
                if p['status'] != 'agreed':       # a date/amount already agreed with the customer is kept
                    p['status'] = 'hardship_offer'
                    p['offer'] = None
            elif typ == 'declines_support':
                if p['status'] in ('hardship_offer', 'open', 'offered'):
                    p['status'] = 'hardship'
                    p['offer'] = None
                    p['hs'] = True
            elif typ in ('dispute', 'paid'):
                p['status'] = typ
                p['offer'] = None
            elif typ == 'stop':
                if p['status'] in ('open', 'offered', 'hardship_offer'):
                    p['status'] = 'hardship' if p['status'] == 'hardship_offer' else 'refused'
            else:
                raise ValueError('unknown event type ' + typ)
        if typ == 'hardship' and not said['hardship']:
            out.append(say('hardship'))
            said['hardship'] = True
        elif typ == 'paid':
            out.append(say('paid'))
        elif typ == 'dispute':
            out.append(say('dispute'))

    for e in evs:
        handle(e)
    # the support offer is answered (declined or passed over): the customer's own date/amount from the hardship turn
    # is now handled under the date and amount rules (A32 last sentence); a held proposal never records by itself
    if st.get('held') and not [p for p in st['products'] if p['status'] == 'hardship_offer']:
        held, st['held'] = st['held'], None
        if not [e for e in evs if e['type'] in ('proposes', 'pays_today', 'changes')]:
            for e in held:
                handle(e, dedupe=False)
    if st['phase'] == 'first_ask':
        st['phase'] = 'negotiate'
    if st['phase'] == 'negotiate':
        active = [p for p in st['products'] if p['status'] in ('open', 'offered', 'hardship_offer')]
        if active and not out:
            p = active[0]
            if p['status'] == 'open':
                if p['initial_refused'] or p['used'] > 0 or named:
                    next_attempt(p, t, out, named)
                else:
                    out.append(say('first_ask_one') if not named else say('offer_named', amount=money(p['full']), date=sp(t) if isbd(t) else sp(nbd(t)), name=p['name']))
                    if p['status'] == 'open':
                        d0 = t if isbd(t) else nbd(t)
                        p['offer'] = dict(amount=float(p['full']), date=d0.isoformat(), kind='initial')
                        p['status'] = 'offered'
        active = [p for p in st['products'] if p['status'] in ('open', 'offered', 'hardship_offer')]
        if not active:
            agreed = [p for p in st['products'] if p['status'] == 'agreed']
            if agreed:
                st['phase'] = 'readback'
                st['version'] += 1
                st['rb_version'] = st['version']
                items = []
                for p in agreed:
                    it = say('readback_item', name=p['name'], amount=money(p['agreed']['amount']), date=sp(D(p['agreed']['date'])))
                    if p['clamped']:
                        it = it.rstrip(' .;,') + '. ' + say('readback_clamped', name=p['name'], deadline=sp(D(p['agreed']['date'])))
                    items.append(it)
                out.append((say('readback_intro') + ' ' + '; '.join(i.rstrip(' .;') for i in items) + '. ' + say('confirm_question')).strip())
                st['rb_pkg'] = package(st)
            else:
                st['phase'] = 'finish'
    if not [x for x in out if x] and st['phase'] == 'negotiate':
        pend = [p for p in st['products'] if p['status'] == 'offered' and p['offer']]
        if pend:
            p = pend[0]
            out.append(say('offer_named' if named else 'offer', amount=money(p['offer']['amount']), date=sp(D(p['offer']['date'])), name=p['name']))
        else:
            out.append(say('error'))
    ans = str(params.get('answer') or '').strip() if isinstance(params, dict) else ''
    ans = re.sub(r'[{}]', '', ans)[:240]
    if hardship_turn:
        ans = ''          # the hardship reply has one owner (code): no second sympathy or extra offer from the model
    save(st)
    vars['neg_say'] = ' '.join(x for x in ([ans] if ans else []) + out if x)
    vars['neg_final_say'] = vars['neg_say'] if st['phase'] == 'finish' else ''
    vars['neg_flag'] = {'record': 'record', 'finish': 'finish'}.get(st['phase'], 'new')
    vars['neg_phase'] = st['phase']
except Exception as e:
    vars['neg_error'] = str(e)[:160]
    vars['neg_say'] = say('error')
    vars['neg_flag'] = 'new'
'''

REC_NEXT = HELPERS + r'''
try:
    st = load()
    sc = int(float(vars.get(CFG['rec_node'] + '_success_count') or 0))
    fc = int(float(vars.get(CFG['rec_node'] + '_failure_count') or 0))
    if st.get('rec_pending'):
        p = [x for x in st['products'] if x['id'] == st['rec_pending']][0]
        okv = str(vars.get(CFG['rec_node'] + '_response.data.' + CFG['ok']) or '').strip().lower() == 'true'
        if sc > st['rec_sc'] and okv:
            p['status'] = 'recorded'
        elif p['rec_attempts'] >= 1 + int(CFG['retries']):
            p['status'] = 'service_error'
        st['rec_pending'] = None
    go = 'done'
    pkg = dict((x[0], x) for x in (st.get('confirmed_pkg') or []))
    if st['phase'] != 'record' or not pkg or transferred():
        go = 'blocked'
    for p in st['products'] if go == 'done' else []:
        if p['status'] == 'agreed' and p['rec_attempts'] < 1 + int(CFG['retries']):
            item = pkg.get(p['id'])
            if item is None or item != [p['id'], money(p['agreed']['amount']), p['agreed']['date']]:
                go = 'blocked'
                break
            p['rec_attempts'] += 1
            st['rec_pending'] = p['id']
            st['rec_sc'], st['rec_fc'] = sc, fc
            st.setdefault('writes', []).append(list(item))
            vars['rec_product'], vars['rec_amount'], vars['rec_date'] = item[0], item[1], item[2]
            go = 'yes'
            break
    if go == 'done':
        st['phase'] = 'finish'
    if go == 'blocked':
        vars['neg_flag'] = 'used'   # back in the negotiation, a stale 'record' flag must not route here again
    save(st)
    vars['rec_go'] = go
except Exception as e:
    vars['rec_error'] = str(e)[:160]
    vars['rec_go'] = 'done'
'''

FINISH = HELPERS + r'''
try:
    st = load()
    q = str(vars.get('transfer_to_agent_args.' + CFG['queue_field']) or '')
    t_ok = str(vars.get('transfer_to_agent_response.data.' + CFG['ok']) or '').strip().lower() == 'true'
    rec = [p for p in st['products'] if p['status'] == 'recorded']
    words = [str(vars.get('neg_final_say') or '').strip()]
    if rec:
        words.append(say('recorded'))
        if CFG['after_promise_sentence'] and CFG['after_promise_sentence'].strip(' .') not in ' '.join(words):
            words.append(CFG['after_promise_sentence'])
    for p in st['products']:
        if p['status'] == 'service_error':
            words.append(say('not_recorded', name=p['name']))
    notes = []
    vars['fin_ready'] = 'yes'
    unresolved = [p['id'] for p in st['products'] if p['status'] in ('open', 'offered', 'hardship_offer')
                  or (p['status'] == 'agreed' and p['rec_attempts'] < 1 + int(CFG['retries']))]
    if t_ok and q in CFG['queue_reason']:
        outcome, reason = CFG['transferred'], CFG['queue_reason'][q]
    elif unresolved and int(st.get('finish_blocked') or 0) < 2:
        st['finish_blocked'] = int(st.get('finish_blocked') or 0) + 1
        save(st)
        vars['fin_ready'] = 'no'
        vars['fin_unresolved'] = ','.join(unresolved)
        vars['neg_flag'] = 'used'
        raise StopIteration()
    else:
        if unresolved:
            vars['fin_unresolved'] = ','.join(unresolved)
        for p in st['products']:
            if p['id'] in unresolved:
                continue
            if p['status'] != 'recorded':
                notes.append([p['id'], CFG['statuses'][p['status']]])
        if rec:
            outcome, reason = CFG['promise'], ''
        elif unresolved:
            outcome, reason = CFG['technical']['outcome'], CFG['technical']['reason']
        elif notes and all(n[1] == CFG['statuses']['paid'] for n in notes):
            outcome, reason = CFG['paid'], ''
        else:
            first = [p for p in st['products'] if p['status'] != 'paid'][0]
            outcome, reason = CFG['no_promise'], CFG['statuses'][first['status']]
        if not CFG['uses_notes']:
            notes = []
    if outcome in CFG['no_reason']:
        reason = ''
    st['notes'] = notes
    st['phase'] = 'closing'
    save(st)
    words.append(CFG['goodbye'])
    vars['fin_say'] = ' '.join(w for w in words if w)
    vars['fin_outcome'] = outcome
    vars['fin_reason'] = reason
except StopIteration:
    pass
except Exception as e:
    vars['fin_error'] = str(e)[:160]
    vars['fin_say'] = CFG['goodbye']
    vars['fin_outcome'] = CFG['technical']['outcome']
    vars['fin_reason'] = CFG['technical']['reason']
'''

CONFIRM = HELPERS + r'''
try:
    st = load()
    if can_confirm(st):
        st['phase'] = 'record'
        st['confirmed_pkg'] = package(st)
        vars['neg_flag'] = 'record'
    else:
        vars['neg_flag'] = 'used'
    vars['rb_answer'] = 'consumed'
    save(st)
except Exception as e:
    vars['confirm_error'] = str(e)[:160]
    vars['neg_flag'] = 'used'
'''

HARDSHIP = HELPERS + r'''
try:
    if str(vars.get('hardship_done') or '') != 'yes':
        st = load()
        for p in st['products']:
            if p['status'] in ('open', 'offered'):
                p['status'] = 'hardship_offer'
                p['offer'] = None
                p['hs'] = True
        st['hardship_handled'] = True
        if st['phase'] == 'first_ask':
            st['phase'] = 'negotiate'
        save(st)
        vars['neg_say'] = say('hardship')
        vars['neg_phase'] = st['phase']
    vars['hardship_done'] = 'yes'
    vars['neg_flag'] = 'used'
except Exception as e:
    vars['hardship_error'] = str(e)[:160]
    vars['hardship_done'] = 'yes'
    vars['neg_say'] = say('hardship')
    vars['neg_flag'] = 'used'
'''

CLOSE_CHECK = r'''
import json
CFG = json.loads(r"""__CFG__""")
try:
    sc = int(float(vars.get('close_one_success_count') or 0))
    okv = str(vars.get('close_one_response.data.' + CFG['ok']) or '').strip().lower() == 'true'
    vars['close_result'] = 'ok' if (sc > 0 and okv) else 'failed'
except Exception as e:
    vars['close_result'] = 'unknown: ' + str(e)[:80]
'''

NOTES_NEXT = HELPERS + r'''
try:
    st = load()
    sc = int(float(vars.get(CFG['note_node'] + '_success_count') or 0))
    fc = int(float(vars.get(CFG['note_node'] + '_failure_count') or 0))
    if st.get('note_pending'):
        okv = str(vars.get(CFG['note_node'] + '_response.data.' + CFG['ok']) or '').strip().lower() == 'true'
        res = 'ok' if (sc > int(st.get('note_sc') or 0) and okv) else 'failed'
        st.setdefault('note_results', []).append(st['note_pending'] + [res])
        st['note_pending'] = None
        vars['note_failures'] = str(len([r for r in st['note_results'] if r[2] != 'ok']))
    notes = st.get('notes') or []
    if notes:
        n = notes.pop(0)
        st['note_pending'], st['note_sc'], st['note_fc'] = [n[0], n[1]], sc, fc
        vars['note_product'], vars['note_reason'] = n[0], n[1]
        vars['note_go'] = 'yes'
    else:
        vars['note_go'] = 'done'
    st['notes'] = notes
    save(st)
except Exception as e:
    vars['note_error'] = str(e)[:160]
    vars['note_go'] = 'done'
'''


def embed(code, cfg):
    cfg_json = json.dumps(cfg, indent=1)
    out = code.replace("__CFG__", cfg_json)
    if "{{" in out or "}}" in out or '"""' in cfg_json:
        raise ValueError("generated code would contain '{{', '}}' or triple quotes")
    return out


EVENT_TYPES = ["pays_today", "refuses", "too_much", "proposes", "accepts", "confirms", "changes",
               "hardship", "declines_support", "dispute", "paid", "stop"]
