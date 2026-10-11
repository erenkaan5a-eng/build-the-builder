import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://bank-mock-final.erenkaan5a.workers.dev/voice/v1/"

def cond(var, op, operand=None):
    c = {"variable": var, "operator": op}
    if operand is not None:
        c["operand"] = operand
        c["mode"] = "exact"
    return c

def eq(var, val):
    return {"logic": "or", "conditions": [cond(var, "equals", val)]}

def gt0(var):
    return {"logic": "or", "conditions": [cond(var, "greater_than", 0)]}

def tr(target, condition, desc):
    return {"target_node": target, "description": desc, "condition": condition}

ALWAYS = {"operator": "always"}

def base(name, ntype, **kw):
    n = {"name": name, "node_type": ntype, "assertions": [], "truncation_strategy": "keep_all"}
    n.update(kw)
    return n

def code_node(name, code, transitions, default):
    return base(name, "code", passthrough=True, passthrough_default_transition=default,
                on_enter={"type": "silent"}, disable_inactivity_monitor=True,
                pre_actions=[{"type": "function", "function": {"name": "code_exec", "handler": "__function__:code_exec",
                    "parameters": {"type": "object", "properties": {
                        "code": {"type": "string", "default": code},
                        "timeout_ms": {"type": "number", "default": 10000}}}}}],
                transitions=transitions)

HDRS = {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}}
CALL = {"type": "object", "properties": {"lang": {"type": "string", "default": "tr"}}}

def api_fn(name, endpoint, data_props, desc, retries=0, hook=None, mapping=None, timeout=15000, required=None):
    f = {"type": "function", "config": {"timeoutMs": timeout, "maxRetries": retries},
         "function": {"name": name, "handler": "__function__:api_call", "description": desc,
                      "parameters": {"type": "object", "properties": {
                          "url": {"type": "string", "default": BASE + endpoint},
                          "method": {"type": "string", "default": "POST"},
                          "headers": HDRS,
                          "body": {"type": "object", "required": ["data"], "properties": {
                              "data": {"type": "object", "properties": data_props},
                              "call": CALL}}}}}}
    if hook:
        f["function"]["post_process_code"] = hook
    if mapping:
        f["response_mapping"] = mapping
    return f

def hook(msg_ok, msg_bad):
    return ("try:\n    if isinstance(result, dict):\n        result.pop('header', None)\n        d = result.get('data')\n"
            "        if not isinstance(d, dict):\n            d = {}\n            result['data'] = d\n"
            "        d['what_to_do_next'] = %r\nexcept Exception:\n    pass\n" % msg_ok)

def sf(default, typ="string"):
    return {"type": typ, "default": default}

def api_node(name, endpoint, data_props, mapping, ok, fail, retries=1):
    fn = {"type": "function", "config": {"timeoutMs": 20000, "maxRetries": retries},
          "function": {"name": name, "handler": "__function__:api_call", "description": name,
                       "parameters": {"type": "object", "properties": {
                           "url": {"type": "string", "default": BASE + endpoint},
                           "method": {"type": "string", "default": "POST"},
                           "headers": HDRS,
                           "body": {"type": "object", "required": ["data"], "properties": {
                               "data": {"type": "object", "properties": data_props}, "call": CALL}}}}}}
    return base(name, "api_request", passthrough=True, passthrough_default_transition=ok,
                on_enter={"type": "silent"}, disable_inactivity_monitor=True, pre_actions=[fn],
                response_mapping=mapping,
                transitions=[tr(fail, gt0(name + "_failure_count"), "service error"), tr(ok, ALWAYS, "always")])

def end_node(name, fname, text):
    return base(name, "end_call", on_enter={"type": "silent"}, disable_inactivity_monitor=True, transitions=[],
                terminal={"type": "function", "function": {"name": fname, "handler": "__function__:end_call",
                    "parameters": {"type": "object", "properties": {
                        "message_mode": {"type": "string", "default": "custom"},
                        "spoken_message": {"type": "string", "default": text}}}}})

def conv(name, task, on_enter=None, tools=None, extraction=None, transitions=None, max_turns=12, fallback="end_giveup"):
    n = base(name, "conversation", passthrough=False, role_message="", task_message=task, interruptible=False,
             max_node_turns=max_turns, max_turn_transition=fallback, disable_inactivity_monitor=False,
             response_mapping=[], extraction_schema=extraction or [], transitions=transitions or [])
    n["on_enter"] = on_enter or {"type": "silent"}
    if tools:
        n["tools"] = tools
    return n

