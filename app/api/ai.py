"""PolicySetu API — AI endpoints (demo responses with full multi-language support)."""
from flask import jsonify, request
from app.api import api_v1_bp
from app.demo_data import DEMO_POLICIES


DISCLAIMERS = {
    "en": (
        "This is an AI-generated explanation based on official government documents. "
        "It is not legal advice. Always refer to the official source for authoritative information."
    ),
    "hi": (
        "यह आधिकारिक सरकारी दस्तावेजों पर आधारित AI-जनरेटेड स्पष्टीकरण है। "
        "यह कानूनी सलाह नहीं है। आधिकारिक जानकारी के लिए हमेशा सरकारी स्रोत देखें।"
    ),
    "mr": (
        "हे अधिकृत सरकारी दस्तऐवजांवर आधारित AI द्वारे तयार केलेले स्पष्टीकरण आहे. "
        "हा कायदेशीर सल्ला नाही. अधिकृत माहितीसाठी नेहमी मूळ सरकारी स्त्रोताचा संदर्भ घ्यावा."
    )
}

DEMO_ANSWERS = {
    "pm kisan": {
        "en": (
            "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi) provides income support of ₹6,000 per year "
            "in three equal installments to small and marginal farmer families. The scheme is implemented "
            "by the Ministry of Agriculture and Farmers' Welfare. Eligible farmer families receive direct "
            "benefit transfers to their bank accounts."
        ),
        "hi": (
            "पीएम-किसान (प्रधानमंत्री किसान सम्मान निधि) छोटे और सीमांत किसान परिवारों को ₹6,000 प्रति वर्ष की आय सहायता "
            "तीन समान किस्तों में प्रदान करती है। यह योजना कृषि एवं किसान कल्याण मंत्रालय द्वारा संचालित की जाती है और राशि सीधे "
            "किसानों के बैंक खातों में डीबीटी के माध्यम से भेजी जाती है।"
        ),
        "mr": (
            "पीएम-किसान (पंतप्रधान किसान सन्मान निधी) योजना लहान आणि अल्पभूधारक शेतकरी कुटुंबांना दरवर्षी ₹6,000 चे आर्थिक सहाय्य "
            "तीन समान हप्त्यांमध्ये प्रदान करते. ही योजना कृषी आणि शेतकरी कल्याण मंत्रालयामार्फत राबवली जाते आणि निधी थेट शेतकऱ्यांच्या "
            "बँक खात्यात जमा केला जातो."
        ),
        "confidence": "high",
        "sources": [
            {
                "title": "PM-KISAN Scheme Guidelines",
                "official_url": "https://pmkisan.gov.in",
                "excerpt": "Income support of Rs. 6000/- per year in three equal installments..."
            }
        ]
    },
    "nps": {
        "en": (
            "The National Pension System (NPS) is a voluntary, long-term retirement savings scheme "
            "designed to enable systematic savings. It is regulated by the Pension Fund Regulatory and "
            "Development Authority (PFRDA). Both government employees and citizens can subscribe."
        ),
        "hi": (
            "राष्ट्रीय पेंशन प्रणाली (NPS) एक स्वैच्छिक, दीर्घकालिक सेवानिवृत्ति बचत योजना है जो नागरिकों को व्यवस्थित बचत करने में "
            "सक्षम बनाती है। इसे पेंशन फंड नियामक और विकास प्राधिकरण (PFRDA) द्वारा नियंत्रित किया जाता है।"
        ),
        "mr": (
            "राष्ट्रीय पेन्शन योजना (NPS) ही एक ऐच्छिक, दीर्घकालीन निवृत्ती वेतन बचत योजना आहे जी पद्धतशीर बचतीस सक्षम करते. "
            "याचे नियमन पेन्शन फंड नियामक आणि विकास प्राधिकरण (PFRDA) द्वारे केले जाते."
        ),
        "confidence": "high",
        "sources": [
            {
                "title": "NPS — PFRDA Guidelines",
                "official_url": "https://www.pfrda.org.in",
                "excerpt": "NPS is a voluntary defined contribution retirement savings scheme..."
            }
        ]
    },
}


