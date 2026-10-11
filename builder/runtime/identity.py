"""Identity runtime: the dialogue model turns each customer message of the identity stage into events (answer parts,
corrections, refusals, questions); code keeps the state, combines the parts, checks the format, decides whether the
bank is asked, processes the bank's result once, and owns every sentence and the close of this stage.
Only the bank decides whether an answer is right. Every value comes from CFG (built from policy.json).

State (vars['id_state'], one JSON object per call; a new call starts without it):
  active          index of the question being asked (the first one the bank has not verified)
  parts[field]    the answer heard so far: date -> day/month/year, digits -> digits (a string: leading zeros kept), text
  rev[field]      answer revision; the pending request carries (field, revision, answer)
  verified        fields the bank verified in this call
  pending         the request for the bank and the verify node's counters right before it was sent (sc, fc):
                  a result is processed only when the success counter moved past sc, and only once
  declines        refusals / 'what is this about' instead of an answer / 'do not want to talk' (at most one per message)
  humans          requests for a person; wrong_local (only when the API has no remaining-tries field); svc (service errors)
  cand[field]     after a day/month hint: the two numbers heard, so a month said as a word completes the date
  done            None | verified | failed | declined | transferred | technical
Outcomes: failed only on the bank's current result (not verified and no tries left); declined on the policy's count;
the account is reached only when the bank's current result says every question passed (security_verified='yes').

Event/transition table (one customer message = one call of ID_EVENT):
  human           first time(s): the policy's 'can I help first' sentence; after that: engine-run transfer
  answer          parts for the named (or active) question; a question already verified is never sent again
  correction      replaces the parts it names (digits: the whole answer)
  refuses / stop / asks_purpose (only without an answer in the same message)
                  -> one decline; the first is answered with the policy's explanation; the policy's count closes 'declined'
  robot / scam    the policy's answer, then the step continues
  other           the step continues (the open question or its missing part is asked)
After the events: active question complete and valid -> one verify request; incomplete -> only the missing part is asked;
invalid (not a calendar date, too many digits) -> 'could not read' + the question again (no bank call, nothing counted).
"""

