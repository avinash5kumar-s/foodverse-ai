"""Single-page web UI served at '/'. Photos are downscaled in the browser before upload."""

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Food Verse AI</title>
<style>
  :root { --bg:#faf7f2; --card:#fff; --ink:#1f2328; --muted:#6b7280; --accent:#e8590c; --line:#e5e0d8; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#17130f; --card:#221c16; --ink:#f3ede4; --muted:#a79c8e; --accent:#ff8a3d; --line:#3a3128; }
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--ink); font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
  main { max-width:680px; margin:0 auto; padding:28px 16px 64px; }
  h1 { margin:0 0 4px; font-size:28px; }
  .sub { color:var(--muted); margin:0 0 20px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px; }
  textarea { width:100%; min-height:84px; resize:vertical; border:1px solid var(--line); border-radius:10px;
             padding:10px; font:inherit; color:var(--ink); background:transparent; }
  .row { display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin-top:12px; }
  label.file { border:1px dashed var(--line); border-radius:10px; padding:8px 12px; cursor:pointer; color:var(--muted); }
  input[type=file] { display:none; }
  button { background:var(--accent); color:#fff; border:0; border-radius:10px; padding:10px 18px; font:inherit; font-weight:600; cursor:pointer; }
  button:disabled { opacity:.55; cursor:wait; }
  #preview { max-width:120px; max-height:120px; border-radius:10px; display:none; }
  #out { margin-top:18px; white-space:pre-wrap; }
  .err { color:#c92a2a; }
  details { margin-top:12px; color:var(--muted); font-size:14px; }
  pre { overflow:auto; font-size:12px; }
  .note { color:var(--muted); font-size:13px; margin-top:22px; }
</style>
</head>
<body>
<main>
  <h1>🍽️ Food Verse AI</h1>
  <p class="sub">Snap a meal or describe it. Get calories, macros and diet insights.</p>
  <div class="card">
    <textarea id="text" placeholder="e.g. 2 chapati, a bowl of dal and some paneer. Is this high protein?"></textarea>
    <div class="row">
      <label class="file" for="image">📷 Add photo</label>
      <input id="image" type="file" accept="image/*">
      <img id="preview" alt="preview">
      <button id="go">Analyze</button>
    </div>
  </div>
  <div id="out"></div>
  <details id="tools" hidden><summary>Tool calls</summary><pre id="toolsPre"></pre></details>
  <p class="note">Portion sizes from photos are estimates. Not medical advice.</p>
</main>
<script>
const $ = id => document.getElementById(id);
let blob = null;

// Downscale in the browser so uploads stay well under Vercel's ~4.5 MB body limit.
function shrink(file, maxSide = 1280, quality = 0.85) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const k = Math.min(1, maxSide / Math.max(img.width, img.height));
      const c = document.createElement('canvas');
      c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
      c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
      c.toBlob(b => b ? resolve(b) : reject(new Error('Could not process image')), 'image/jpeg', quality);
    };
    img.onerror = () => reject(new Error('Could not read that image'));
    img.src = URL.createObjectURL(file);
  });
}

$('image').addEventListener('change', async e => {
  const f = e.target.files[0];
  if (!f) { blob = null; $('preview').style.display = 'none'; return; }
  try {
    blob = await shrink(f);
    $('preview').src = URL.createObjectURL(blob);
    $('preview').style.display = 'block';
  } catch (err) { $('out').innerHTML = '<span class="err"></span>'; $('out').firstChild.textContent = err.message; }
});

$('go').addEventListener('click', async () => {
  const text = $('text').value.trim();
  if (!text && !blob) { $('out').textContent = 'Add a description or a photo first.'; return; }
  const fd = new FormData();
  fd.append('text', text);
  if (blob) fd.append('image', blob, 'meal.jpg');
  $('go').disabled = true; $('out').textContent = 'Analyzing…'; $('tools').hidden = true;
  try {
    const r = await fetch('/api/analyze', { method: 'POST', body: fd });
    let data = {};
    try { data = await r.json(); } catch { data = { error: 'Server returned an unexpected response (HTTP ' + r.status + ').' }; }
    if (!r.ok || data.error) throw new Error(data.error || 'Request failed');
    $('out').textContent = data.answer;
    if (data.tool_calls && data.tool_calls.length) {
      $('toolsPre').textContent = data.tool_calls.map(t => t.tool + '(' + JSON.stringify(t.input) + ')\n→ ' + t.output).join('\n\n');
      $('tools').hidden = false;
    }
  } catch (err) {
    $('out').innerHTML = '<span class="err"></span>';
    $('out').firstChild.textContent = err.message;
  } finally { $('go').disabled = false; }
});
</script>
</body>
</html>
"""
