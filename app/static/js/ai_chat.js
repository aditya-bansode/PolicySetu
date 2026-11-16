/**
 * PolicySetu — Ask PolicySetu AI Chat JavaScript
 * Handles interactive AI question answering, structured source citations,
 * direct policy detail linking, and sessionStorage conversation persistence.
 */

const CHAT_STORAGE_KEY = 'policysetu_chat_messages_v2';

const aiChat = {
  history: [],
  savedMessages: [],
  loading: false,
  lang: localStorage.getItem('ps_lang') || 'en',
};

document.addEventListener('DOMContentLoaded', () => {
  initAiChat();
});

function initAiChat() {
  const form = document.getElementById('chatForm');
  const input = document.getElementById('chatInput');
  const sendBtn = document.getElementById('chatSendBtn');
  const langSelect = document.getElementById('chatLangSelect');
  const messages = document.getElementById('chatMessages');

  if (!form) return;

  // Restore language preference
  if (langSelect) {
    langSelect.value = aiChat.lang;
    langSelect.addEventListener('change', () => {
      aiChat.lang = langSelect.value;
    });
  }

  // Restore conversation history from sessionStorage
  restoreChatSession();

  // Auto-resize textarea
  input?.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  });

  // Send on Enter (Shift+Enter = newline)
  input?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  form.addEventListener('submit', e => {
    e.preventDefault();
    sendMessage();
  });

  // Suggested question buttons
  document.querySelectorAll('.suggested-q-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      if (input) {
        input.value = btn.textContent.trim();
        input.focus();
        sendMessage();
      }
    });
  });

  // Clear chat button
  document.getElementById('clearChatBtn')?.addEventListener('click', () => {
    aiChat.history = [];
    aiChat.savedMessages = [];
    try {
      sessionStorage.removeItem(CHAT_STORAGE_KEY);
    } catch (e) {
      console.warn('Could not clear sessionStorage:', e);
    }
    if (messages) {
      messages.innerHTML = renderWelcomeMessage();
    }
    const toastMsg = (aiChat.lang === 'hi')
      ? 'बातचीत रीसेट कर दी गई'
      : ((aiChat.lang === 'mr') ? 'संभाषण रीसेट केले' : 'Conversation reset');
    if (typeof showToast === 'function') {
      showToast(toastMsg, 'info');
    }
  });
}

function restoreChatSession() {
  const messages = document.getElementById('chatMessages');
  if (!messages) return;

  try {
    const raw = sessionStorage.getItem(CHAT_STORAGE_KEY);
    if (!raw) return;

    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.length > 0) {
      aiChat.savedMessages = parsed;
      messages.innerHTML = '';
      parsed.forEach(m => {
        messages.appendChild(createMessageEl(m.role, m.text, m.sources || [], m.disclaimer || null, m.isDemo || false));
        aiChat.history.push({
          role: m.role === 'user' ? 'user' : 'assistant',
          content: m.text || ''
        });
      });
      scrollToBottom(messages);
    }
  } catch (err) {
    console.warn('Failed to restore chat session:', err);
  }
}

function persistChatSession() {
  try {
    sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(aiChat.savedMessages.slice(-20)));
  } catch (err) {
    console.warn('Failed to persist chat session:', err);
  }
}

async function sendMessage() {
  if (aiChat.loading) return;

  const input = document.getElementById('chatInput');
  const messages = document.getElementById('chatMessages');
  if (!input || !messages) return;

  const question = input.value.trim();
  if (!question) return;

  // Append user bubble
  messages.appendChild(createMessageEl('user', question));
  input.value = '';
  input.style.height = 'auto';

  // Record user message
  aiChat.savedMessages.push({ role: 'user', text: question });
  persistChatSession();

  // Append AI thinking bubble
  const thinkingEl = createThinkingBubble();
  messages.appendChild(thinkingEl);
  scrollToBottom(messages);

  aiChat.loading = true;
  document.getElementById('chatSendBtn')?.setAttribute('disabled', 'true');

  try {
    const res = await apiPost('/ask', {
      question,
      language: aiChat.lang,
      conversation_history: aiChat.history.slice(-6),
    });

    thinkingEl.remove();

    const { answer, sources, disclaimer, is_demo } = res.data || {};

    // Build answer bubble
    const answerEl = createMessageEl('ai', answer, sources, disclaimer, is_demo);
    messages.appendChild(answerEl);

    // Store in history
    aiChat.history.push({ role: 'user', content: question });
    aiChat.history.push({ role: 'assistant', content: answer || '' });

    aiChat.savedMessages.push({
      role: 'ai',
      text: answer,
      sources: sources || [],
      disclaimer: disclaimer || null,
      isDemo: !!is_demo,
    });
    persistChatSession();

  } catch (err) {
    thinkingEl.remove();
    const errMsg = (aiChat.lang === 'hi')
      ? 'आधिकारिक रिकॉर्ड प्राप्त करते समय त्रुटि हुई। कृपया पुनः प्रयास करें।'
      : ((aiChat.lang === 'mr')
        ? 'अधिकृत नोंदी मिळवताना एक त्रुटी आली. कृपया पुन्हा प्रयत्न करा.'
        : 'An error occurred while retrieving official records. Please try again.');
    const errEl = createMessageEl('ai', errMsg, [], null, false);
    messages.appendChild(errEl);
    if (typeof showToast === 'function') {
      showToast('AI request failed', 'error');
    }
  } finally {
    aiChat.loading = false;
    document.getElementById('chatSendBtn')?.removeAttribute('disabled');
    scrollToBottom(messages);
  }
}