ID_HELPERS = r'''
import json, datetime, re
CFG = json.loads(r"""__CFG__""")
MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
class Safe(dict):
    def __missing__(self, k):
        return ''
def say(key, **kw):
    t = CFG['say'].get(key) or ''
    return t.format_map(Safe(kw)).strip()
def yes(x):
    return str(x).strip().lower() == 'true'
def as_int(x):
    s = str('' if x is None else x).strip()
    if re.match(r'^-?\d+(\.0+)?$', s):
        return int(float(s))
    return None
def load():
    s = vars.get('id_state')
    if isinstance(s, str) and s:
        return json.loads(s)
    return dict(active=0, parts=dict(), rev=dict(), verified=[], pending=None, declines=0, explained=False, humans=0,
                wrong_local=0, svc=0, cand=dict(), done=None, prefix='')
def save(st):
    vars['id_state'] = json.dumps(st)
def qs():
    return CFG['questions']
def qby(field):
    for q in qs():
        if q['field'] == field:
            return q
    return None
def first_open(st):
    for i, q in enumerate(qs()):
        if q['field'] not in st['verified']:
            return i
    return None
def ask_text(st):
    i = first_open(st)
    return qs()[i]['ask'] if i is not None else ''
def joined(words):
    return ' '.join(w.strip() for w in words if w and w.strip())
def close(st, key, outcome_key, words):
    st['done'] = key
    o = CFG[outcome_key]
    vars['fin_say'] = joined(words + [CFG['goodbye']])
    vars['fin_outcome'] = o['outcome']
    vars['fin_reason'] = '' if o['outcome'] in CFG['no_reason'] else str(o.get('reason') or '')
    vars['id_flag'] = 'close'
def date_parts(e):
    out = dict()
    for k in ('day', 'month', 'year'):
        v = str(e.get(k) or '').strip().lower()
        if not v:
            continue
        if k == 'month' and v in MONTHS:
            out[k] = MONTHS.index(v) + 1
            continue
        dg = re.sub(r'\D', '', v)
        if not dg:
            continue                    # not given as digits: that part is asked again, the parts heard are kept
        elif k == 'year' and len(dg) != 4:
            out[k] = 'short'
        else:
            out[k] = int(dg)
    return out
def complete(q, p):
    """-> ('ok', answer) | ('missing', [part names]) | ('bad', None)"""
    k = q['kind']
    if k == 'date':
        if [x for x in ('day', 'month', 'year') if p.get(x) == 'bad']:
            return 'bad', None
        miss = [x for x in ('day', 'month', 'year') if p.get(x) in (None, '', 'short')]
        if miss:
            return 'missing', miss
        try:
            d = datetime.date(int(p['year']), int(p['month']), int(p['day']))
        except Exception:
            return 'bad', None
        return 'ok', q['output'].replace('YYYY', '%04d' % d.year).replace('MM', '%02d' % d.month).replace('DD', '%02d' % d.day)
    if k == 'digits':
        s = str(p.get('digits') or '')
        n = int(q['digits'])
        if len(s) < n:
            return 'missing', ['digits']
        if len(s) > n:
            return 'bad', None
        return 'ok', s
    s = str(p.get('text') or '').strip()
    return ('ok', s) if s else ('missing', ['text'])
def missing_say(miss):
    names = [say('part_' + m) or m for m in miss]
    both = names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' ' + (say('and_word') or 'and') + ' ' + names[-1]
    return say('ask_missing', missing=both)
def next_step(st, words):
    """After the state changed: send the active question's complete answer to the bank, or ask for what is missing."""
    i = first_open(st)
    if i is None:
        vars['id_error'] = 'every question verified but no full verification from the bank'
        close(st, 'technical', 'technical', words + [say('service_error')])
        return
    q = qs()[i]
    st['active'] = i
    p = st['parts'].get(q['field']) or dict()
    if not [x for x in p.values() if x not in (None, '')]:
        vars['id_say'] = joined(words + [q['ask']])
        vars['id_flag'] = 'say'
        return
    state, ans = complete(q, p)
    if state == 'ok':
        st['pending'] = dict(field=q['field'], answer=ans, rev=int(st['rev'].get(q['field']) or 0), tries=0, sc=None, fc=None)
        st['prefix'] = joined(words)
        vars['id_field'] = q['field']
        vars['id_answer'] = ans
        vars['id_flag'] = 'verify'
    elif state == 'bad':
        st['parts'][q['field']] = dict()
        vars['id_say'] = joined(words + [say('unreadable'), q['ask']])
        vars['id_flag'] = 'say'
    else:
        vars['id_say'] = joined(words + [missing_say(ans)])
        vars['id_flag'] = 'say'
'''

ID_EVENT = ID_HELPERS + r'''
def apply_answer(st, q, e, correction):
    f = q['field']
    p = dict(st['parts'].get(f) or dict())
    before = json.dumps(p, sort_keys=True)
    if q['kind'] == 'date':
        new = date_parts(e)
        cand = st['cand'].get(f)
        if cand and len(cand) == 2 and isinstance(new.get('month'), int) and 'day' not in new and new['month'] in cand:
            # after a day/month hint: the month said as a word picks one of the two numbers heard; the other is the day
            rest = list(cand)
            rest.remove(new['month'])
            new['day'] = rest[0]
        if new:
            st['cand'].pop(f, None)
        p.update(new)
    elif q['kind'] == 'digits':
        d = re.sub(r'\D', '', str(e.get('digits') or ''))
        if not d:
            return
        n = int(q['digits'])
        cur = str(p.get('digits') or '')
        if correction or len(d) >= n or not cur or len(cur) + len(d) > n:
            p['digits'] = d                 # a whole new answer (or a correction) replaces what was heard
        else:
            p['digits'] = cur + d           # the next part of the same answer, kept as text: '15' + '02' -> '1502'
    else:
        t = str(e.get('text') or '').strip()
        if t:
            p['text'] = t
    if json.dumps(p, sort_keys=True) != before:
        st['parts'][f] = p
        st['rev'][f] = int(st['rev'].get(f) or 0) + 1
try:
    st = load()
    evs = params.get('events') if isinstance(params, dict) else None
    if isinstance(evs, dict):
        evs = [evs]
    if not isinstance(evs, list):
        evs = []
    E = [dict(e, type=str(e.get('type') or '').strip().lower(), field=str(e.get('field') or '').strip()) for e in evs if isinstance(e, dict)]
    if st.get('done'):
        vars['id_flag'] = 'used'
        raise StopIteration()
    kinds = [e['type'] for e in E]
    answers = [e for e in E if e['type'] in ('answer', 'correction')]
    words = [CFG[k] for k in ('robot', 'scam') if k in kinds and CFG.get(k)]
    if 'human' in kinds:
        st['humans'] = int(st.get('humans') or 0) + 1
        if st['humans'] > int(CFG['human']['asks_before_transfer']):
            st['done'] = 'transferred'
            vars['xfer_queue'] = CFG['human']['queue']
            vars['id_flag'] = 'transfer'
            save(st)
            raise StopIteration()
        if not answers:
            vars['id_say'] = joined(words + [CFG['human']['say']])
            vars['id_flag'] = 'say'
            save(st)
            raise StopIteration()
    act = first_open(st)
    for e in answers:
        q = qby(e['field']) if e['field'] else None
        if q is None and act is not None:
            q = qs()[act]
        if q is None or q['field'] in st['verified']:
            continue                        # a question the bank already passed is not asked or sent again
        apply_answer(st, q, e, e['type'] == 'correction')
    if not answers and [e for e in E if e['type'] in ('refuses', 'stop', 'asks_purpose')]:
        st['declines'] = int(st.get('declines') or 0) + 1
        if st['declines'] >= int(CFG['declines_to_close']):
            close(st, 'declined', 'declined', words)
            save(st)
            raise StopIteration()
        if not st.get('explained'):
            st['explained'] = True
            words.append(say('decline_explain'))
    next_step(st, words)
    save(st)
except StopIteration:
    pass
except Exception as e:
    vars['id_error'] = str(e)[:160]
    try:
        vars['id_say'] = joined([say('unreadable'), ask_text(load())])
    except Exception:
        vars['id_say'] = say('unreadable')
    vars['id_flag'] = 'say'
'''

