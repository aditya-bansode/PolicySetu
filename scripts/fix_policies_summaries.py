import sys

path = r"d:\Projects\PolicySetu\app\demo_data.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Clean Policy 1 duplicated lines:
old_p1 = '''        "summary": "The 17th instalment of PM-KISAN Samman Nidhi has been released, transferring ₹2,000 directly into the bank accounts of eligible farmer families. This instalment benefits over 9.4 crore farmers across India under the scheme providing ₹6,000 annual income support.",
        "summary_hi": "प्रधानमंत्री आवास योजना (शहरी) 2.0 का विस्तार 1 करोड़ अतिरिक्त शहरी परिवारों को ईडब्ल्यूएस, एलआईजी और एमआईजी श्रेणियों के लिए ₹2.5 लाख तक की ब्याज सब्सिडी के साथ पक्के घर प्रदान करने के लिए किया गया है।",
        "summary_mr": "पंतप्रधान आवास योजना (शहरी) 2.0 चा विस्तार 1 कोटी अतिरिक्त शहरी कुटुंबांना EWS, LIG आणि MIG श्रेणींसाठी ₹2.5 लाखांपर्यंत व्याज अनुदानासह पक्की घरे उपलब्ध करून देण्यासाठी करण्यात आला आहे.",
        "summary_hi": "डिजिटल व्यक्तिगत डेटा संरक्षण नियम 2025 नागरिकों के व्यक्तिगत डेटा की सुरक्षा, सहमति प्रबंधन और उल्लंघन के लिए ₹250 करोड़ तक के दंड के लिए परिचालन ढांचा अधिसूचित करता है।",
        "summary_mr": "डिजिटल वैयक्तिक डेटा संरक्षण नियम 2025 नागरिकांच्या वैयक्तिक डेटाचे रक्षण, संमती व्यवस्थापन आणि डेटा उल्लंघनासाठी ₹250 कोटींपर्यंतच्या दंडासाठी कार्यपद्धती अधिसूचित करते.",
        "summary_hi": "आयकर संशोधन नियम 2026 धारा 80सी कटौती सीमा को ₹1.5 लाख से बढ़ाकर ₹2 लाख प्रति वर्ष करता है, जो कर निर्धारण वर्ष 2027-28 से प्रभावी होगा। यह वेतनभोगी कर्मचारियों और पेशेवरों को अतिरिक्त कर राहत प्रदान करता है।",
        "summary_mr": "आयकर दुरुस्ती नियम 2026 ने कलम 80C कपात मर्यादा दरवर्षी ₹1.5 लाखांवरून ₹2 लाखांपर्यंत वाढवली आहे, जी कर आकारणी वर्ष 2027-28 पासून लागू होईल. यामुळे पगारदार कर्मचारी व व्यावसायिकांना अतिरिक्त कर सवलत मिळेल.",
        "summary_hi": "आयुष्मान भारत पीएम-जेएवाई योजना ने ₹5 लाख तक की वार्षिक आय वाले परिवारों को शामिल करने के लिए पात्रता मानदंड को संशोधित किया है, जिससे अतिरिक्त 2 करोड़ परिवारों को लाभ मिलेगा। ₹5 लाख का स्वास्थ्य कवर अपरिवर्तित रहेगा।",
        "summary_mr": "आयुष्मान भारत पीएम-जेएवाय योजनेने ₹5 लाखांपर्यंत वार्षिक उत्पन्न असलेल्या कुटुंबांचा समावेश करण्यासाठी पात्रता निकष सुधारित केले आहेत, ज्यामुळे अतिरिक्त 2 कोटी कुटुंबांना लाभ मिळेल. ₹5 लाखांचे आरोग्य कवच कायम राहील.",
        "summary_hi": "राष्ट्रीय शिक्षा नीति 2020 के लिए अद्यतन कार्यान्वयन दिशानिर्देश जारी किए गए हैं, जिसमें मूलभूत साक्षरता, 5+3+3+4 पाठ्यचर्या संरचना और कक्षा 6 से व्यावसायिक शिक्षा का एकीकरण शामिल है।",
        "summary_mr": "राष्ट्रीय शिक्षण धोरण 2020 साठी अद्ययावत अंमलबजावणी मार्गदर्शक तत्त्वे जारी करण्यात आली असून, यामध्ये मूलभूत साक्षरता, 5+3+3+4 अभ्यासक्रम रचना आणि इयत्ता 6 वी पासून व्यावसायिक शिक्षणाचा समावेश आहे.",
        "summary_hi": "पीएम-किसान सम्मान निधि की 17वीं किस्त जारी की गई है। पात्र किसान परिवारों के बैंक खातों में ₹2,000 सीधे हस्तांतरित किए गए हैं।",
        "summary_mr": "पीएम-किसान सन्मान निधीचा 17वा हप्ता जाहीर करण्यात आला आहे. पात्र शेतकरी कुटुंबांच्या बँक खात्यांमध्ये ₹2,000 थेट हस्तांतरित केले गेले आहेत.",'''

