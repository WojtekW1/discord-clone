(function(){
  if (!window.VOICE_CONTEXT) return;

  const voiceId = window.VOICE_CONTEXT.voiceId;
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const wsUrl = `${proto}://${window.location.host}/ws/voice/${voiceId}/`;
  const ws = new WebSocket(wsUrl);

  const peersUl = document.getElementById("voicePeers");
  const remoteAudioDiv = document.getElementById("voiceRemoteAudio");
  const btnMute = document.getElementById("btnMute");
  const btnLeave = document.getElementById("btnLeaveVoice");

  const pcs = new Map();          // userId -> RTCPeerConnection
  const remoteEls = new Map();    // userId -> <audio>
  let localStream = null;
  let muted = false;

  function addPeerLi(userId, label){
    if (!peersUl) return;
    const id = `peer-li-${userId}`;
    if (document.getElementById(id)) return;
    const li = document.createElement("li");
    li.id = id;
    li.textContent = label || `user ${userId}`;
    peersUl.appendChild(li);
  }
  function removePeerLi(userId){
    const el = document.getElementById(`peer-li-${userId}`);
    el?.remove();
  }

  async function ensureMic(){
    if (localStream) return localStream;
    localStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    return localStream;
  }

  function makePC(remoteUserId){
    const pc = new RTCPeerConnection({
      iceServers: [{ urls: ["stun:stun.l.google.com:19302"] }]
    });

    pc.onicecandidate = (ev) => {
      if (!ev.candidate) return;
      ws.send(JSON.stringify({
        type: "webrtc.ice",
        to: remoteUserId,
        data: ev.candidate
      }));
    };

    pc.ontrack = (ev) => {
      let a = remoteEls.get(remoteUserId);
      if (!a) {
        a = document.createElement("audio");
        a.autoplay = true;
        a.controls = true;
        a.dataset.uid = String(remoteUserId);
        remoteAudioDiv?.appendChild(a);
        remoteEls.set(remoteUserId, a);
      }
      a.srcObject = ev.streams[0];
    };

    pcs.set(remoteUserId, pc);
    return pc;
  }

  async function call(remoteUserId){
    const stream = await ensureMic();
    const pc = pcs.get(remoteUserId) || makePC(remoteUserId);

    stream.getTracks().forEach(t => pc.addTrack(t, stream));
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    ws.send(JSON.stringify({
      type: "webrtc.offer",
      to: remoteUserId,
      data: offer
    }));
  }

  ws.onmessage = async (ev) => {
    const msg = JSON.parse(ev.data);

    if (msg.type === "peer.join") {
      addPeerLi(msg.user_id, msg.username);
      // prosta reguła: dzwoni ten z mniejszym id, żeby uniknąć podwójnych offerów
      if (window.CURRENT_USER_ID && window.CURRENT_USER_ID < msg.user_id) {
        await call(msg.user_id);
      }
      return;
    }

    if (msg.type === "peer.leave") {
      removePeerLi(msg.user_id);
      const pc = pcs.get(msg.user_id);
      if (pc) pc.close();
      pcs.delete(msg.user_id);

      const a = remoteEls.get(msg.user_id);
      a?.remove();
      remoteEls.delete(msg.user_id);
      return;
    }

    // relay: każdy filtruje po "to"
    if (msg.to && window.CURRENT_USER_ID && msg.to !== window.CURRENT_USER_ID) return;

    if (msg.type === "webrtc.offer") {
      addPeerLi(msg.from, msg.from_name);
      const stream = await ensureMic();
      const pc = pcs.get(msg.from) || makePC(msg.from);

      stream.getTracks().forEach(t => pc.addTrack(t, stream));

      await pc.setRemoteDescription(new RTCSessionDescription(msg.data));
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);

      ws.send(JSON.stringify({
        type: "webrtc.answer",
        to: msg.from,
        data: answer
      }));
      return;
    }

    if (msg.type === "webrtc.answer") {
      const pc = pcs.get(msg.from);
      if (!pc) return;
      await pc.setRemoteDescription(new RTCSessionDescription(msg.data));
      return;
    }

    if (msg.type === "webrtc.ice") {
      const pc = pcs.get(msg.from) || makePC(msg.from);
      try {
        await pc.addIceCandidate(new RTCIceCandidate(msg.data));
      } catch {}
      return;
    }
  };

  btnMute?.addEventListener("click", () => {
    if (!localStream) return;
    muted = !muted;
    localStream.getAudioTracks().forEach(t => t.enabled = !muted);
    btnMute.textContent = muted ? "Unmute" : "Mute";
  });

  btnLeave?.addEventListener("click", () => {
    // wyłącz lokalny stream
    if (localStream) {
      localStream.getTracks().forEach(t => t.stop());
    }
    // zamknij peer connections
    pcs.forEach(pc => pc.close());
    pcs.clear();
    // zamknij ws
    ws.close();
    // wróć do home
    window.location.href = "/";
  });
})();