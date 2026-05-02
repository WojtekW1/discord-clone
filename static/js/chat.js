(function(){
  if (!window.CHAT_CONTEXT) return;

  const ctx = window.CHAT_CONTEXT;
  const messagesEl = document.getElementById("messages");
  const inputEl = document.getElementById("messageInput");
  const presenceEl = document.getElementById("presenceInfo");

  if (messagesEl) {
  // po wejściu w kanał/DM od razu na dół (najnowsze)
  setTimeout(() => {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }, 0);
}

  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  let wsUrl = "";
  let scope = "";
  if (ctx.isDM) {
    wsUrl = `${proto}://${window.location.host}/ws/chat/dm/${ctx.dmId}/`;
    scope = `dm:${ctx.dmId}`;
  } else {
    wsUrl = `${proto}://${window.location.host}/ws/chat/channel/${ctx.channelId}/`;
    scope = `channel:${ctx.channelId}`;
  }

  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    // console.log("ws open");
  };

  ws.onmessage = (ev) => {
    const data = JSON.parse(ev.data);
    if (data.type === "user.status") {
      presenceEl.textContent = `${data.user} ${data.status}`;
      return;
    }
    if (data.type === "message.delete") {
      const node = document.querySelector(`.msg[data-id='${data.message_id}']`);
      if (node) {
        // usuń obrazki i audio jeśli są
        node.querySelectorAll("img").forEach(el => el.remove());
        node.querySelectorAll("audio").forEach(el => el.remove());

        // podmień treść na [deleted]
        const content = node.querySelector(".msg-text");
        if (content) {
          content.innerHTML = "<span class='text-secondary fst-italic'>[deleted]</span>";
        } else {
          // fallback: wstaw w pierwsze sensowne miejsce
          const mt1 = node.querySelector(".mt-1");
          if (mt1) mt1.innerHTML = "<span class='text-secondary fst-italic'>[deleted]</span>";
        }
      }
      return;
    }
    if (data.type === "reaction.update") {
      const box = document.getElementById(`rx-${data.message_id}`);
      if (box) {
        box.textContent = (data.counts || []).map(x => `${x.emoji} ${x.c}`).join("  ");
      }
      return;
    }
    if (data.type === "message.new") {
      appendMessage(data);
      return;
    }
  };

  ws.onclose = () => {
    presenceEl.textContent = "offline";
  };

    // --- Notify socket (status + notifications) ---
  const notifyUrl = `${proto}://${window.location.host}/ws/notify/`;
  const notifyWs = new WebSocket(notifyUrl);

  const statusDot = document.getElementById("statusDot");
  const statusText = document.getElementById("statusText");

  function setStatus(online){
    if (!statusDot || !statusText) return;
    statusDot.classList.toggle("status-online", online);
    statusDot.classList.toggle("status-offline", !online);
    statusText.textContent = online ? "online" : "offline";
  }

  function bumpBadge(elId){
    const el = document.getElementById(elId);
    if (!el) return;
    let v = parseInt(el.textContent || "0", 10);
    v += 1;
    el.textContent = String(v);
    el.style.display = "inline-block";
  }

  function clearBadge(elId) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.textContent = "0";
    el.style.display = "none";
  }

  function setUserDot(userId, online) {
    const dot = document.getElementById(`userdot-${userId}`);
    if (!dot) return;
    dot.classList.toggle("status-online", !!online);
    dot.classList.toggle("status-offline", !online);
  }

  // Czyścimy badge dla aktualnie otwartego scope przy wejściu
  if (ctx.isDM && ctx.dmId) clearBadge(`badge-dm-${ctx.dmId}`);
  if (!ctx.isDM && ctx.channelId) clearBadge(`badge-channel-${ctx.channelId}`);

  notifyWs.onopen = () => setStatus(true);
  notifyWs.onclose = () => setStatus(false);

  (async () => {
    try {
      const r = await fetch("/presence/");
      if (!r.ok) return;
      const j = await r.json();
      (j.online_user_ids || []).forEach(uid => setUserDot(uid, true));
    } catch { }
  })();

  notifyWs.onmessage = (ev) => {
    let data = {};
    try { data = JSON.parse(ev.data); } catch { return; }

    if (data.type === "presence.user") {
      setUserDot(data.user_id, !!data.online);
      return;
    }

    // Status potwierdzenia (opcjonalne)
    if (data.type === "status.self") {
      setStatus(!!data.online);
      return;
    }

    // Powiadomienie o nowej wiadomości w innym scope
    if (data.type === "notify.message") {
      const scope = data.scope || "";
      // Nie nabijaj badge jeśli user jest aktualnie w tym scope
      if (scope === `channel:${ctx.channelId}` || scope === `dm:${ctx.dmId}`) return;

      if (scope.startsWith("channel:")) {
        const id = scope.split(":")[1];
        bumpBadge(`badge-channel-${id}`);
      } else if (scope.startsWith("dm:")) {
        const id = scope.split(":")[1];
        bumpBadge(`badge-dm-${id}`);
      }
    }
  };

  document.addEventListener("click", async (e) => {
  const btn = e.target.closest(".reaction-btn");
  if (!btn) return;

  const mid = btn.dataset.mid;
  const emoji = btn.dataset.emoji;
  const fd = new FormData();
  fd.append("message_id", mid);
  fd.append("emoji", emoji);

  const resp = await fetch("/reactions/toggle/", {
    method: "POST",
    body: fd,
    headers: {"X-CSRFToken": getCookie("csrftoken")}
  });

  if (!resp.ok) return;
  const j = await resp.json();
  const box = document.getElementById(`rx-${j.message_id}`);
  if (box) {
    box.textContent = j.counts.map(x => `${x.emoji} ${x.c}`).join("  ");
  }
});

  document.addEventListener("click", async (e) => {
  const btn = e.target.closest(".report-btn");
  if (!btn) return;

  const uid = btn.dataset.uid;
  const uname = btn.dataset.uname;
  const reason = prompt(`Powód zgłoszenia użytkownika ${uname}:`);
  if (!reason) return;

  const fd = new FormData();
    fd.append("user_id", uid);
    fd.append("reason", reason);

    const resp = await fetch("/moderation/report/", {
      method: "POST",
      body: fd,
      headers: { "X-CSRFToken": getCookie("csrftoken") }
    });
    if (resp.ok) alert("Zgłoszenie wysłane.");
  });

  function appendMessage(m) {
    const wrap = document.createElement("div");
    wrap.className = "msg mb-2";
    wrap.dataset.id = m.id;

    const isOwner = (window.CURRENT_USER_ID && m.author_id === window.CURRENT_USER_ID);
    const canDelete = ctx.canDeleteAny || isOwner;

    wrap.innerHTML = `
    <div class="d-flex gap-2">
      <div class="msg-avatar">
        <div class="avatar-sm rounded-circle bg-secondary d-flex align-items-center justify-content-center">
          <span class="fw-bold">${(m.author || "?").slice(0, 1).toUpperCase()}</span>
        </div>
      </div>
      <div class="flex-grow-1">
        <div class="d-flex justify-content-between">
          <div>
            <span class="fw-bold">${escapeHtml(m.author || "")}</span>
            <span class="small text-secondary">${new Date(m.created_at).toLocaleString()}</span>
          </div>
          <div class="d-flex gap-1">
            ${canDelete ? `<button class="btn btn-sm btn-outline-danger py-0" onclick="deleteMessage(${m.id})">Usuń</button>` : ``}
            <button class="btn btn-sm btn-outline-info py-0 report-btn" data-uid="${m.author_id}" data-uname="${escapeHtml(m.author || "")}">Zgłoś</button>
          </div>
        </div>

        <div class="mt-1">
          ${m.text ? `<div class="msg-text">${escapeHtml(m.text)}</div>` : ``}
          ${m.image_url ? `<div class="mt-1"><img src="${m.image_url}" class="img-fluid rounded border border-secondary"></div>` : ``}
          ${m.audio_url ? `<div class="mt-1"><audio controls src="${m.audio_url}" class="w-100"></audio></div>` : ``}
        </div>

        <div class="mt-2 d-flex gap-2 align-items-center flex-wrap">
          <button type="button" class="btn btn-sm btn-outline-light py-0 reaction-btn" data-mid="${m.id}" data-emoji="👍">👍</button>
          <button type="button" class="btn btn-sm btn-outline-light py-0 reaction-btn" data-mid="${m.id}" data-emoji="😂">😂</button>
          <button type="button" class="btn btn-sm btn-outline-light py-0 reaction-btn" data-mid="${m.id}" data-emoji="❤️">❤️</button>

          <span class="small text-secondary ms-2" id="rx-${m.id}"></span>
        </div>
      </div>
    </div>
  `;

    messagesEl.appendChild(wrap);
    if (shouldAutoScroll()) {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }
  }

  function shouldAutoScroll() {
    if (!messagesEl) return false;
    const threshold = 80;
    return (messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight) < threshold;
  }

  function escapeHtml(s) {
    return (s || "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
  }

  window.sendMessage = function(){
    const text = (inputEl.value || "").trim();
    if (!text) return;
    ws.send(JSON.stringify({action:"send", text}));
    inputEl.value = "";
  };

  window.deleteMessage = function(id){
    ws.send(JSON.stringify({action:"delete", message_id:id}));
  };

  window.uploadAttachment = async function(){
    const img = document.getElementById("imageFile").files[0];
    const aud = document.getElementById("audioFile").files[0];
    const text = (inputEl.value || "").trim();

    if (!text && !img && !aud) return;

    const fd = new FormData();
    fd.append("scope", scope);
    fd.append("text", text);
    if (img) fd.append("image", img);
    if (aud) fd.append("audio", aud);

    const resp = await fetch("/upload/", { method: "POST", body: fd, headers: { "X-CSRFToken": getCookie("csrftoken") } });
    if (!resp.ok) return;

    await resp.json();
    inputEl.value = "";
    document.getElementById("imageFile").value = "";
    document.getElementById("audioFile").value = "";
  };

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + "=")) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  // Enter to send
  inputEl?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      window.sendMessage();
    }
  });

})();
