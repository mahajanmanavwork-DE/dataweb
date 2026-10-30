path = r"C:\Users\mahaj\Desktop\college-prac-2\templates\info.html"
html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Data Weaber — Info</title>
<link rel="stylesheet" href="/static/style.css">
<style>
:root{--ink:#0b1220;--slate:#1a2a3a;--gold:#d4a843;--gold-soft:#f4e9c6;--blue:#2e5a88;--blue-deep:#1c3a5c;--cream:#faf8f5;--surface:#ffffff;--text:#1f2937;--text-muted:#5b6b7b;--radius:18px;--shadow:0 12px 32px rgba(11,18,32,0.08);--shadow-hover:0 20px 48px rgba(11,18,32,0.14);}
*{box-sizing:border-box;}
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:var(--cream);color:var(--text);line-height:1.65;margin:0;padding-bottom:0;}
.hero{background:linear-gradient(160deg,var(--blue-deep) 0%,var(--blue) 55%,#3d6fa8 100%);position:relative;overflow:hidden;padding:72px 24px 100px;text-align:center;border-bottom-left-radius:48px;border-bottom-right-radius:48px;box-shadow:inset 0 -12px 30px rgba(0,0,0,0.15);}
.hero::before{content:"";position:absolute;inset:0;background:url("data:image/svg+xml,%3Csvg width='60' height='60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' stroke='%23ffffff' stroke-opacity='0.06'%3E%3Cpath d='M0 30h60M30 0v60'/%3E%3C/g%3E%3C/svg%3E");pointer-events:none;opacity:0.7}
.hero h1{font-family:Georgia,"Times New Roman",serif;font-size:clamp(30px,5vw,52px);font-weight:700;color:#fff;letter-spacing:-0.025em;margin-bottom:12px;text-shadow:0 4px 18px rgba(0,0,0,0.22);position:relative;z-index:2}
.hero p{color:rgba(255,255,255,0.85);font-size:clamp(15px,2vw,19px);max-width:640px;margin:0 auto;position:relative;z-index:2}
.hero .label{display:inline-block;background:rgba(255,255,255,0.12);backdrop-filter:blur(6px);border:1px solid rgba(255,255,255,0.18);color:#fff;padding:6px 16px;border-radius:999px;font-size:12px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:18px}
.tags{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-top:28px;position:relative;z-index:2}
.tag{padding:8px 18px;border-radius:999px;font-size:12px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;background:#fff;color:var(--ink);box-shadow:0 4px 12px rgba(0,0,0,0.1);transition:transform .15s ease}
.tag:hover{transform:translateY(-3px);box-shadow:0 8px 20px rgba(0,0,0,0.14)}
.tag.accent{background:var(--gold);color:#2b1f08}
.container{max-width:980px;margin:0 auto;padding:56px 24px 100px}
.section{margin-bottom:72px}
.section h2{font-family:Georgia,serif;font-size:26px;color:var(--ink);margin-bottom:28px;letter-spacing:-0.01em;position:relative;padding-left:18px}
.section h2::before{content:"";position:absolute;left:0;top:50%;transform:translateY(-50%);width:5px;height:28px;background:linear-gradient(180deg,var(--gold),var(--blue-deep));border-radius:999px}
.section p{color:var(--text-muted);font-size:15.5px;line-height:1.75}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:22px}
.card{background:var(--surface);border:1px solid rgba(11,18,32,0.06);border-radius:var(--radius);padding:28px;box-shadow:var(--shadow);transition:box-shadow .2s ease,transform .2s ease;position:relative}
.card:hover{box-shadow:var(--shadow-hover);transform:translateY(-4px)}
.card .icon{width:42px;height:42px;border-radius:12px;background:linear-gradient(135deg,var(--gold),#b08d2e);display:flex;align-items:center;justify-content:center;margin-bottom:16px;color:#fff;font-size:20px;box-shadow:0 6px 16px rgba(212,168,67,0.25)}
.card h3{font-family:Georgia,serif;font-size:18px;color:var(--ink);margin-bottom:10px}
.card p{font-size:14.5px;color:var(--text-muted);line-height:1.7;margin:0}
.card .list{margin:14px 0 0;padding-left:18px;font-size:14px;color:var(--text-muted)}
.card .list li{margin-bottom:6px}
.card .list .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:8px;vertical-align:middle}
.feature-row{display:flex;align-items:flex-start;gap:20px;margin-top:28px;padding:20px 22px;background:rgba(255,255,255,0.7);backdrop-filter:blur(10px);border:1px solid rgba(11,18,32,0.06);border-radius:14px;box-shadow:0 6px 18px rgba(11,18,32,0.04)}
.feature-number{font-family:Georgia,serif;font-size:32px;font-weight:700;color:var(--gold);line-height:1;min-width:48px;text-align:center}
.feature-content h4{font-size:16px;color:var(--ink);margin-bottom:6px}
.feature-content p{font-size:14px;color:var(--text-muted);margin:0;line-height:1.6}
.divider{max-width:980px;margin:0 auto;height:1px;background:linear-gradient(90deg,transparent,rgba(11,18,32,0.08),transparent)}
.cta{background:linear-gradient(160deg,var(--ink) 0%,var(--slate) 100%);border-radius:var(--radius);padding:48px 32px;text-align:center;color:#fff;position:relative;overflow:hidden;box-shadow:inset 0 -8px 24px rgba(0,0,0,0.2)}
.cta::after{content:"";position:absolute;top:-30%;right:-10%;width:320px;height:320px;background:radial-gradient(circle,rgba(212,168,67,0.25),transparent 70%);border-radius:50%}
.cta h3{font-family:Georgia,serif;font-size:26px;margin-bottom:8px;position:relative;z-index:2}
.cta p{color:rgba(255,255,255,0.75);font-size:15px;margin-bottom:24px;position:relative;z-index:2}
.cta a{display:inline-block;background:var(--gold);color:#2b1f08;padding:14px 28px;border-radius:999px;font-weight:700;text-decoration:none;transition:transform .15s ease,box-shadow .15s ease;box-shadow:0 8px 20px rgba(212,168,67,0.3);position:relative;z-index:2}
.cta a:hover{transform:translateY(-3px);box-shadow:0 12px 28px rgba(212,168,67,0.4)}
.footer{max-width:980px;margin:0 auto;padding:24px 24px 36px;text-align:center;color:#8892a3;font-size:13px;letter-spacing:0.02em}
@media (max-width:640px){.container{padding:36px 18px 60px}.section{margin-bottom:48px}.hero{border-bottom-left-radius:32px;border-bottom-right-radius:32px;padding:56px 18px 72px}.grid{grid-template-columns:1fr}.feature-row{flex-direction:column;gap:14px}.cta{padding:36px 22px}}
</style>
</head>
<body>
<header class="hero">
<div class="label">Visual Data Preprocessing</div>
<h1>Data Weaber</h1>
<p>A server-deployed, authorized-access platform for guided SQL-style file transformations.</p>
<div class="tags">
<span class="tag">CSV</span><span class="tag">JSON</span><span class="tag">Parquet</span><span class="tag accent">Excel</span><span class="tag">Server Deployable</span><span class="tag">Authorized Access</span>
</div>
</header>
<main class="container">
<section class="section">
<h2>Who This Serves Best</h2>
<p>This tool is built for people who need to process structured files quickly, securely, and without deep database or programming overhead. Whether you are an analyst cleaning a dataset, a student learning SQL concepts visually, or a small team sharing a server-based workspace, the guided forms and authorized access make it practical.</p>
<div class="grid">
<div class="card">
<div class="icon">&#128101;</div>
<h3>Analysts & Students</h3>
<p>Filter, sort, group, and export without writing raw SQL or Python scripts. Real-time previews reduce errors.</p>
</div>
<div class="card">
<div class="icon">&#127760;</div>
<h3>Server Deployable</h3>
<p>Run behind a reverse proxy or container. Portable <code>.env</code> paths resolve relative to each file — no hardcoded paths.</p>
</div>
<div class="card">
<div class="icon">&#128274;</div>
<h3>Authorized Access</h3>
<p>Per-user login, session control, isolated operations, operation logs, and history tracking by default.</p>
</div>
<div class="card">
<div class="icon">&#9881;</div>
<h3>Educators & Labs</h3>
<p>Demonstrate WHERE, GROUP BY, ORDER BY, window functions, and aggregations through guided forms.</p>
</div>
</div>
</section>
<section class="section">
<h2>What You Can Do</h2>
<p>Every action is handled server-side through the interactive footer panel. You open a file, select operations, and preview results immediately.</p>
<div class="feature-row">
<div class="feature-number">01</div>
<div class="feature-content"><h4>Open & Preview</h4><p>Scan folders, open CSV/JSON/Parquet/Excel files, and preview columns with data types.</p></div>
</div>
<div class="feature-row">
<div class="feature-number">02</div>
<div class="feature-content"><h4>Transform Columns</h4><p>Rename, delete, reorder columns with drag-and-drop and form-based actions.</p></div>
</div>
<div class="feature-row">
<div class="feature-number">03</div>
<div class="feature-content"><h4>Query Operations</h4><p>Filter, limit, offset, order by, distinct, group by with aggregations, and window functions.</p></div>
</div>
<div class="feature-row">
<div class="feature-number">04</div>
<div class="feature-content"><h4>Export Results</h4><p>Write outputs as CSV, JSON, Parquet, or Excel directly to your output folder.</p></div>
</div>
</section>
<div class="divider"></div>
<section class="section" style="margin-top:56px">
<h2>Deployment & Security</h2>
<p>The application runs securely on the server. Session middleware protects access, and user state — selected files, operations, and logs — is isolated per account. Deploy with Uvicorn or Gunicorn; the environment file resolves paths relative to the file location, making it portable across devices.</p>
<div class="grid">
<div class="card"><h3>FastAPI Backend</h3><p>Lightweight, async-capable Python web framework with session middleware and Jinja2 templates.</p></div>
<div class="card"><h3>Pandas Processing</h3><p>File transformations execute server-side through Pandas, ensuring consistent results regardless of browser.</p></div>
<div class="card"><h3>Authorized Sessions</h3><p>Every user has isolated session state, operation logs, and file access. Admin account is created on startup.</p></div>
</div>
</section>
<section class="cta" aria-label="Deployment call to action">
<h3>Ready for production?</h3>
<p>Deploy the server, configure your environment variables, and share secure access with your team.</p>
<a href="/">Back to Home</a>
</section>
</main>
<footer class="footer">Data Weaber — Visual File Preprocessing. Server-side operations. Authorized access only.</footer>
</body>
</html>'''
open(path, "w", encoding="utf-8").write(html)
print("written")