function renderSourceCard(s) {
  const hasDbId = s.id && Number.isInteger(Number(s.id)) && Number(s.id) > 0;
  const rawOfficial = s.official_url;
  const officialUrl = (rawOfficial && rawOfficial !== '#' && !rawOfficial.startsWith('javascript:')) ? rawOfficial : null;
  const title = s.title || (officialUrl ? 'Official Government Document' : 'Referenced Document');
  const dept = s.department || 'Government of India';
  const cat = s.category || 'General';
  const summary = s.summary || s.excerpt || '';

  const viewDetailsLabel = (aiChat.lang === 'hi')
    ? 'नीति विवरण देखें'
    : ((aiChat.lang === 'mr') ? 'धोरण तपशील पहा' : 'View Policy Details');

  const officialDocLabel = (aiChat.lang === 'hi')
    ? 'आधिकारिक दस्तावेज'
    : ((aiChat.lang === 'mr') ? 'अधिकृत दस्तऐवज' : 'Official Document');

  return `
    <div class="chat-source-card" style="margin-top:6px; padding:10px 12px; background:var(--color-paper); border:1px solid var(--color-border); border-radius:var(--radius-md); box-shadow:0 1px 3px rgba(0,0,0,0.04); text-align:left;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px; margin-bottom:4px;">
        <div style="font-weight:600; font-size:0.85rem; color:var(--color-heading, #0F172A); line-height:1.35;">
          ${escHtml(title)}
        </div>
        <span class="badge badge-info" style="font-size:0.65rem; white-space:nowrap; flex-shrink:0;">
          ${escHtml(cat)}
        </span>
      </div>
      <div style="font-size:0.75rem; color:var(--color-muted); margin-bottom:6px;">
        ${escHtml(dept)}
      </div>
      ${summary ? `<p style="font-size:0.75rem; color:var(--color-slate); margin:0 0 8px 0; line-height:1.4;">${escHtml(summary)}</p>` : ''}
      <div style="display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-top:6px;">
        ${hasDbId ? `
          <a href="/policies/${s.id}" class="btn btn-primary btn-xs" style="text-decoration:none; display:inline-flex; align-items:center; gap:4px; font-size:0.75rem; padding:4px 10px; font-weight:600;">
            <span>${viewDetailsLabel}</span> &rarr;
          </a>
        ` : ''}
        ${officialUrl ? `
          <a href="${escHtml(officialUrl)}" target="_blank" rel="noopener noreferrer" class="btn btn-outline btn-xs" style="text-decoration:none; display:inline-flex; align-items:center; gap:4px; font-size:0.75rem; padding:4px 8px;">
            <svg class="icon icon-xs" viewBox="0 0 24 24" style="width:12px;height:12px;stroke:currentColor;fill:none;stroke-width:2;"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
            <span>${officialDocLabel}</span>
          </a>
        ` : ''}
      </div>
    </div>
  `;
}