# right before the engine-run verify call: binds the pending request to the verify node's counters at that moment
ID_SEND = ID_HELPERS + r'''
try:
    st = load()
    p = st.get('pending')
    node = CFG['verify_node']
    if p and not st.get('done'):
        p['sc'] = int(float(vars.get(node + '_success_count') or 0))
        p['fc'] = int(float(vars.get(node + '_failure_count') or 0))
        st['sends'] = int(st.get('sends') or 0) + 1
        p['req'] = 'r' + str(st['sends'])
        vars['id_req'] = p['req']
        vars['id_field'], vars['id_answer'] = p['field'], p['answer']
        vars['id_go'] = 'yes'
    else:
        vars['id_go'] = 'no'
        vars['id_say'] = ask_text(st)
    save(st)
except Exception as e:
    vars['id_error'] = str(e)[:160]
    vars['id_go'] = 'no'
    vars['id_say'] = say('service_error')
'''

ID_RESULT = ID_HELPERS + r'''
try:
    st = load()
    node = CFG['verify_node']
    sc = int(float(vars.get(node + '_success_count') or 0))
    fc = int(float(vars.get(node + '_failure_count') or 0))
    p = st.get('pending')
    if st.get('done'):
        vars['id_flag'] = 'used'
        raise StopIteration()
    if not p or p.get('sc') is None:
        # no request of this call waits for a result (e.g. a repeated entry): nothing is processed again
        vars['id_say'] = ask_text(st)
        vars['id_flag'] = 'say'
        raise StopIteration()
    if sc > int(p['sc']):
        st['pending'] = None
        rec = None
        try:
            rec = json.loads(str(vars.get('id_res') or ''))
        except Exception:
            rec = None
        fresh = isinstance(rec, dict) and rec.get('req') == p.get('req') and isinstance(rec.get('data'), dict)
        if fresh:
            g = lambda k: rec['data'].get(CFG['f'].get(k)) if CFG['f'].get(k) else None
        else:
            g = lambda k: vars.get(node + '_response.data.' + str(CFG['f'].get(k))) if CFG['f'].get(k) else None
        st['fresh'] = int(st.get('fresh') or 0) + (1 if fresh else 0)
        okv = yes(g('ok'))
        hint = str(g('hint') or '').strip()
        rem = as_int(g('remaining'))
        last_rem = st.get('last_rem')
        if rem is not None:
            st['last_rem'] = rem
        f = p['field']
        q = qby(f)
        ask = q['ask'] if q else ''
        words = [st.get('prefix') or '']
        st['prefix'] = ''
        if okv and yes(g('all_verified')):
            if f not in st['verified']:
                st['verified'].append(f)
            st['done'] = 'verified'
            vars['security_verified'] = 'yes'
            vars['id_prefix'] = joined(words + [say('verified_all')])
            vars['id_flag'] = 'account'
        elif rem is not None and rem <= 0:
            # the bank's current result: no tries left (a 0 seen earlier would already have closed the call)
            close(st, 'failed', 'failed', words + [say('failed')])
        elif okv and yes(g('verified')):
            if f not in st['verified']:
                st['verified'].append(f)
            next_step(st, words + [say('verified_one')])
        elif hint and hint in CFG['hint_say'] and (fresh or not st.get('hints_seen') or (rem is not None and rem == last_rem)):
            # the bank's hint: not a wrong answer; the parts it concerns are asked again (the year is kept). Without the
            # post-hook's record a hint key can be left over from an earlier response: then it counts only while the
            # bank's remaining tries did not drop (a hint never uses a try)
            st['hints_seen'] = True
            old = st['parts'].get(f) or dict()
            if q and q['kind'] == 'date' and isinstance(old.get('day'), int) and isinstance(old.get('month'), int):
                st['cand'][f] = [old['day'], old['month']]
                st['parts'][f] = dict(year=old.get('year'))
            else:
                st['parts'][f] = dict()
            vars['id_say'] = joined(words + [CFG['hint_say'][hint]])
            vars['id_flag'] = 'say'
        elif not okv:
            # not checked (unreadable, or refused by the service): not a wrong answer; asked again
            st['parts'][f] = dict()
            vars['id_say'] = joined(words + [say('unreadable'), ask])
            vars['id_flag'] = 'say'
        else:
            if rem is None and CFG.get('max_wrong'):
                st['wrong_local'] = int(st.get('wrong_local') or 0) + 1
            if rem is None and CFG.get('max_wrong') and st['wrong_local'] >= int(CFG['max_wrong']):
                close(st, 'failed', 'failed', words + [say('failed')])
            else:
                st['parts'][f] = dict()
                vars['id_say'] = joined(words + [say('wrong'), ask])
                vars['id_flag'] = 'say'
    else:
        # the call did not succeed (HTTP error, or no result): nothing was checked and nothing counts as wrong
        p['tries'] = int(p.get('tries') or 0) + 1
        if p['tries'] <= int(CFG['verify_retries']):
            vars['id_flag'] = 'verify'
        else:
            st['pending'] = None
            st['svc'] = int(st.get('svc') or 0) + 1
            if st['svc'] >= int(CFG['service_errors_to_close']):
                close(st, 'technical', 'technical', [st.get('prefix') or '', say('service_error')])
            else:
                st['parts'][p['field']] = dict()
                q = qby(p['field'])
                vars['id_say'] = joined([st.get('prefix') or '', say('service_error'), q['ask'] if q else ''])
                vars['id_flag'] = 'say'
            st['prefix'] = ''
    save(st)
except StopIteration:
    pass
except Exception as e:
    vars['id_error'] = str(e)[:160]
    vars['id_say'] = say('service_error')
    vars['id_flag'] = 'say'
'''