clean_p1 = '''        "summary": "The 17th instalment of PM-KISAN Samman Nidhi has been released, transferring ₹2,000 directly into the bank accounts of eligible farmer families. This instalment benefits over 9.4 crore farmers across India under the scheme providing ₹6,000 annual income support.",
        "summary_hi": "पीएम-किसान सम्मान निधि की 17वीं किस्त जारी की गई है। पात्र किसान परिवारों के बैंक खातों में ₹2,000 सीधे हस्तांतरित किए गए हैं।",
        "summary_mr": "पीएम-किसान सन्मान निधीचा 17वा हप्ता जाहीर करण्यात आला आहे. पात्र शेतकरी कुटुंबांच्या बँक खात्यांमध्ये ₹2,000 थेट हस्तांतरित केले गेले आहेत.",'''

if old_p1 in text:
    text = text.replace(old_p1, clean_p1)
    print("Cleaned Policy 1 successfully.")
else:
    print("Warning: old_p1 not found directly, checking...")

# Policy 2
p2_target = '"summary": "Updated implementation guidelines for the National Education Policy 2020 have been issued, covering foundational literacy and numeracy programs, the 5+3+3+4 curricular structure, and integration of vocational education from Class 6 onwards.",'
p2_repl = p2_target + '\n        "summary_hi": "राष्ट्रीय शिक्षा नीति 2020 के लिए अद्यतन कार्यान्वयन दिशानिर्देश जारी किए गए हैं, जिसमें मूलभूत साक्षरता, 5+3+3+4 पाठ्यचर्या संरचना और कक्षा 6 से व्यावसायिक शिक्षा का एकीकरण शामिल है।",\n        "summary_mr": "राष्ट्रीय शिक्षण धोरण 2020 साठी अद्ययावत अंमलबजावणी मार्गदर्शक तत्त्वे जारी करण्यात आली असून, यामध्ये मूलभूत साक्षरता, 5+3+3+4 अभ्यासक्रम रचना आणि इयत्ता 6 वी पासून व्यावसायिक शिक्षणाचा समावेश आहे.",'
if p2_target in text:
    text = text.replace(p2_target, p2_repl, 1)
    print("Updated Policy 2")

# Policy 3
p3_target = '"summary": "The Ayushman Bharat PM-JAY scheme has revised its income eligibility criteria to include families with annual income up to ₹5 lakh, expanding coverage to an additional 2 crore families. Health cover of ₹5 lakh per family per year remains unchanged.",'
p3_repl = p3_target + '\n        "summary_hi": "आयुष्मान भारत पीएम-जेएवाई योजना ने ₹5 लाख तक की वार्षिक आय वाले परिवारों को शामिल करने के लिए पात्रता मानदंड को संशोधित किया है, जिससे अतिरिक्त 2 करोड़ परिवारों को लाभ मिलेगा। ₹5 लाख का स्वास्थ्य कवर अपरिवर्तित रहेगा।",\n        "summary_mr": "आयुष्मान भारत पीएम-जेएवाय योजनेने ₹5 लाखांपर्यंत वार्षिक उत्पन्न असलेल्या कुटुंबांचा समावेश करण्यासाठी पात्रता निकष सुधारित केले आहेत, ज्यामुळे अतिरिक्त 2 कोटी कुटुंबांना लाभ मिळेल. ₹5 लाखांचे आरोग्य कवच कायम राहील.",'
if p3_target in text:
    text = text.replace(p3_target, p3_repl, 1)
    print("Updated Policy 3")