def ext(name, desc, enum=None):
    f = {"name": name, "type": "string", "description": desc, "min_confidence": 0.6}
    if enum:
        f["enum"] = enum
    return f

# ---------------- code snippets ----------------
INIT = """try:
    now = str(vars.get('now') or '').strip()
    cust = str(vars.get('customerNumber') or '').strip()
    ok = len(now) >= 10 and len(cust) > 0
    vars['init_state'] = 'ok' if ok else 'missing'
    vars['today_iso'] = now[:10]
    vars['card_tries'] = '0'
except Exception:
    vars['init_state'] = 'missing'
"""

CARDS_PREP = """try:
    nums = []; l4 = []; names = []
    for i in range(30):
        n = vars.get('fetch_cards_response.data.cards.%d.cardNumber' % i)
        if n is None or str(n) == '':
            break
        st = str(vars.get('fetch_cards_response.data.cards.%d.status' % i) or 'A')
        mainc = str(vars.get('fetch_cards_response.data.cards.%d.isMainCard' % i)).strip().lower()
        if st != 'A' or mainc == 'false':
            continue
        nums.append(str(n))
        l4.append(str(vars.get('fetch_cards_response.data.cards.%d.cardNumberLast4' % i) or str(n)[-4:]))
        names.append(str(vars.get('fetch_cards_response.data.cards.%d.productName' % i) or '').strip())
    vars['card_nums'] = '|'.join(nums)
    vars['card_l4s'] = '|'.join(l4)
    vars['card_names'] = '|'.join(names)
    vars['card_count'] = str(len(nums))
    ex = []
    for nm in names:
        if nm and nm not in ex:
            ex.append(nm)
    vars['card_examples'] = ' veya '.join(ex[:2]) if ex else ''
    vars['card_all_names'] = ', '.join(ex)
    if len(nums) == 0:
        vars['cards_state'] = 'none'
    elif len(nums) == 1:
        vars['cards_state'] = 'one'
        vars['selected_card_number'] = nums[0]
        vars['selected_last4'] = l4[0]
        vars['selected_name'] = names[0]
    else:
        vars['cards_state'] = 'many'
    vars['card_feedback'] = ''
except Exception:
    vars['cards_state'] = 'error'
"""

CARD_RESOLVE = """def low(s):
    return str(s or '').replace('I', 'i').replace('\\u0130', 'i').lower().strip()
try:
    nums = str(vars.get('card_nums') or '').split('|')
    l4s = str(vars.get('card_l4s') or '').split('|')
    names = str(vars.get('card_names') or '').split('|')
    qn = low(vars.get('card_name'))
    q4 = ''.join(ch for ch in str(vars.get('card_last4') or '') if ch.isdigit())
    q4 = q4[-4:] if q4 else ''
    idx = []
    for i in range(len(nums)):
        if qn and qn not in low(names[i]) and low(names[i]) not in qn:
            continue
        if q4 and l4s[i] != q4:
            continue
        idx.append(i)
    tries = int(str(vars.get('card_tries') or '0'))
    vars['card_name'] = ''
    vars['card_last4'] = ''
    if len(idx) == 1 and (qn or q4):
        i = idx[0]
        vars['selected_card_number'] = nums[i]
        vars['selected_last4'] = l4s[i]
        vars['selected_name'] = names[i]
        vars['resolve_state'] = 'ok'
        vars['card_feedback'] = ''
    else:
        tries += 1
        vars['card_tries'] = str(tries)
        if tries >= 3:
            vars['resolve_state'] = 'giveup'
        else:
            vars['resolve_state'] = 'again'
            if len(idx) > 1 and qn and not q4:
                vars['card_feedback'] = '%s isimli birden fazla kartınız var. Kartınızın son dört hanesini söyler misiniz?' % str(vars.get('card_names').split('|')[idx[0]] or qn)
            elif len(idx) > 1:
                vars['card_feedback'] = 'Son dört hanesi aynı olan birden fazla kartınız var. Kart numaranızın tamamını söyler misiniz?'
            elif qn or q4:
                vars['card_feedback'] = 'Bu isimde bir kartınız bulunmuyor. Kartlarınız: %s. Hangisinin borcunu öğrenmek istersiniz?' % str(vars.get('card_all_names') or '')
            else:
                vars['card_feedback'] = 'Hangi kartınızın borcunu öğrenmek istersiniz? Örneğin, %s diyebilirsiniz.' % str(vars.get('card_examples') or '')
except Exception:
    vars['resolve_state'] = 'giveup'
"""