@api_v1_bp.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    language = data.get("language", "en")
    lang = language if language in ["en", "hi", "mr"] else "en"
    disclaimer = DISCLAIMERS.get(lang, DISCLAIMERS["en"])

    if not question:
        return jsonify({"success": False, "error": "Question is required"}), 400

    # Match demo answers
    answer_data = None
    q_lower = question.lower()
    for key, val in DEMO_ANSWERS.items():
        if key in q_lower or (key == "pm kisan" and ("kisan" in q_lower or "किसान" in q_lower or "शेतकरी" in q_lower)):
            answer_data = val
            break
        elif key == "nps" and ("pension" in q_lower or "पेंशन" in q_lower or "पेन्शन" in q_lower):
            answer_data = val
            break

    if answer_data:
        ans_text = answer_data.get(lang, answer_data["en"])
        sources = answer_data["sources"]
        confidence = answer_data["confidence"]
    else:
        if lang == "hi":
            ans_text = (
                f"डेमो डेटाबेस में भारतीय शासन से संबंधित {len(DEMO_POLICIES)} नीतियां उपलब्ध हैं। "
                "सटीक आधिकारिक उत्तर प्रदान करने के लिए RAG पाइपलाइन उत्पादन डेटाबेस से जोड़ी जाएगी। "
                "डेमो पूर्वावलोकन के लिए कृपया PM-KISAN या पेंशन के बारे में पूछें।"
            )
        elif lang == "mr":
            ans_text = (
                f"डेमो डेटाबेसमध्ये भारतीय प्रशासनाशी संबंधित {len(DEMO_POLICIES)} धोरणे उपलब्ध आहेत. "
                "अचूक अधिकृत उत्तरे देण्यासाठी RAG प्रणाली उत्पादन डेटाबेसशी जोडली जाईल. "
                "डेमो पूर्वावलोकनासाठी कृपया PM-KISAN किंवा पेन्शनबद्दल विचारा."
            )
        else:
            ans_text = (
                f"I found {len(DEMO_POLICIES)} policies in the demo database related to Indian governance. "
                "To provide accurate answers grounded in official documents, the RAG (Retrieval-Augmented Generation) "
                "pipeline will be connected to the production database with real policy documents. "
                "Currently running in DEMO mode — please ask about PM-KISAN or NPS for example responses."
            )
        confidence = "demo"
        sources = []

    return jsonify({
        "success": True,
        "data": {
            "question": question,
            "answer": ans_text,
            "language": lang,
            "confidence": confidence,
            "sources": sources,
            "disclaimer": disclaimer,
            "is_demo": True,
        }
    })


@api_v1_bp.route("/summarize/<int:policy_id>", methods=["POST"])
def summarize(policy_id):
    policy = next((p for p in DEMO_POLICIES if p["id"] == policy_id), None)
    if not policy:
        return jsonify({"success": False, "error": "Policy not found"}), 404

    data = request.get_json(silent=True) or {}
    lang = data.get("language") or request.args.get("lang") or "en"
    if lang == "hi":
        summary = policy.get("summary_hi") or policy.get("summary", "")
        title = policy.get("title_hi") or policy.get("title", "")
    elif lang == "mr":
        summary = policy.get("summary_mr") or policy.get("summary", "")
        title = policy.get("title_mr") or policy.get("title", "")
    else:
        summary = policy.get("summary", "")
        title = policy.get("title", "")

    return jsonify({
        "success": True,
        "data": {
            "policy_id": policy_id,
            "title": title,
            "language": lang,
            "summary_short": summary,
            "key_points": policy.get("key_points", []),
            "stakeholders": policy.get("stakeholders", []),
            "disclaimer": DISCLAIMERS.get(lang, DISCLAIMERS["en"]),
            "is_demo": True,
        }
    })