# Policy 4
p4_target = '"summary": "The Income Tax Amendment Rules 2026 increase the Section 80C deduction limit from ₹1.5 lakh to ₹2 lakh per annum, effective from Assessment Year 2027-28. This provides additional tax relief for salaried employees, professionals, and self-employed individuals investing in specified instruments.",'
p4_repl = p4_target + '\n        "summary_hi": "आयकर संशोधन नियम 2026 धारा 80सी कटौती सीमा को ₹1.5 लाख से बढ़ाकर ₹2 लाख प्रति वर्ष करता है, जो कर निर्धारण वर्ष 2027-28 से प्रभावी होगा। यह वेतनभोगी कर्मचारियों और पेशेवरों को अतिरिक्त कर राहत प्रदान करता है।",\n        "summary_mr": "आयकर दुरुस्ती नियम 2026 ने कलम 80C कपात मर्यादा दरवर्षी ₹1.5 लाखांवरून ₹2 लाखांपर्यंत वाढवली आहे, जी कर आकारणी वर्ष 2027-28 पासून लागू होईल. यामुळे पगारदार कर्मचारी व व्यावसायिकांना अतिरिक्त कर सवलत मिळेल.",'
if p4_target in text:
    text = text.replace(p4_target, p4_repl, 1)
    print("Updated Policy 4")

# Policy 5
p5_target = '"summary": "Maharashtra has released revised implementation guidelines for PMAY-Urban within the state, including enhanced subsidy amounts for EWS/LIG categories, simplified documentation requirements, and a new online portal for applications.",'
p5_repl = p5_target + '\n        "summary_hi": "महाराष्ट्र ने राज्य के भीतर पीएमएवाई-शहरी के लिए संशोधित कार्यान्वयन दिशानिर्देश जारी किए हैं, जिसमें ईडब्ल्यूएस/एलआईजी श्रेणियों के लिए बढ़ी हुई सब्सिडी राशि, सरलीकृत दस्तावेज आवश्यकताएं और आवेदनों के लिए एक नया ऑनलाइन पोर्टल शामिल है।",\n        "summary_mr": "महाराष्ट्राने राज्यातील PMAY-नागरीसाठी सुधारित अंमलबजावणी मार्गदर्शक तत्त्वे जारी केली आहेत, ज्यामध्ये EWS/LIG श्रेणींसाठी वाढीव अनुदान रक्कम, सुलभ कागदपत्रे आवश्यकता आणि अर्जांसाठी नवीन ऑनलाइन पोर्टल समाविष्ट आहे.",'
if p5_target in text:
    text = text.replace(p5_target, p5_repl, 1)
    print("Updated Policy 5")

# Policy 6
p6_target = '"summary": "The Digital Personal Data Protection Act 2023 compliance rules for Data Fiduciaries have been notified. Organizations processing personal data of Indian citizens must appoint a Data Protection Officer, implement consent mechanisms, and maintain processing records by January 2027.",'
p6_repl = p6_target + '\n        "summary_hi": "डिजिटल व्यक्तिगत डेटा संरक्षण अधिनियम 2023 के डेटा फिड्यूशियरी अनुपालन नियम अधिसूचित किए गए हैं। नागरिकों के डेटा को संसाधित करने वाले संगठनों को जनवरी 2027 तक डेटा संरक्षण अधिकारी नियुक्त करना होगा और सहमति तंत्र लागू करना होगा।",\n        "summary_mr": "डिजिटल वैयक्तिक डेटा संरक्षण कायदा 2023 अंतर्गत डेटा फिड्युशियरी अनुपालन नियम अधिसूचित करण्यात आले आहेत. नागरिकांचा डेटा हाताळणाऱ्या संस्थांनी जानेवारी 2027 पर्यंत डेटा संरक्षण अधिकारी नियुक्त करणे आणि संमती यंत्रणा लागू करणे अनिवार्य आहे.",'
if p6_target in text:
    text = text.replace(p6_target, p6_repl, 1)
    print("Updated Policy 6")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Finished writing demo_data.py")