BUILD = """O = ['', 'bir', 'iki', '\\u00fc\\u00e7', 'd\\u00f6rt', 'be\\u015f', 'alt\\u0131', 'yedi', 'sekiz', 'dokuz']
T = ['', 'on', 'yirmi', 'otuz', 'k\\u0131rk', 'elli', 'altm\\u0131\\u015f', 'yetmi\\u015f', 'seksen', 'doksan']
MON = ['Ocak', '\\u015eubat', 'Mart', 'Nisan', 'May\\u0131s', 'Haziran', 'Temmuz', 'A\\u011fustos', 'Eyl\\u00fcl', 'Ekim', 'Kas\\u0131m', 'Aral\\u0131k']
def w3(n):
    h = n // 100; t = (n // 10) % 10; o = n % 10; s = ''
    if h:
        s += ('' if h == 1 else O[h] + ' ') + 'y\\u00fcz '
    if t:
        s += T[t] + ' '
    if o:
        s += O[o] + ' '
    return s.strip()
def w(n):
    if n == 0:
        return 's\\u0131f\\u0131r'
    p = []
    m = n // 1000000; k = (n // 1000) % 1000; r = n % 1000
    if m:
        p.append(w3(m) + ' milyon')
    if k:
        p.append(('' if k == 1 else w3(k) + ' ') + 'bin')
    if r:
        p.append(w3(r))
    return ' '.join(p)
def money(x, unit, sub):
    c = int(round(abs(x) * 100)); a = c // 100; b = c % 100
    s = w(a) + ' ' + unit
    if b:
        s += ' ' + w(b) + ' ' + sub
    return s
def dt(s):
    try:
        d, m, y = str(s).strip().split('.')
        return '%d %s %s' % (int(d), MON[int(m) - 1], y)
    except Exception:
        return ''
def digits(s):
    D = ['s\\u0131f\\u0131r'] + O[1:]
    return ' '.join(D[int(ch)] for ch in str(s) if ch.isdigit())
def num(cur, f):
    try:
        return float(vars.get('bal_%s_%s' % (cur, f)))
    except Exception:
        return None
CUR = [('TL', 'T\\u00fcrk Liras\\u0131', 'lira', 'kuru\\u015f', 'TL'), ('USD', 'Dolar', 'dolar', 'sent', 'USD'),
       ('EUR', 'Euro', 'euro', 'sent', 'EUR'), ('GBP', '\\u0130ngiliz Sterlini', 'sterlin', 'peni', 'GBP')]
try:
    last4 = str(vars.get('selected_last4') or '')
    name = str(vars.get('selected_name') or '').strip()
    sdate = str(vars.get('bal_statementDate') or '').strip()
    nsdate = str(vars.get('bal_nextStatementDate') or '').strip()
    lpd = str(vars.get('bal_lastPayDate') or '').strip()
    nlpd = str(vars.get('bal_nextLastPayDate') or '').strip()
    today = str(vars.get('today_iso') or '')[:10]
    try:
        y, mo, d = today.split('-')
        today_tr = '%s.%s.%s' % (d, mo, y)
    except Exception:
        today_tr = ''
    intro = 'Sonu %s ile biten %s kart\\u0131n\\u0131za' % (digits(last4), name) if name else 'Sonu %s ile biten kart\\u0131n\\u0131za' % digits(last4)
    out = []
    pdf_cur = ''
    vars['pdf_statement_date'] = sdate
    if not sdate:
        out.append('Kart\\u0131n\\u0131z\\u0131n hen\\u00fcz kesilmi\\u015f bir ekstresi olmad\\u0131\\u011f\\u0131 i\\u00e7in ekstre borcunuz bulunmamaktad\\u0131r.')
        if dt(nsdate):
            out.append('\\u0130lk hesap kesim tarihiniz %s olacak.' % dt(nsdate))
        vars['reading_kind'] = 'nostatement'
    elif nsdate and nsdate == today_tr:
        out.append('Hesap kesim tarihiniz bug\\u00fcn, ekstreniz saat s\\u0131f\\u0131r s\\u0131f\\u0131r itibar\\u0131yla kesilecek.')
        nodebt = []
        for c, full, unit, sub, code in CUR:
            tdv = num(c, 'totalDebt')
            if tdv is not None and tdv > 0:
                out.append('%s toplam borcunuz %s %s.' % (full, money(tdv, unit, sub), code))
            else:
                nodebt.append(full)
        if nodebt:
            out.append('%s borcunuz bulunmamaktad\\u0131r.' % ', '.join(nodebt))
        if dt(lpd):
            out.append('Bor\\u00e7lar\\u0131n\\u0131z i\\u00e7in son \\u00f6deme tarihiniz %s\\'d\\u0131r.' % dt(lpd))
        vars['reading_kind'] = 'cutday'
    else:
        has = []
        first = True
        nodebt = []
        for c, full, unit, sub, code in CUR:
            rd = num(c, 'remainingDebt'); sd = num(c, 'statementDebt'); mp = num(c, 'minPayment'); rm = num(c, 'remainingMinPayment')
            if rd is None or sd is None or rd <= 0:
                nodebt.append((c, full))
                continue
            has.append(c)
            if not pdf_cur:
                pdf_cur = c
            lead = ''
            if first:
                lead = '%s %s tarihinde kesilen ekstre ' % (intro, dt(sdate))
                first = False
            if c == 'TL':
                if rm is not None and mp is not None and rm <= 0:
                    s = '%s borcunuz %s, kalan toplam borcunuz %s. Minimum \\u00f6demenizi yapt\\u0131\\u011f\\u0131n\\u0131z i\\u00e7in te\\u015fekk\\u00fcr ederiz.' % (full, money(sd, unit, sub) + ' TL', money(rd, unit, sub) + ' TL')
                elif rm is not None and mp is not None and rm < mp:
                    s = '%s borcunuz %s, \\u00f6denmesi gereken minimum tutar %s, kalan toplam borcunuz %s, kalan minimum \\u00f6deme tutar\\u0131n\\u0131z %s.' % (full, money(sd, unit, sub) + ' TL', money(mp or 0, unit, sub) + ' TL', money(rd, unit, sub) + ' TL', money(rm, unit, sub) + ' TL')
                else:
                    s = '%s borcunuz %s, \\u00f6denmesi gereken minimum tutar %s.' % (full, money(sd, unit, sub) + ' TL', money(mp or 0, unit, sub) + ' TL')
            else:
                s = '%s borcunuz %s %s, kalan toplam borcunuz %s %s, \\u00f6denmesi gereken minimum tutar %s %s.' % (full, money(sd, unit, sub), code, money(rd, unit, sub), code, money(mp or 0, unit, sub), code)
            out.append(lead + s)
        if not has:
            tdv = num('TL', 'totalDebt') or 0.0
            s = 'Sonu %s ile biten %s kart\\u0131n\\u0131z\\u0131n %s tarihli ekstresinden borcunuz bulunmamaktad\\u0131r.' % (digits(last4), name, dt(sdate))
            if tdv > 0:
                s += ' Gelecek d\\u00f6nemler dahil toplam borcunuz %s TL.' % money(tdv, 'lira', 'kuru\\u015f')
            if dt(nlpd or lpd):
                s += ' Son \\u00f6deme tarihiniz %s olacakt\\u0131r.' % dt(nlpd or lpd)
            out = [s]
            vars['reading_kind'] = 'nodebt'
        else:
            if nodebt and len(has) < 4:
                nm = [f for c, f in nodebt]
                nm = ['TL' if x == 'T\\u00fcrk Liras\\u0131' else x for x in nm]
                out.append('%s borcunuz bulunmamaktad\\u0131r.' % ' ve '.join([', '.join(nm[:-1]), nm[-1]] if len(nm) > 1 else nm))
            if dt(lpd):
                if lpd == today_tr:
                    out.append('Bor\\u00e7lar\\u0131n\\u0131z i\\u00e7in son \\u00f6deme tarihiniz bug\\u00fcnd\\u00fcr.')
                else:
                    out.append('Bor\\u00e7lar\\u0131n\\u0131z i\\u00e7in son \\u00f6deme tarihiniz %s\\'d\\u0131r.' % dt(lpd))
            vars['reading_kind'] = 'debt'
    vars['pdf_currency'] = pdf_cur or 'TL'
    import re
    txt = ' '.join(out)
    txt = re.sub(r'(lira|dolar|euro|sterlin|sent|peni|kuru\\u015f) (TL|USD|EUR|GBP)', r'\\1', txt)
    vars['reading_text'] = txt
    vars['reading_state'] = 'ok'
    more = ' Ba\\u015fka bir kart\\u0131n\\u0131z\\u0131n borcunu \\u00f6\\u011frenmek ister misiniz?' if int(str(vars.get('card_count') or '1')) > 1 else ''
    vars['more_text'] = more
except Exception:
    vars['reading_state'] = 'error'
"""

