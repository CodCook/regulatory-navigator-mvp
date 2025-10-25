/* QDB Regulatory Navigator - Application Logic */

(function () {
  // Wait for DOM
  document.addEventListener('DOMContentLoaded', function () {
    const runBtn = document.getElementById('runBtn');
    const runBtnTop = document.getElementById('runBtnTop');
    const loadSampleBtn = document.getElementById('loadSampleBtn');
    const status = document.getElementById('status');
    const scoreEl = document.getElementById('score');
    const scoreFill = document.getElementById('scoreFill');
    const breakdownBody = document.querySelector('#breakdown tbody');
    const recsEl = document.getElementById('recs');
    const fileInput = document.getElementById('fileInput');
    const runFilesBtn = document.getElementById('runFilesBtn');
    const fileInputLabel = document.getElementById('fileInputLabel');
    const downloadPdfBtn = document.getElementById('downloadPdfBtn');
    const downloadPdfBtn2 = document.getElementById('downloadPdfBtn2');
    const countrySelect = document.getElementById('countrySelect');
    const navLinks = document.querySelectorAll('.nav a');
    const pages = {
      dashboard: document.getElementById('page-dashboard'),
      reports: document.getElementById('page-reports')
    };
    const failedChecks = document.getElementById('failedChecks');
    const passedChecks = document.getElementById('passedChecks');
    const modalRoot = document.getElementById('modalRoot');
    const modalOverlay = document.getElementById('modalOverlay');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    const modalClose = document.getElementById('modalClose');

    // Store selected country
    let selectedCountry = 'qatar';

    // Country selection handler
    if (countrySelect) {
      countrySelect.addEventListener('change', function(e) {
        selectedCountry = e.target.value;
        console.log('Selected country:', selectedCountry);
        
        // Update header title based on country
        const headerTitle = document.querySelector('.header-title');
        const countryNames = {
          'qatar': 'QDB Regulatory Readiness Evaluator',
          'uae': 'UAE Regulatory Readiness Evaluator',
          'saudi': 'Saudi Arabia Regulatory Readiness Evaluator'
        };
        if (headerTitle) {
          headerTitle.textContent = countryNames[selectedCountry] || 'Regulatory Readiness Evaluator';
        }
        
        // Show notification
        status.textContent = `Switched to ${e.target.options[e.target.selectedIndex].text}`;
        status.style.color = '#5C2D91';
        setTimeout(() => {
          status.textContent = '';
        }, 3000);
      });
    }


    // Mapping from check name to regulation article id in regulation_texts.json
    const CHECK_TO_ARTICLE = {
      'Capital Shortfall': '1.2.2',
      'Data Residency Failure': '2.1.1',
      'Compliance Officer Missing': '2.2.1',
      'AML/CFT Policy Gap': '2.2.1',
      'Fit & Proper Docs Missing': '1.1.4',
      'AoA Submission': null
    };

    // Color mapping for checks
    const CHECK_COLOR = {
      'Capital Shortfall': 'status-red',
      'Data Residency Failure': 'status-red',
      'Compliance Officer Missing': 'status-amber',
      'AML/CFT Policy Gap': 'status-amber',
      'Fit & Proper Docs Missing': 'status-amber',
      'AoA Submission': 'status-green'
    };

    let regulationTexts = {}; // will load from server

    async function loadRegulationTexts() {
      try {
        const r = await fetch('/api/regulation_texts');
        if (r.ok) {
          regulationTexts = await r.json();
        }
      } catch (e) {
        console.warn('Could not load regulation_texts', e);
      }
    }

    // modal handlers
    if (modalClose) modalClose.addEventListener('click', () => { modalRoot.style.display = 'none'; });
    if (modalOverlay) modalOverlay.addEventListener('click', (ev) => { if (ev.target === modalOverlay) modalRoot.style.display = 'none'; });

    // Sample demo text (pastes into textarea when demoers click 'Load Sample Text')
    const SAMPLE_TEXT = `Paid-Up Capital: The company has a paid-up capital of QAR 5,000,000 reported in the AoA and capitalization schedule.\n\nBusiness Activity: The startup will operate a P2P lending platform (Category 2 payment service) and provide wallet services to Qatari residents.\n\nData Residency: Customer data is currently hosted across multiple cloud providers with primary backups in Ireland and Singapore. No explicit clause limits cross-border storage in the current hosting agreement.\n\nCompliance: The company documents do not list a named Compliance Officer or show board-approved AML/CFT policies. AML checks are performed ad-hoc by operations.\n\nAoA & Fit & Proper: A draft AoA exists but the founders have not signed the final version; fit-and-proper supporting documents (IDs, declarations) are incomplete.`;

    // wire sample loader
    if (loadSampleBtn) {
      loadSampleBtn.addEventListener('click', () => {
        const docsInput = document.getElementById('docsInput');
        if (docsInput) {
          docsInput.value = SAMPLE_TEXT;
          docsInput.focus();
        }
      });
    }

    async function runAssessment() {
      status.innerHTML = '<span class="spinner"></span> Running...';
      scoreEl.textContent = '—';
      breakdownBody.innerHTML = '';
      recsEl.innerHTML = '';

      try {
        const docsInput = document.getElementById('docsInput');
        const payloadText = docsInput && docsInput.value ? docsInput.value : '';
        const resp = await fetch('/api/scorecard', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ documents: payloadText })
        });
        if (!resp.ok) throw new Error('Server returned ' + resp.status);
        const data = await resp.json();
        window.__lastResult = data; // stash for PDF
        window.__lastAssessmentId = data.assessment_id || null;

        // Score
        scoreEl.textContent = data.readiness_score;
        // update progress bar and color
        const scoreVal = Number(data.readiness_score) || 0;
        scoreFill.style.width = Math.max(0, Math.min(100, scoreVal)) + '%';
        if (scoreVal >= 80) {
          scoreFill.style.background = 'linear-gradient(90deg,#2af,#2a9)';
        }
        else if (scoreVal >= 50) {
          scoreFill.style.background = 'linear-gradient(90deg,#ffb64d,#f08)';
        }
        else {
          scoreFill.style.background = 'linear-gradient(90deg,#f33,#a00)';
        }

        // load regulation texts for modal
        await loadRegulationTexts();

        // Breakdown
        breakdownBody.innerHTML = '';
        for (const row of data.score_breakdown) {
          const tr = document.createElement('tr');
          const colorCls = CHECK_COLOR[row.check] || (row.status === 'PASS' ? 'status-green' : 'status-amber');
          const statusText = row.status;
          tr.innerHTML = `
            <td>${row.check}</td>
            <td class="${colorCls} ${statusText === 'FAIL' ? 'clickable-status' : ''}" data-check="${row.check}">${statusText}</td>
            <td>${row.weight.toFixed(0)}</td>
            <td>${row.score_contribution.toFixed(0)}</td>
          `;
          // If it's a FAIL, make the status clickable to open transparency modal
          if (statusText === 'FAIL') {
            const statusCell = tr.querySelector('.clickable-status');
            statusCell.addEventListener('click', () => {
              const articleId = CHECK_TO_ARTICLE[row.check];
              modalTitle.textContent = row.check + (articleId ? (' — Article ' + articleId) : '');
              modalBody.textContent = articleId && regulationTexts[articleId] ? regulationTexts[articleId] : ('Original text not available for ' + row.check);
              modalRoot.style.display = 'block';
            });
          }
          breakdownBody.appendChild(tr);
        }

        // Recommendations (unified renderer)
        recsEl.innerHTML = '';
        const renderRecs = (recs) => {
          if (!recs || recs.length === 0) {
            recsEl.innerHTML = '<em>No recommendations found.</em>';
            return;
          }
          for (const rec of recs) {
            const container = document.createElement('div');
            const gap = document.createElement('h4');
            gap.textContent = rec.gap;
            container.appendChild(gap);
            if (!rec.resources || rec.resources.length === 0) {
              const p = document.createElement('p');
              p.innerHTML = '<em>No resource matches in the mapping file.</em>';
              container.appendChild(p);
            } else {
              const ul = document.createElement('ul');
              for (const r of rec.resources) {
                const li = document.createElement('li');
                const title = r.title || r.name || 'Resource';
                const typ = r.type || '';
                // Prefer link, then contact
                let contactHtml = '';
                const link = r.link || '';
                const contact = r.contact || '';
                if (link && (link.startsWith('http://') || link.startsWith('https://'))) {
                  contactHtml = `<a href="${link}" target="_blank" rel="noopener">${link}</a>`;
                } else if (contact) {
                  if (contact.includes('@')) {
                    contactHtml = `<a href="mailto:${contact}">${contact}</a>`;
                  } else if (contact.startsWith('http://') || contact.startsWith('https://')) {
                    contactHtml = `<a href="${contact}" target="_blank" rel="noopener">${contact}</a>`;
                  } else {
                    contactHtml = contact;
                  }
                } else {
                  contactHtml = 'no link/contact';
                }
                // Add a small type badge
                const badge = typ ? `<span style="background:#f0e8ff;color:#45206f;padding:2px 8px;border-radius:999px;font-size:12px; margin-left:6px">${typ}</span>` : '';
                li.innerHTML = `<strong>${title}</strong> ${badge} — ${contactHtml}`;
                ul.appendChild(li);
              }
              container.appendChild(ul);
            }
            recsEl.appendChild(container);
          }
        };
        renderRecs(data.recommendations);

        // Update dashboard stats
        if (failedChecks) {
          const failed = data.score_breakdown.filter(r => r.status === 'FAIL').length;
          failedChecks.textContent = failed;
        }
        if (passedChecks) {
          const passed = data.score_breakdown.filter(r => r.status === 'PASS').length;
          passedChecks.textContent = passed;
        }

        status.textContent = 'Done';
      } catch (err) {
        console.error(err);
        status.textContent = 'Error: ' + (err.message || err);
        scoreEl.textContent = '—';
      }
    }

    if (runBtn) runBtn.addEventListener('click', runAssessment);
    if (runBtnTop) runBtnTop.addEventListener('click', runAssessment);

    if (fileInput) fileInput.addEventListener('change', () => {
      if (fileInput.files && fileInput.files.length > 0) {
        const names = Array.from(fileInput.files).map(f => f.name).slice(0, 3).join(', ');
        fileInputLabel.textContent = fileInput.files.length > 3 ? names + ' +' + (fileInput.files.length - 3) + ' more' : names || 'Choose Files…';
      } else {
        fileInputLabel.textContent = 'Choose Files…';
      }
    });

    async function runAssessmentFiles() {
      status.innerHTML = '<span class="spinner"></span> Uploading & analyzing...';
      scoreEl.textContent = '—';
      breakdownBody.innerHTML = '';
      recsEl.innerHTML = '';
      try {
        if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
          throw new Error('Please choose one or more files');
        }
        const fd = new FormData();
        for (const f of fileInput.files) {
          fd.append('files', f);
        }
        const resp = await fetch('/api/scorecard_upload', { method: 'POST', body: fd });
        if (!resp.ok) throw new Error('Server returned ' + resp.status);
        const data = await resp.json();
        window.__lastResult = data; // stash for PDF
        window.__lastAssessmentId = data.assessment_id || null;
        // Reuse renderer
        const docsInput = document.getElementById('docsInput');
        if (docsInput) docsInput.value = '';
        scoreEl.textContent = data.readiness_score;
        const scoreVal = Number(data.readiness_score) || 0;
        scoreFill.style.width = Math.max(0, Math.min(100, scoreVal)) + '%';
        if (scoreVal >= 80) {
          scoreFill.style.background = 'linear-gradient(90deg,#2af,#2a9)';
        }
        else if (scoreVal >= 50) {
          scoreFill.style.background = 'linear-gradient(90deg,#ffb64d,#f08)';
        }
        else {
          scoreFill.style.background = 'linear-gradient(90deg,#f33,#a00)';
        }
        await loadRegulationTexts();
        breakdownBody.innerHTML = '';
        for (const row of data.score_breakdown) {
          const tr = document.createElement('tr');
          const colorCls = CHECK_COLOR[row.check] || (row.status === 'PASS' ? 'status-green' : 'status-amber');
          const statusText = row.status;
          tr.innerHTML = `
            <td>${row.check}</td>
            <td class="${colorCls} ${statusText === 'FAIL' ? 'clickable-status' : ''}" data-check="${row.check}">${statusText}</td>
            <td>${row.weight.toFixed(0)}</td>
            <td>${row.score_contribution.toFixed(0)}</td>
          `;
          if (statusText === 'FAIL') {
            const statusCell = tr.querySelector('.clickable-status');
            statusCell.addEventListener('click', () => {
              const articleId = CHECK_TO_ARTICLE[row.check];
              modalTitle.textContent = row.check + (articleId ? (' — Article ' + articleId) : '');
              modalBody.textContent = articleId && regulationTexts[articleId] ? regulationTexts[articleId] : ('Original text not available for ' + row.check);
              modalRoot.style.display = 'block';
            });
          }
          breakdownBody.appendChild(tr);
        }
        recsEl.innerHTML = '';
        if (!data.recommendations || data.recommendations.length === 0) {
          recsEl.innerHTML = '<em>No recommendations found.</em>';
        } else {
          for (const rec of data.recommendations) {
            const container = document.createElement('div');
            const gap = document.createElement('h4');
            gap.textContent = rec.gap;
            container.appendChild(gap);
            if (!rec.resources || rec.resources.length === 0) {
              const p = document.createElement('p');
              p.innerHTML = '<em>No resource matches in the mapping file.</em>';
              container.appendChild(p);
            } else {
              const ul = document.createElement('ul');
              for (const r of rec.resources) {
                const li = document.createElement('li');
                let contactHtml = r.contact || r.link || '';
                if (contactHtml && contactHtml.includes('@')) {
                  contactHtml = `<a href="mailto:${contactHtml}">${contactHtml}</a>`;
                } else if (contactHtml && (contactHtml.startsWith('http://') || contactHtml.startsWith('https://'))) {
                  contactHtml = `<a href="${contactHtml}" target="_blank" rel="noopener">${contactHtml}</a>`;
                }
                const title = r.title || r.name || 'Resource';
                const typ = r.type || '';
                li.innerHTML = `<strong>${title}</strong> (${typ}) — ${contactHtml}`;
                ul.appendChild(li);
              }
              container.appendChild(ul);
            }
            recsEl.appendChild(container);
          }
        }
        
        // Update dashboard stats
        if (failedChecks) {
          const failed = data.score_breakdown.filter(r => r.status === 'FAIL').length;
          failedChecks.textContent = failed;
        }
        if (passedChecks) {
          const passed = data.score_breakdown.filter(r => r.status === 'PASS').length;
          passedChecks.textContent = passed;
        }
        
        status.textContent = 'Done';
      } catch (e) {
        console.error(e);
        status.textContent = 'Error: ' + (e.message || e);
      }
    }

    if (runFilesBtn) runFilesBtn.addEventListener('click', runAssessmentFiles);

    async function downloadPdf() {
      try {
        status.textContent = 'Generating PDF...';
        const docsInput = document.getElementById('docsInput');
        const payloadText = docsInput && docsInput.value ? docsInput.value : '';
        // Prefer using the last assessment id (for file uploads or text runs)
        const body = {};
        if (window.__lastAssessmentId) {
          body.assessment_id = window.__lastAssessmentId;
        } else if (payloadText) {
          body.documents = payloadText;
        } else if (window.__lastResult) {
          body.result = window.__lastResult;
        }
        const resp = await fetch('/api/report', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        if (!resp.ok) throw new Error('Server returned ' + resp.status);
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'readiness_report.pdf';
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        status.textContent = 'PDF downloaded';
      } catch (e) {
        console.error(e);
        status.textContent = 'Error: ' + (e.message || e);
      }
    }
    if (downloadPdfBtn) downloadPdfBtn.addEventListener('click', downloadPdf);
    if (downloadPdfBtn2) downloadPdfBtn2.addEventListener('click', downloadPdf);

    // Simple SPA nav
    navLinks.forEach(a => a.addEventListener('click', (e) => {
      e.preventDefault();
      const page = a.getAttribute('data-page');
      navLinks.forEach(x => x.classList.remove('active'));
      a.classList.add('active');
      Object.values(pages).forEach(sec => sec.classList.remove('active'));
      if (pages[page]) pages[page].classList.add('active');
    }));

    // Allow Ctrl+Enter to run from textarea
    const docsInput = document.getElementById('docsInput');
    if (docsInput) {
      docsInput.addEventListener('keydown', function (e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
          runAssessment();
        }
      });
    }
  });
})();
