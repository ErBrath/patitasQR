/* =========================
   Módulo: Insumos (sólo si existe en la página)
   ========================= */
(() => {
  const cont = document.getElementById('insumos-rows');
  const addBtn = document.getElementById('add-row');
  if (!cont || !addBtn) return; // <- evita error en páginas sin el formulario

  const base = cont.querySelector('.row');
  if (!base) return;

  addBtn.addEventListener('click', () => {
    const clone = base.cloneNode(true);

    // limpia los valores del clon
    const sel = clone.querySelector('select');
    if (sel) sel.selectedIndex = 0;
    const qty = clone.querySelector('input[name="cantidad[]"]');
    if (qty) qty.value = '';

    cont.appendChild(clone);
  });

  cont.addEventListener('click', (e) => {
    const btn = e.target.closest('.rm-row');
    if (!btn) return;

    const rows = cont.querySelectorAll('.row');
    if (rows.length > 1) {
      btn.closest('.row').remove();
    }
  });
})();


/* =========================
   Módulo: Toggle de tema
   ========================= */
(() => {
  const btn = document.getElementById('theme-toggle');
  if (!btn) return; // si no hay botón, no hacemos nada

  const getSaved = () => {
    try { return localStorage.getItem('theme'); } catch { return null; }
  };
  const getSystem = () =>
    window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';

  const current = () => {
    const forced = document.documentElement.getAttribute('data-theme');
    return forced || getSystem();
  };

  const apply = (theme) => {
    document.documentElement.setAttribute('data-theme', theme);
    try { localStorage.setItem('theme', theme); } catch {}
    btn.textContent = theme === 'dark' ? '☀️' : '🌙';
    btn.setAttribute('aria-pressed', theme === 'dark');
  };

  // estado inicial (prioriza guardado)
  const saved = getSaved();
  apply(saved === 'dark' || saved === 'light' ? saved : current());

  btn.addEventListener('click', () => {
    const next = current() === 'dark' ? 'light' : 'dark';
    apply(next);
  });
})();

// ver/ocultar contraseña
(() => {
  const input = document.getElementById('password');
  const toggle = document.querySelector('.pw-toggle');
  if (!input || !toggle) return;

  const apply = (show) => {
    input.type = show ? 'text' : 'password';
    toggle.textContent = show ? '🙈' : '👁️';
    toggle.setAttribute('aria-pressed', show);
  };

  let visible = false;
  apply(visible);

  toggle.addEventListener('click', () => {
    visible = !visible;
    apply(visible);
  });
})();

// Menú móvil
(() => {
  const toggle = document.getElementById('nav-toggle');
  const panel  = document.getElementById('nav-links');
  if (!toggle || !panel) return;

  const open = (v) => {
    panel.classList.toggle('is-open', v);
    toggle.setAttribute('aria-expanded', v);
    toggle.setAttribute('aria-label', v ? 'Cerrar menú' : 'Abrir menú');
  };

  toggle.addEventListener('click', () => open(!panel.classList.contains('is-open')));

  // Cerrar al hacer clic fuera
  document.addEventListener('click', (e) => {
    if (!panel.classList.contains('is-open')) return;
    if (!panel.contains(e.target) && e.target !== toggle) open(false);
  });

  // Cerrar con Esc
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && panel.classList.contains('is-open')) open(false);
  });
})();