EMAIL_PREP = """try:
    em = str(vars.get('email_address') or '').strip()
    kind = str(vars.get('reading_kind') or '')
    ok = ('@' in em) and kind == 'debt'
    vars['has_email'] = 'yes' if ok else 'no'
    wk = kind != 'nostatement'
    if ok:
        vars['offer_text'] = 'Hesap kesim tarihinizi de\\u011fi\\u015ftirebilirim ya da ekstrenizi kay\\u0131tl\\u0131 mail adresinize g\\u00f6nderebilirim.'
    else:
        vars['offer_text'] = 'Hesap kesim tarihinizi de\\u011fi\\u015ftirebilirim.'
    vars['full_say'] = str(vars.get('reading_text') or '') + vars.get('more_text', '') + ' ' + vars['offer_text']
    if int(str(vars.get('card_count') or '1')) > 1:
        vars['full_say'] = str(vars.get('reading_text') or '') + ' Ba\\u015fka bir kart\\u0131n\\u0131z\\u0131n borcunu \\u00f6\\u011frenmek ister misiniz? ' + vars['offer_text']
except Exception:
    vars['has_email'] = 'no'
    vars['full_say'] = str(vars.get('reading_text') or '')
"""

# ---------------- nodes ----------------
N = {}
N["init"] = code_node("init", INIT, [tr("end_error", eq("init_state", "missing"), "now or customer missing"), tr("fetch_cards", ALWAYS, "ok")], "fetch_cards")
N["fetch_cards"] = api_node("fetch_cards", "cards.list",
    {"customerNo": sf("{{customerNumber}}"), "aiFlow": sf("CardOps")}, [], "cards_prepare", "end_error")
