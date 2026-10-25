#!/usr/bin/env python3
"""Reference-only deterministic rules for approved 24 Oct 2026 decisions.
No live AI provider, user authentication, storage, Word export, or legal opinion.
"""
from __future__ import annotations
from datetime import date
from dateutil.relativedelta import relativedelta

S7_REASON_LABELS = {
 1: 'पेरणी किंवा लागवडीचा हंगाम संपत चालल्याने वेळेत पीक घेता येणार नाही.',
 2: 'उभ्या पिकांची मशागत, खते देणे किंवा निगा राखणे वेळेत करता येत नाही.',
 3: 'पीक काढणी किंवा शेतमालाची वाहतूक वेळेत करता येत नाही.',
 4: 'पिकांचे नुकसान होत आहे किंवा वेळेत शेतीकामे न झाल्यास नुकसान होण्याची अथवा वाढण्याची शक्यता आहे.',
 5: 'शेतातील घराकडे जाण्या-येण्यास अडचण निर्माण झाली आहे.',
 6: 'शेतीच्या इतर आवश्यक कामांमध्ये विलंब होत असल्याने तातडीने रस्ता वापरणे आवश्यक आहे.',
}

PRAYERS = {
 'PR-1': 'वादी यांच्या पूर्वीपासूनच्या वापरातील व दाव्यात वर्णन केलेल्या रस्त्यावर प्रतिवादी यांनी निर्माण केलेला अडथळा दूर करण्याचे आदेश देण्यात यावेत.',
 'PR-2': 'प्रतिवादी यांनी अडथळा दूर न केल्यास सदर अडथळा सक्षम अधिकाऱ्यामार्फत दूर करून रस्ता पूर्वीप्रमाणे खुला करून मिळावा.',
 'PR-3': 'प्रतिवादी यांनी वादी यांच्या सदर रस्त्याच्या वापरास भविष्यात कोणत्याही प्रकारे अडथळा निर्माण करू नये, असा मनाई आदेश देण्यात यावा.',
 'PR-4': 'वादी यांना सदर रस्त्याच्या वापराची तातडीची आवश्यकता असल्याने प्रस्तुत प्रकरणाची तातडीने सुनावणी घेऊन अंतिम निर्णय देण्यात यावा.',
}

class InvalidForm(ValueError): pass

def select_prayers(status:int, urgency_reasons:list[int]|None, urgent_hearing_yes_no:bool|None):
    """Preserve immutable prayer IDs, renumber display consecutively (only applicable prayers)."""
    if status not in (1,2,3): raise InvalidForm('INVALID_OBSTRUCTION_STATUS')
    if urgent_hearing_yes_no is not None and type(urgent_hearing_yes_no) is not bool:
        raise InvalidForm('URGENT_HEARING_MUST_BE_BOOLEAN_OR_UNANSWERED')
    reasons=urgency_reasons or []
    if any(type(x) is not int or x not in S7_REASON_LABELS for x in reasons):
        raise InvalidForm('INVALID_URGENCY_REASON')
    if status == 3:
        if reasons or urgent_hearing_yes_no is True: raise InvalidForm('S7_HIDDEN_FOR_STATUS_3_CLEAR_STALE_DATA')
        keys=['PR-3']
    else:
        keys=['PR-1','PR-2','PR-3']
        if reasons:
            if urgent_hearing_yes_no is None: raise InvalidForm('ASK_SEPARATE_URGENT_HEARING_YES_NO')
            if urgent_hearing_yes_no: keys.append('PR-4')
        elif urgent_hearing_yes_no is True:
            raise InvalidForm('URGENT_HEARING_WITHOUT_REASON')
    return [{'display_number':i, 'master_prayer_id':k, 'text':PRAYERS[k]} for i,k in enumerate(keys,1)]

def limitation_mode(obstruction_date:str|None, filing_date:str|None):
    """Conservative calendar check routes uncertain/boundary cases to human review.
    Statutory interpretation and filing readiness always require independent legal review.
    """
    if not obstruction_date or not filing_date:
        return {'mode':'REVIEW_ONLY', 'flag':'DATE_UNVERIFIED', 'within_limit_statement_allowed':False,
                'warning':'अडथळ्याची अथवा अर्ज दाखल करण्याची तारीख पडताळलेली नाही. कायदेशीर पुनरावलोकन आवश्यक.'}
    try:
        obstruction=date.fromisoformat(obstruction_date); filing=date.fromisoformat(filing_date)
    except (ValueError,TypeError):
        return {'mode':'REVIEW_ONLY','flag':'INVALID_DATE','within_limit_statement_allowed':False,
                'warning':'दिलेली तारीख अवैध आहे. दुरुस्त व पडताळणी आवश्यक.'}
    if filing < obstruction:
        return {'mode':'REVIEW_ONLY','flag':'FILING_BEFORE_OBSTRUCTION','within_limit_statement_allowed':False,
                'warning':'अर्जाची तारीख अडथळ्याच्या तारखेपूर्वी आहे; दुरुस्ती व पुनरावलोकन आवश्यक.'}
    cutoff=obstruction+relativedelta(months=6)
    if filing >= cutoff:   # deliberately conservative at the threshold
        return {'mode':'REVIEW_ONLY','flag':'SIX_MONTH_BOUNDARY_OR_LATE','threshold':cutoff.isoformat(),
                'within_limit_statement_allowed':False,
                'warning':'सहा महिन्यांच्या मुदतीचा प्रश्न आहे. हा मसुदा फक्त कायदेशीर पुनरावलोकनासाठी आहे; न्यायालयात सादर करण्यास तयार असल्याचे प्रमाणपत्र नाही.'}
    return {'mode':'NORMAL_REVIEW','flag':'DATES_PRELIMINARILY_WITHIN_SIX_MONTHS',
            'within_limit_statement_allowed':False, # only later verified human/legal stage may author that statement
            'warning':None, 'independent_legal_review_still_required':True}

def export_label(mode:dict):
    if mode['mode']=='REVIEW_ONLY':return 'केवळ कायदेशीर पुनरावलोकनासाठी — न्यायालयात दाखल करण्यासाठी अंतिम नाही'
    return 'मसुदा पुनरावलोकनासाठी — अंतिम स्वीकृती आणि कायदेशीर पडताळणी आवश्यक'
