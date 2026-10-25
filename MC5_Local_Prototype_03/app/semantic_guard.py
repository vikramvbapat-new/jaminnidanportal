"""Conservative lexical contradiction traps for *review-only* AI rewording.

Not a truth/entailment verifier. Adds defence-in-depth to source/numeric and
human review checks. Only clear, locally grounded contradictions are blocked.
"""
from __future__ import annotations
import re

# Do not replace human review with keyword gates. Only match fairly explicit
# Marathi claims that contradict canonical §5 fixture inputs.
_DENY_PREEXISTENCE = [
    r'रस्त[ा-्य\w\s]{0,45}(?:अस्तित्वात\s+नव्हता|कधीच\s+अस्तित्वात\s+नव्हता)',
    r'(?:सदर\s+)?रस्ता\s+(?:पूर्वी\s+)?(?:कधीही\s+)?वापरात\s+नव्हता',
    r'पूर्वीपासून\s+रस्ता\s+नव्हता',
]
_FALSE_PAST_ATTEMPT = [
    r'(?:विनंती|प्रयत्न|मध्यस्थी|तक्रार)[^।.]{0,55}(?:केली\s+नाही|केले\s+नाही|झाली\s+नाही)',
    r'कोणतेही\s+प्रयत्न\s+केले\s+नाहीत',
]
_FALSE_UNAVAILABLE_EVIDENCE = [
    r'(?:कोणतेही|कुठलेही)\s+पुरावे\s+उपलब्ध\s+नाहीत',
    r'पुरावा\s+(?:मुळीच\s+)?उपलब्ध\s+नाही',
]
_ONGOING_OBSTRUCTION = [
    r'(?:अडथळा|कुंपण|दगडांचा\s+अडथळा)[^।.]{0,35}(?:अद्याप\s+कायम|अजूनही\s+कायम|सध्या\s+कायम)',
    r'(?:सध्या|अजूनही)\s+रस्ता\s+(?:पूर्णपणे\s+)?बंद',
    r'भौतिक\s+अडथळा\s+कायम\s+आहे',
]
_FALSE_CONNECTION = [
    r'गाव\s*रस्त्या(?:शी|पर्यंत)[^।.]{0,45}(?:जोडलेला|जोडणी\s+आहे|जोडतो|जातो|पोहोचतो)',
    r'गाव\s*रस्त्यापर्यंत\s+हा\s+वहिवाटीचा\s+रस्ता',
]


def _hits(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text) for p in patterns)


def semantic_contradiction_errors(number:int, text:str, *, facts:dict, case:dict)->list[str]:
    """Checks explicit reversals only; silence about subtler AI mistakes is not approval."""
    issues=[]
    if number==2 and facts.get('preexisting_use') and _hits(text,_DENY_PREEXISTENCE):
        issues.append('परिच्छेद २: पूर्वअस्तित्व/पूर्ववापर नाकारल्याने पुष्टी झालेल्या माहितीशी विरोधाभास.')
    if number==3 and case.get('village_road_confirmed') is False and _hits(text,_FALSE_CONNECTION):
        issues.append('परिच्छेद ३: गाव रस्त्याशी जोड असल्याचा अपुष्ट दावा.')
    if number==7 and case.get('status')==3 and _hits(text,_ONGOING_OBSTRUCTION):
        issues.append('परिच्छेद ७: भौतिक अडथळा दूर झालेला असताना चालू अडथळ्याचा दावा.')
    if number==10 and facts.get('evidence') and _hits(text,_FALSE_UNAVAILABLE_EVIDENCE):
        issues.append('परिच्छेद १०: उपलब्ध असल्याचे पुष्टी झालेले पुरावे नाकारले आहेत.')
    if number==11 and case.get('attempts_made') is True and _hits(text,_FALSE_PAST_ATTEMPT):
        issues.append('परिच्छेद ११: प्रयत्न झाले असल्याच्या पुष्टी झालेल्या माहितीचा निषेध.')
    return issues