N["cards_prepare"] = code_node("cards_prepare", CARDS_PREP, [
    tr("end_nocard", eq("cards_state", "none"), "no eligible card"),
    tr("end_error", eq("cards_state", "error"), "error"),
    tr("fetch_balance", eq("cards_state", "one"), "single card"),
    tr("card_select", ALWAYS, "many")], "card_select")

N["card_select"] = conv("card_select",
    "Müşteri hangi kartının borcunu öğrenmek istediğini söyleyecek. Türkçe, kısa konuş. Önce müşterinin son mesajındaki bir soruya tek kısa cümleyle cevap ver, sonra devam et. Kart adını card_name alanına, dört haneyi card_last4 alanına, tam numarayı card_full alanına çıkar. 'Hepsi' derse kart seçilmemiş say ve soruyu tekrar sor. Haneleri geri okuma.",
    on_enter={"type": "tts", "text": "{{card_feedback}}"},
    extraction=[ext("card_name", "Kart adı (örn. Yıldız Premium), söylenmediyse boş"),
                ext("card_last4", "Kartın son dört hanesi, rakamlarla"),
                ext("card_full", "Tam kart numarası, söylendiyse")],
    transitions=[tr("card_resolve", {"logic": "or", "conditions": [cond("card_name", "is_set"), cond("card_last4", "is_set"), cond("card_full", "is_set")]}, "customer answered"),
                 tr("card_giveup_tick", ALWAYS, "no answer")],
    max_turns=3, fallback="end_giveup")
N["card_giveup_tick"] = code_node("card_giveup_tick", "try:\n    t = int(str(vars.get('card_tries') or '0')) + 1\n    vars['card_tries'] = str(t)\n    vars['resolve_state'] = 'giveup' if t >= 3 else 'again'\n    vars['card_feedback'] = 'Hangi kartınızın borcunu öğrenmek istersiniz? Örneğin, %s diyebilirsiniz.' % str(vars.get('card_examples') or '')\nexcept Exception:\n    vars['resolve_state'] = 'giveup'\n",
    [tr("end_giveup", eq("resolve_state", "giveup"), "three tries"), tr("card_select", ALWAYS, "again")], "card_select")
N["card_resolve"] = code_node("card_resolve", CARD_RESOLVE, [
    tr("fetch_balance", eq("resolve_state", "ok"), "resolved"),
    tr("end_giveup", eq("resolve_state", "giveup"), "three tries used"),
    tr("card_select", ALWAYS, "ask again")], "card_select")

