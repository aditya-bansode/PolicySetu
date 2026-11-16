import urllib.request
import json

base_url = "http://127.0.0.1:5000"

def test_endpoint(path, check_bytes):
    url = f"{base_url}{path}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            content = res.read()
            status = res.status
            passed = all(b in content for b in check_bytes)
            print(f"[{'PASS' if passed and status==200 else 'FAIL'}] {path} -> HTTP {status}")
            return passed
    except Exception as e:
        print(f"[FAIL] {path} -> Exception")
        return False

def test_post_json(path, data, check_str_in_answer):
    url = f"{base_url}{path}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            raw = res.read().decode("utf-8")
            status = res.status
            parsed = json.loads(raw)
            answer = parsed.get("data", {}).get("answer") or parsed.get("data", {}).get("summary_short", "")
            passed = check_str_in_answer in answer
            print(f"[{'PASS' if passed and status==200 else 'FAIL'}] POST {path} (lang={data.get('language')}) -> HTTP {status}")
            return passed
    except Exception as e:
        print(f"[FAIL] POST {path} -> Exception")
        return False

print("=== Testing PolicySetu Language Strategy ===")

# 1. Home English
test_endpoint("/?lang=en", [
    "Bridging Government Policies & People".encode("utf-8"),
    "Explore Policies".encode("utf-8"),
    "More Indian Languages Coming Soon".encode("utf-8"),
])

# 2. Home Hindi
test_endpoint("/?lang=hi", [
    "सरकारी नीतियों और नागरिकों के बीच सेतु".encode("utf-8"),
    "नीतियां देखें".encode("utf-8"),
    "More Indian Languages Coming Soon".encode("utf-8"),
    "हिन्दी (HI)".encode("utf-8"),
])

# 3. Home Marathi
test_endpoint("/?lang=mr", [
    "सरकारी धोरणे आणि नागरिक यांच्यातील सेतू".encode("utf-8"),
    "धोरणे शोधा".encode("utf-8"),
    "मराठी (MR)".encode("utf-8"),
])

# 4. Policy Explorer Hindi
test_endpoint("/policies?lang=hi", [
    "नीति अन्वेषक".encode("utf-8"),
    "दस्तावेज़ प्रकार".encode("utf-8"),
    "क्रमबद्ध करें".encode("utf-8"),
])

# 5. Policy Detail Hindi
test_endpoint("/policies/1?lang=hi", [
    "पीएम-किसान सम्मान निधि".encode("utf-8"),
    "AI सारांश एवं अवलोकन".encode("utf-8"),
    "आधिकारिक दस्तावेज़ देखें".encode("utf-8"),
])

# 6. Policy Detail Marathi
test_endpoint("/policies/1?lang=mr", [
    "पीएम-किसान सन्मान निधी".encode("utf-8"),
    "AI सारांश आणि आढावा".encode("utf-8"),
])

# 7. Ask AI Hindi
test_endpoint("/ask?lang=hi", [
    "पॉलिसीसेतु AI सहायक".encode("utf-8"),
    "पीएम-किसान सम्मान निधि क्या है और कौन पात्र है?".encode("utf-8"),
])

# 8. Ask AI Marathi
test_endpoint("/ask?lang=mr", [
    "पॉलिसीसेतू AI सहाय्यक".encode("utf-8"),
    "पीएम-किसान सन्मान निधी काय आहे आणि कोण पात्र आहे?".encode("utf-8"),
])

# 9. API Ask Hindi
test_post_json("/api/v1/ask", {"question": "pm kisan", "language": "hi"}, "छोटे और सीमांत किसान परिवारों को")

# 10. API Ask Marathi
test_post_json("/api/v1/ask", {"question": "pm kisan", "language": "mr"}, "लहान आणि अल्पभूधारक शेतकरी कुटुंबांना")

# 11. API Summarize Hindi
test_post_json("/api/v1/summarize/1", {"language": "hi"}, "पीएम-किसान सम्मान निधि")

# 12. API Summarize Marathi
test_post_json("/api/v1/summarize/1", {"language": "mr"}, "पीएम-किसान सन्मान निधी")

print("=== Language Strategy Testing Complete ===")