function createMessageEl(role, text, sources = [], disclaimer = null, isDemo = false) {
  const div = document.createElement('div');
  div.className = `chat-message ${role}`;

  const avatarLabel = role === 'ai' ? 'AI' : 'YOU';
  const avatarClass = role === 'ai' ? 'ai' : 'user-icon';

  let sourcesHtml = '';
  if (sources && sources.length > 0) {
    const sourcesCitedLabel = (aiChat.lang === 'hi')
      ? 'उद्धृत आधिकारिक नीतियां एवं स्रोत'
      : ((aiChat.lang === 'mr') ? 'उल्लेखित अधिकृत धोरणे आणि स्रोत' : 'Cited Official Policies & Sources');
    sourcesHtml = `
      <div class="chat-sources" style="margin-top:10px;">
        <small style="font-size:0.7rem; color:#94A3B8; font-weight:700; text-transform:uppercase; letter-spacing:.05em;">
          ${sourcesCitedLabel} (${sources.length})
        </small>
        <div style="display:flex; flex-direction:column; gap:8px; margin-top:4px;">
          ${sources.map(renderSourceCard).join('')}
        </div>
      </div>
    `;
  }

  const demoBadge = isDemo
    ? `<span class="badge badge-demo" style="font-size:.65rem;margin-top:8px">${aiChat.lang === 'hi' ? 'डेमो उत्तर' : (aiChat.lang === 'mr' ? 'डेमो उत्तर' : 'Demo Response')}</span>`
    : '';

  const disclaimerHtml = disclaimer
    ? `<div class="chat-disclaimer">${escHtml(disclaimer)}</div>`
    : '';

  div.innerHTML = `
    <div class="chat-avatar ${avatarClass}" style="font-size:0.75rem; font-weight:700;">${avatarLabel}</div>
    <div class="chat-message-content">
      <div class="chat-bubble ${role}">
        ${escHtml(text || '')}
        ${demoBadge}
      </div>
      ${sourcesHtml}
      ${disclaimerHtml}
    </div>
  `;

  return div;
}

function createThinkingBubble() {
  const div = document.createElement('div');
  div.className = 'chat-message ai';
  div.id = 'thinkingBubble';
  const thinkingText = aiChat.lang === 'hi'
    ? 'आधिकारिक नीति संदर्भ खोजे जा रहे हैं...'
    : (aiChat.lang === 'mr' ? 'अधिकृत धोरण संदर्भ शोधत आहे...' : 'Retrieving official policy references...');
  div.innerHTML = `
    <div class="chat-avatar ai" style="font-size:0.75rem; font-weight:700;">AI</div>
    <div class="chat-bubble ai" style="display:flex;align-items:center;gap:8px">
      <div class="spinner" style="width:16px;height:16px;border-width:2px"></div>
      <span style="color:#94A3B8;font-size:13px">${thinkingText}</span>
    </div>
  `;
  return div;
}

function renderWelcomeMessage() {
  const isHi = aiChat.lang === 'hi';
  const isMr = aiChat.lang === 'mr';
  const title = isHi ? 'पॉलिसीसेतु AI में आपका स्वागत है' : (isMr ? 'पॉलिसीसेतू AI मध्ये आपले स्वागत आहे' : 'Welcome to PolicySetu AI');
  const p1 = isHi
    ? 'मैं भारतीय केंद्र और राज्य सरकार की अधिसूचनाओं, अधिनियमों, परिपत्रों और योजनाओं को सरल, स्पष्ट भाषा में समझाने के लिए यहाँ हूँ।'
    : (isMr
      ? 'मी भारतीय केंद्र आणि राज्य सरकारच्या अधिसूचना, कायदे, परिपत्रके आणि योजनांचे सोप्या भाषेत स्पष्टीकरण देण्यासाठी येथे आहे.'
      : 'I am here to decode Indian central and state government notifications, acts, circulars, and schemes into simple, unambiguous explanations.');
  const p2 = isHi
    ? 'सभी उत्तर सीधे सत्यापित आधिकारिक सरकारी लिंक्स के साथ दिए जाते हैं। आज आप किस नीति के बारे में जानना चाहते हैं?'
    : (isMr
      ? 'सर्व उत्तरे थेट सत्यापित अधिकृत सरकारी लिंक्ससह दिली जातात. आज तुम्हाला कोणत्या धोरणाबद्दल माहिती हवी आहे?'
      : 'All answers are cited directly with verified official government links. What policy would you like to explore today?');

  return `
    <div class="chat-message ai">
      <div class="chat-avatar ai" style="font-size:0.75rem; font-weight:700;">AI</div>
      <div class="chat-message-content">
        <div class="chat-bubble ai">
          <strong>${title}</strong>
          <p style="margin-top:8px; margin-bottom:8px;">${p1}</p>
          <p style="margin:0;">${p2}</p>
        </div>
      </div>
    </div>
  `;
}

function scrollToBottom(el) {
  setTimeout(() => { el.scrollTop = el.scrollHeight; }, 50);
}