BAL_FIELDS = ["statementDebt", "minPayment", "remainingDebt", "remainingMinPayment", "totalDebt"]
bal_map = [{"path": "data." + f, "variable": "bal_" + f} for f in ["statementDate", "lastPayDate", "nextStatementDate", "nextLastPayDate", "cardNumberLast4", "productName"]]
for c in ["TL", "USD", "EUR", "GBP"]:
    for f in BAL_FIELDS:
        bal_map.append({"path": "data.debt%s.%s" % (c, f), "variable": "bal_%s_%s" % (c, f)})
N["fetch_balance"] = api_node("fetch_balance", "cards.balance", {"cardNumber": sf("{{selected_card_number}}")}, bal_map, "build_reading", "end_error")
N["build_reading"] = code_node("build_reading", BUILD, [tr("end_error", eq("reading_state", "error"), "error"), tr("fetch_email", ALWAYS, "ok")], "fetch_email")
N["fetch_email"] = api_node("fetch_email", "contact.email.get", {"customerNo": sf("{{customerNumber}}"), "intAddressInfoType": sf("E")},
    [{"path": "data.ibanEmail", "variable": "email_address"}, {"path": "data.ttsEmail", "variable": "email_tts"}], "email_prepare", "email_prepare", retries=0)
N["email_prepare"] = code_node("email_prepare", EMAIL_PREP, [tr("after_reading", ALWAYS, "go")], "after_reading")

N["after_reading"] = conv("after_reading",
    "Okuma ve teklif cümleleri on_enter ile söylendi, tekrar etme. Müşterinin cevabını bekle ve next_choice alanını doldur. Önce müşterinin sorusu varsa tek kısa cümleyle cevap ver. Başka bir kartın borcu: other_card. Ekstreyi e-postayla gönder: email. Hesap kesim tarihini değiştir: week. Başka bir isteği yok / teşekkür / hayır: done. Müşteri temsilcisi isterse: agent. Kapsam dışı bir soru: out_of_scope. Başka dil: other_language. Cevabı belirsizse tekrar sor.",
    on_enter={"type": "tts", "text": "{{full_say}}"},
    extraction=[ext("next_choice", "Müşterinin seçimi", ["other_card", "email", "week", "done", "agent", "out_of_scope", "other_language"])],
    transitions=[
        tr("card_reset", eq("next_choice", "other_card"), "another card"),
        tr("email_confirm", {"logic": "or", "conditions": [{"logic": "and", "conditions": [cond("next_choice", "equals", "email"), cond("has_email", "equals", "yes")]}]}, "email"),
        tr("no_email", {"logic": "or", "conditions": [{"logic": "and", "conditions": [cond("next_choice", "equals", "email"), cond("has_email", "equals", "no")]}]}, "no email"),
        tr("fetch_week", eq("next_choice", "week"), "week change"),
        tr("end_menu", eq("next_choice", "done"), "done"),
        tr("end_menu", eq("next_choice", "other_language"), "other language"),
        tr("end_agent", eq("next_choice", "agent"), "agent"),
        tr("end_oos", eq("next_choice", "out_of_scope"), "oos")],
    max_turns=4, fallback="end_giveup")
N["card_reset"] = code_node("card_reset", "vars['card_tries'] = '0'\nvars['card_feedback'] = 'Hangi kartınızın borcunu öğrenmek istersiniz? Örneğin, %s diyebilirsiniz.' % str(vars.get('card_examples') or '')\nvars['next_choice'] = ''\n", [tr("card_select", ALWAYS, "go")], "card_select")

N["no_email"] = conv("no_email",
    "Önce şu cümleyi tam olarak söyle: 'Bankamızda kayıtlı bir e-posta adresiniz bulunmadığı için ekstrenizi gönderemiyorum.' Sonra hesap kesim tarihini değiştirmek isteyip istemediğini sor. Cevabı wants_week alanına yaz.",
    extraction=[ext("wants_week", "Hesap kesim tarihini değiştirmek istiyor mu", ["yes", "no"])],
    transitions=[tr("fetch_week", eq("wants_week", "yes"), "yes"), tr("end_menu", eq("wants_week", "no"), "no")], max_turns=4)