ID_POST = r'''
import json
CFG = json.loads(r"""__CFG__""")
try:
    if isinstance(result, dict):
        result.pop('header', None)
        d = result.get('data')
        if isinstance(d, dict):
            vars['id_res'] = json.dumps(dict(req=str(vars.get('id_req') or ''), data=d))
            for k in CFG['keys']:
                if k and k not in d:
                    d[k] = ''
except Exception:
    pass
'''

ID_CONSUME = "vars['id_flag'] = 'used'\n"

# engine-run transfer (identity: a person insisted on; negotiation: the support offer accepted)
XFER_PREP = r'''
import json
CFG = json.loads(r"""__CFG__""")
try:
    vars['xfer_sc_before'] = str(int(float(vars.get(CFG['node'] + '_success_count') or 0)))
except Exception:
    vars['xfer_sc_before'] = '0'
'''

XFER_CHECK = r'''
import json
CFG = json.loads(r"""__CFG__""")
try:
    sc = int(float(vars.get(CFG['node'] + '_success_count') or 0))
    okv = str(vars.get(CFG['node'] + '_response.data.' + CFG['ok']) or '').strip().lower() == 'true'
    vars['xfer_done'] = 'yes' if (sc > int(float(vars.get('xfer_sc_before') or 0)) and okv) else 'failed'
except Exception as e:
    vars['xfer_error'] = str(e)[:160]
    vars['xfer_done'] = 'failed'
'''

EVENT_TYPES = ["answer", "correction", "refuses", "asks_purpose", "stop", "robot", "scam", "human", "other"]
