const $ = (q) => document.querySelector(q);
const safe = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dateLabel = (d) => new Date(`${d}T12:00:00`).toLocaleDateString('ru-RU',{day:'numeric',month:'long',year:'numeric'});
let dashboardData;

async function api(url, options={}) {
  const response = await fetch(url,{headers:{'Content-Type':'application/json',...(options.headers||{})},...options});
  if(!response.ok) { let message=await response.text(); try { message=JSON.parse(message).detail||message; } catch {} throw new Error(message); }
  return response;
}
async function loadDashboard(){
  dashboardData=await (await api('/api/dashboard')).json();
  $('#demo-banner').classList.toggle('hidden',!dashboardData.demo_mode);
  $('#new-meeting').textContent=dashboardData.demo_mode?'＋ Новая встречa':'＋ New meeting / Upload recording';
  $('#stat-meetings').textContent=dashboardData.meeting_count;
  $('#stat-actions').textContent=dashboardData.action_count;
  $('#stat-overdue').textContent=dashboardData.overdue_count;
  $('#stat-completed').textContent=dashboardData.completed_count;
  $('#meetings-list').innerHTML=dashboardData.meetings.map((m,i)=>`<article class="meeting-card" data-meeting="${m.id}"><div class="meeting-icon">▤</div><div class="meeting-info"><h3>${safe(m.title)}</h3><p>${dateLabel(m.meeting_date)} · Протокол встречи</p></div><div class="meeting-meta"><span>${i===0?'3':'2'} участника</span><div class="mini-avatars"><span>А</span><span>З</span><span>Д</span></div><span class="arrow">→</span></div></article>`).join('')||'<p class="subtitle">Пока нет встреч. Создайте первую.</p>';
  document.querySelectorAll('[data-meeting]').forEach(el=>el.addEventListener('click',()=>openMeeting(el.dataset.meeting)));
}
function statusClass(s){return s==='Completed'?'completed':s==='Overdue'?'overdue':'progress'}
function statusRu(s){return s==='Completed'?'Выполнено':s==='Overdue'?'Просрочено':'В работе'}
async function openMeeting(id){
  const data=await (await api(`/api/meetings/${id}`)).json();
  if(data.meeting.processing_status==='failed'){alert(data.meeting.processing_error||'Local transcription failed.');return;}
  $('#dashboard-view').classList.add('hidden');$('#meeting-view').classList.remove('hidden');
  const speakers=data.speakers.map(s=>`<label class="speaker-chip"><i class="speaker-dot"></i><span>${safe(s.speaker_key.replace('SPEAKER_','Спикер '))}</span><input aria-label="Имя спикера" data-speaker="${safe(s.speaker_key)}" value="${safe(s.display_name)}" title="Измените имя и нажмите Enter"></label>`).join('');
  const transcript=data.segments.map(s=>`<div class="transcript-row"><span class="timestamp">${String(Math.floor(s.start_seconds/60)).padStart(2,'0')}:${String(Math.floor(s.start_seconds%60)).padStart(2,'0')}</span><span class="transcript-speaker">${safe(s.display_name)}</span><span class="transcript-text">${safe(s.text)} <small class="lang">${safe(s.language)}</small></span></div>`).join('');
  const actions=data.action_items.map(a=>`<tr><td>${safe(a.task)}<div class="source">${safe(a.source)}</div></td><td>${safe(a.responsible_person)}</td><td>${safe(a.deadline)}</td><td><button class="status ${statusClass(a.status)}" data-status="${a.id}" title="Нажмите, чтобы изменить статус">${statusRu(a.status)} ▾</button></td><td class="confidence">${Math.round(a.confidence*100)}%</td></tr>`).join('');
  $('#meeting-content').innerHTML=`<div class="detail-heading"><div><p class="eyebrow">ПРОТОКОЛ ВСТРЕЧИ</p><h1>${safe(data.meeting.title)}</h1><p>${dateLabel(data.meeting.meeting_date)} · ${data.speakers.length} участника · Русский + Қазақша + mixed</p></div><div class="export-actions"><a class="button secondary" href="/api/meetings/${id}/export/docx">↓ DOCX</a><a class="button primary" href="/api/meetings/${id}/export/pdf">↓ PDF</a></div></div><article class="summary-card"><h2>✦ Краткое содержание</h2><p>${safe(data.meeting.summary)}</p></article><article class="panel"><h2>Участники <small>· измените имя, нажав Enter</small></h2><div class="speaker-list">${speakers}</div></article><article class="panel"><h2>Транскрипт</h2>${transcript}</article><article class="panel"><h2>Поручения команды <small>· статус можно изменить нажатием</small></h2><div class="table-wrap"><table><thead><tr><th>ЗАДАЧА / КОНТЕКСТ</th><th>ОТВЕТСТВЕННЫЙ</th><th>СРОК</th><th>СТАТУС</th><th>УВЕРЕННОСТЬ</th></tr></thead><tbody>${actions}</tbody></table></div></article>`;
  document.querySelectorAll('[data-status]').forEach(button=>button.addEventListener('click',async()=>{const next=button.classList.contains('progress')?'Completed':button.classList.contains('completed')?'Overdue':'In progress';await api(`/api/action-items/${button.dataset.status}`,{method:'PATCH',body:JSON.stringify({status:next})});await openMeeting(id);await loadDashboard()}));
  document.querySelectorAll('[data-speaker]').forEach(input=>input.addEventListener('keydown',async e=>{if(e.key==='Enter'){e.preventDefault();await api(`/api/meetings/${id}/speakers/${encodeURIComponent(input.dataset.speaker)}`,{method:'PATCH',body:JSON.stringify({display_name:input.value})});await openMeeting(id)}}));
}
function showHome(){ $('#meeting-view').classList.add('hidden');$('#dashboard-view').classList.remove('hidden');loadDashboard(); }
$('#back').addEventListener('click',showHome);
$('#new-meeting').addEventListener('click',()=>{if(dashboardData&&!dashboardData.demo_mode){$('#dashboard-view').classList.add('hidden');$('#meeting-view').classList.add('hidden');$('#upload-dialog').classList.remove('hidden');$('#upload-form').reset();$('#upload-error').classList.add('hidden');return;}const d=new Date();$('#meeting-form [name=meeting_date]').value=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;$('#new-dialog').showModal()});
$('#dialog-close').addEventListener('click',()=>$('#new-dialog').close());$('#cancel-create').addEventListener('click',()=>$('#new-dialog').close());
$('#meeting-form').addEventListener('submit',async e=>{e.preventDefault();const f=new FormData(e.currentTarget);const m=await(await api('/api/meetings',{method:'POST',body:JSON.stringify({title:f.get('title'),meeting_date:f.get('meeting_date')})})).json();$('#new-dialog').close();await loadDashboard();await openMeeting(m.id)});
$('#upload-cancel').addEventListener('click',()=>{$('#upload-dialog').classList.add('hidden');$('#dashboard-view').classList.remove('hidden')});
$('#upload-form').addEventListener('submit',async e=>{e.preventDefault();const button=$('#upload-submit'),error=$('#upload-error');button.disabled=true;button.textContent='Uploading and transcribing locally…';error.classList.add('hidden');try{const response=await fetch('/api/meetings/upload',{method:'POST',body:new FormData(e.currentTarget)});if(!response.ok){let msg=await response.text();try{msg=JSON.parse(msg).detail||msg}catch{}throw new Error(msg)}const meeting=await response.json();$('#upload-dialog').classList.add('hidden');await loadDashboard();await openMeeting(meeting.id)}catch(err){error.textContent=err.message||'Local transcription failed.';error.classList.remove('hidden')}finally{button.disabled=false;button.textContent='Upload and transcribe locally'}});
$('#see-all').addEventListener('click',()=>document.querySelector('#meetings').scrollIntoView({behavior:'smooth'}));
loadDashboard().catch(e=>{console.error(e);$('#meetings-list').innerHTML='<p>Не удалось подключиться к серверу. Проверьте, что приложение запущено.</p>'});