pdf_hook = hook("Ekstre gönderildi; müşteriye başarıyla gönderildiğini söyle.", "")
N["email_confirm"] = conv("email_confirm",
    "Kayıtlı adres okundu ve izin soruldu (on_enter). Müşterinin cevabını bekle. Önce müşterinin sorusu varsa tek cümleyle cevap ver. Yalnızca açık bir 'evet' sonrasında statement_pdf_send aracını bir kez çağır; başka adrese gönderme, adres değiştirilemez. Araç başarı dönmeden gönderildi deme. Araç hata verirse tekrar çağırma. Hayır derse email_answer=no. Açık evet: email_answer=yes.",
    on_enter={"type": "tts", "text": "Ekstrenizi {{email_tts}} adresine göndermemi ister misiniz?"},
    tools=[api_fn("statement_pdf_send", "statement.pdf.send", {
        "customerNo": sf("{{customerNumber}}"), "cardNumber": sf("{{selected_card_number}}"),
        "currencyType": sf("{{pdf_currency}}"), "statementDate": sf("{{pdf_statement_date}}"),
        "emailAddress": sf("{{email_address}}")}, "Ekstreyi kayıtlı e-posta adresine gönder. Yalnızca açık evetten sonra çağır.", retries=0, hook=pdf_hook)],
    extraction=[ext("email_answer", "Müşterinin gönderim izni", ["yes", "no"])],
    transitions=[tr("end_sent", gt0("statement_pdf_send_success_count"), "sent"),
                 tr("end_send_fail", gt0("statement_pdf_send_failure_count"), "failed"),
                 tr("end_menu", eq("email_answer", "no"), "declined")], max_turns=6)

WEEK_MAP = [{"path": "data.statementWeek", "variable": "wk_week"}, {"path": "data.statementDay", "variable": "wk_day"},
            {"path": "data.productName", "variable": "wk_name"}, {"path": "data.nextStatementDate", "variable": "wk_next"},
            {"path": "data.nextLastPayDate", "variable": "wk_due"}]
N["fetch_week"] = api_node("fetch_week", "statement.week.get", {"cardNumber": sf("{{selected_card_number}}")}, WEEK_MAP, "week_flow", "end_week_fail")

dec_hook = hook("Önizleme alındı; yeni tarihleri söyleyip onay iste. Değişiklik henüz yapılmadı.", "")
chg_hook = hook("Değişiklik sonucu geldi; başarıysa ve exitState OK ise bildir.", "")
N["week_flow"] = conv("week_flow",
    "Hesap kesim haftası değişikliği. Sırayla: 1) on_enter ile mevcut durum söylendi ve değiştirmek isteyip istemediği soruldu. Hayır derse week_declined=yes. 2) Evet derse tam olarak şunu söyle: 'Hesap kesim tarihinizi ayın 1., 3. ya da 4. haftasına alabilirim. Hangisini tercih edersiniz?' ({{wk_week}}. hafta mevcut hafta; mevcut haftayı seçenek sayma, mevcut hafta 1, 3 ya da 4 ise listeyi ona göre düzenle). 3) Müşteri bir hafta seçince week_decide aracını çağır (önizleme, kartı değiştirmez). Sonucun statementDate ve statementDueDate alanlarını al ve şunu söyle: 'Yeni hesap kesim haftanız her ayın N. haftası olacak. Yeni hesap kesim tarihiniz [statementDate], son ödeme tarihiniz [statementDueDate] olacak. Onaylıyor musunuz?' (tarihleri 21 Ağustos 2026 biçiminde söyle). 4) Yalnızca açık evetten sonra week_change aracını bir kez çağır. Hayır derse week_declined=yes, değişiklik yapılmadı. Düzeltme olursa onay geçersizdir, yeniden week_decide çağır. Araç başarı dönmeden değişti deme. Bir araç hata verirse tekrar çağırma. Her araç sonucundan sonra konuş.",
    on_enter={"type": "tts", "text": "{{wk_name}} kartınızın hesap kesim tarihi her ayın {{wk_week}}. haftası olarak tanımlı. Bir sonraki hesap kesim tarihiniz {{wk_next}}, son ödeme tarihiniz {{wk_due}}. Hesap kesim tarihinizi değiştirmek ister misiniz?"},
    tools=[
        api_fn("week_decide", "statement.week.decide", {
            "cardNumber": sf("{{selected_card_number}}"),
            "newStatementWeek": {"type": "string", "default": "{{newStatementWeek}}", "enum": ["1", "2", "3", "4"], "description": "Müşterinin seçtiği yeni hafta (1-4)."},
            "statementDay": sf("{{wk_day}}")}, "Yeni haftanın önizlemesini al; kartı değiştirmez.", retries=0, hook=dec_hook,
            mapping=[{"path": "data.statementDate", "variable": "new_statement_date"}, {"path": "data.statementDueDate", "variable": "new_due_date"}]),
        api_fn("week_change", "statement.week.change", {
            "cardNumber": sf("{{selected_card_number}}"),
            "newStatementWeek": {"type": "string", "default": "{{newStatementWeek}}", "enum": ["1", "2", "3", "4"], "description": "Onaylanan yeni hafta (1-4)."},
            "statementDay": sf("{{wk_day}}")}, "Onaylanan hafta değişikliğini kaydet. Yalnızca açık evetten sonra çağır.", retries=0, hook=chg_hook)],
    extraction=[ext("week_declined", "Müşteri değişiklik istemiyor veya onaylamıyor mu", ["yes", "no"])],
    transitions=[tr("end_week_done", gt0("week_change_success_count"), "changed"),
                 tr("end_week_fail", gt0("week_change_failure_count"), "change failed"),
                 tr("end_week_fail", gt0("week_decide_failure_count"), "preview failed"),
                 tr("end_menu", eq("week_declined", "yes"), "declined")], max_turns=10)