// Lightbox con navegación (prev/next, ESC, clic fuera)
(() => {
  // Crear overlay una sola vez
  const overlay = document.createElement('div');
  overlay.className = 'lightbox';
  overlay.innerHTML = `
    <button type="button" class="lightbox__close" aria-label="Cerrar">✕</button>
    <div class="lightbox__nav">
      <button type="button" class="lightbox__btn lightbox__btn--prev" aria-label="Anterior">‹</button>
      <button type="button" class="lightbox__btn lightbox__btn--next" aria-label="Siguiente">›</button>
    </div>
    <div>
      <img class="lightbox__img" alt="">
      <div class="lightbox__caption" aria-live="polite"></div>
      <div class="lightbox__counter"></div>
    </div>
  `;
  document.body.appendChild(overlay);

  const imgEl      = overlay.querySelector('.lightbox__img');
  const captionEl  = overlay.querySelector('.lightbox__caption');
  const counterEl  = overlay.querySelector('.lightbox__counter');
  const closeBtn   = overlay.querySelector('.lightbox__close');
  const prevBtn    = overlay.querySelector('.lightbox__btn--prev');
  const nextBtn    = overlay.querySelector('.lightbox__btn--next');

  let group = [];   // lista de {el, src, alt}
  let idx   = -1;

  const updateNavState = () => {
    // Deshabilita flechas al llegar a extremos (no-loop). Si quieres loop, comenta estas dos líneas:
    prevBtn.disabled = (idx <= 0);
    nextBtn.disabled = (idx >= group.length - 1);
    // contador
    counterEl.textContent = group.length > 1 ? `${idx + 1} / ${group.length}` : '';
  };

  const showIndex = (i) => {
    if (i < 0 || i >= group.length) return;
    idx = i;
    const it = group[idx];
    imgEl.src = it.src;
    imgEl.alt = it.alt || '';
    captionEl.textContent = it.alt || '';
    updateNavState();
  };

  const open = (startEl) => {
    // Determinar grupo: si la imagen está dentro de un contenedor “galería”, usa ese contenedor
    // Ajusta aquí si usas otros contenedores: .media-grid, .detail-photos, etc.
    const gallery = startEl.closest('.media-grid, .detail-photo, main') || document;
    const candidates = [...gallery.querySelectorAll('img')]
      .filter(img => {
        if (img.classList.contains('no-zoom')) return false;
        if (img.closest('.qr-box')) return false;
        return true;
      });

    group = candidates.map(el => ({ el, src: el.src, alt: el.getAttribute('alt') || '' }));
    // Fallback: si por alguna razón quedó vacío, usa solo la imagen clickeada
    if (group.length === 0) group = [{ el: startEl, src: startEl.src, alt: startEl.alt || '' }];

    // index inicial
    idx = Math.max(0, group.findIndex(it => it.el === startEl));

    overlay.classList.add('is-open');
    showIndex(idx);
  };

  const close = () => {
    overlay.classList.remove('is-open');
    imgEl.src = ''; imgEl.alt = ''; captionEl.textContent = ''; counterEl.textContent = '';
    group = []; idx = -1;
  };

  // Eventos de navegación
  prevBtn.addEventListener('click', () => { if (idx > 0) showIndex(idx - 1); });
  nextBtn.addEventListener('click', () => { if (idx < group.length - 1) showIndex(idx + 1); });

  // Cerrar con clic fuera o botón
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay || e.target === closeBtn) close();
  });

  // Teclado: ESC para cerrar, ←/→ para navegar
  document.addEventListener('keydown', (e) => {
    if (!overlay.classList.contains('is-open')) return;
    if (e.key === 'Escape') close();
    else if (e.key === 'ArrowLeft' && idx > 0) showIndex(idx - 1);
    else if (e.key === 'ArrowRight' && idx < group.length - 1) showIndex(idx + 1);
  });

  // Delegación: abrir lightbox al hacer clic en imágenes del <main>
  document.addEventListener('click', (e) => {
    const img = e.target.closest('main img');
    if (!img) return;
    if (img.classList.contains('no-zoom')) return;
    if (img.closest('.qr-box')) return; // no ampliar QR
    e.preventDefault();
    open(img);
  });
})();


// Navegar al hacer clic en cualquier parte de la fila de la tabla de tratamientos
(() => {
  document.addEventListener('click', (e) => {
    const row = e.target.closest('tr.row-link');
    if (!row) return;
    // No interceptar si se hizo clic en un botón o enlace dentro de la fila
    if (e.target.closest('button, a, select, input, label, form')) return;
    const href = row.getAttribute('data-href');
    if (href) window.location.href = href;
  });
})();