N["end_menu"] = end_node("end_menu", "end_menu_close", "Sizi ana menüye yönlendiriyorum.")
N["end_oos"] = end_node("end_oos", "end_menu_oos", "Size bu konuda yardımcı olamıyorum. Sizi ana menüye yönlendiriyorum.")
N["end_giveup"] = end_node("end_giveup", "end_menu_giveup", "Size şu anda yardımcı olamıyorum. Sizi ana menüye yönlendiriyorum.")
N["end_nocard"] = end_node("end_nocard", "end_menu_nocard", "Ekstre borcunu sorgulayabileceğiniz uygun bir kredi kartınız bulunmuyor. Sizi ana menüye yönlendiriyorum.")
N["end_sent"] = end_node("end_sent", "end_menu_sent", "Ekstreniz kayıtlı e-posta adresinize gönderildi. Sizi ana menüye yönlendiriyorum.")
N["end_send_fail"] = end_node("end_send_fail", "end_menu_sendfail", "Şu anda ekstrenizi gönderemiyorum. Sizi müşteri temsilcimize aktarıyorum.")
N["end_week_done"] = end_node("end_week_done", "end_week_ok", "Sonu {{selected_last4}} ile biten kartınızın hesap kesim haftası değiştirildi. Yeni hesap kesim tarihiniz {{new_statement_date}}, son ödeme tarihiniz {{new_due_date}}. Sizi ana menüye yönlendiriyorum.")
N["end_week_fail"] = end_node("end_week_fail", "end_week_failed", "Şu anda hesap kesim tarihinizi değiştiremiyorum, sizi müşteri temsilcimize aktarıyorum.")
N["end_agent"] = end_node("end_agent", "end_agent_transfer", "Sizi müşteri temsilcimize aktarıyorum.")
N["end_error"] = end_node("end_error", "end_service_error", "Şu anda bilgilerinize ulaşamıyorum. Sizi müşteri temsilcimize aktarıyorum.")

SYSTEM = ("Sen Freya Bank'in sesli asistanısın ve kredi kartı ekstre borcu konusunda yardım ediyorsun. Yalnızca Türkçe konuş, her seferinde bir ya da iki kısa cümle kur. "
          "Önce müşterinin son mesajındaki soruyu (ör. robot musun) tek kısa cümleyle cevapla, sonra akışa devam et. "
          "Her mesajda en fazla bir araç çağır. Araç sonucundan sonra konuş ya da bir sonraki aracı çağır; sonuçtaki what_to_do_next cümlesini izle. "
          "Bir işlemin yapıldığını yalnızca ilgili araç başarı döndürdüyse söyle. Kart numarasının hanelerini asla geri okuma. Hiçbir tarih, tutar ya da bilgi uydurma. "
          "Kapsam dışı konularda ana menüye yönlendir.")
W = {"initial_node": "init", "system_prompt": SYSTEM,
     "test_variables": {"customerNumber": "95004361", "now": "2026-10-12T10:30:00+03:00"}, "nodes": N}
json.dump(W, open(os.path.join(HERE, "workflow.json"), "w"), ensure_ascii=False, indent=1)
print("ok")
