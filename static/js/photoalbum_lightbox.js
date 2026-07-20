(function () {
  'use strict';

  var SWIPE_MIN = 50;

  function bindSwipe(el, onLeft, onRight) {
    if (!el) return;
    var startX = null;
    var startY = null;
    el.addEventListener('touchstart', function (e) {
      if (!e.changedTouches || !e.changedTouches[0]) return;
      startX = e.changedTouches[0].clientX;
      startY = e.changedTouches[0].clientY;
    }, { passive: true });
    el.addEventListener('touchend', function (e) {
      if (startX == null || !e.changedTouches || !e.changedTouches[0]) return;
      var dx = e.changedTouches[0].clientX - startX;
      var dy = e.changedTouches[0].clientY - startY;
      startX = startY = null;
      if (Math.abs(dx) < SWIPE_MIN || Math.abs(dx) < Math.abs(dy)) return;
      if (dx < 0 && onLeft) onLeft();
      if (dx > 0 && onRight) onRight();
    }, { passive: true });
  }

  function initFullres() {
    var overlay = document.getElementById('photo-fullres');
    if (!overlay) return null;
    var img = overlay.querySelector('.photo-fullres-image');

    function open(url) {
      if (!url) return;
      img.src = url;
      overlay.hidden = false;
      document.body.style.overflow = 'hidden';
    }
    function close() {
      overlay.hidden = true;
      img.src = '';
      if (document.getElementById('photo-lightbox') && !document.getElementById('photo-lightbox').hidden) {
        document.body.style.overflow = 'hidden';
      } else {
        document.body.style.overflow = '';
      }
    }

    overlay.querySelectorAll('[data-fullres-close]').forEach(function (el) {
      el.addEventListener('click', close);
    });
    img.addEventListener('click', close);

    return { open: open, close: close, isOpen: function () { return !overlay.hidden; } };
  }

  function initAlbumLightbox(fullres) {
    var grid = document.getElementById('photoalbum-grid');
    var lightbox = document.getElementById('photo-lightbox');
    if (!grid || !lightbox) return;

    var images;
    try {
      images = JSON.parse(grid.getAttribute('data-album-images') || '[]');
    } catch (e) {
      images = [];
    }
    if (!images.length) return;

    var idx = 0;
    var lbImg = lightbox.querySelector('.photo-lightbox-image');
    var posEl = lightbox.querySelector('.photo-lightbox-position');
    var descEl = lightbox.querySelector('.photo-lightbox-description');
    var commentsEl = lightbox.querySelector('.photo-lightbox-comments');
    var prevBtn = lightbox.querySelector('.photo-lightbox-prev');
    var nextBtn = lightbox.querySelector('.photo-lightbox-next');

    function render() {
      var item = images[idx];
      if (!item) return;
      lbImg.src = item.full || item.thumb;
      lbImg.alt = item.description || '';
      posEl.textContent = (idx + 1) + ' / ' + images.length;
      if (item.description) {
        descEl.textContent = item.description;
        descEl.hidden = false;
      } else {
        descEl.textContent = '';
        descEl.hidden = true;
      }
      commentsEl.href = item.detailUrl + '#comments';
      var multi = images.length > 1;
      prevBtn.style.visibility = multi ? 'visible' : 'hidden';
      nextBtn.style.visibility = multi ? 'visible' : 'hidden';
    }

    function openAt(imageId) {
      var found = images.findIndex(function (img) { return String(img.id) === String(imageId); });
      if (found < 0) return;
      idx = found;
      render();
      lightbox.hidden = false;
      document.body.style.overflow = 'hidden';
    }

    function close() {
      if (fullres && fullres.isOpen()) {
        fullres.close();
        return;
      }
      lightbox.hidden = true;
      document.body.style.overflow = '';
    }

    function prev() {
      if (images.length < 2) return;
      idx = (idx - 1 + images.length) % images.length;
      render();
    }
    function next() {
      if (images.length < 2) return;
      idx = (idx + 1) % images.length;
      render();
    }

    grid.querySelectorAll('.photoalbum-thumb-open').forEach(function (btn) {
      btn.addEventListener('click', function () {
        openAt(btn.getAttribute('data-image-id'));
      });
    });

    lightbox.querySelectorAll('[data-lightbox-close]').forEach(function (el) {
      el.addEventListener('click', close);
    });
    prevBtn.addEventListener('click', prev);
    nextBtn.addEventListener('click', next);

    lbImg.addEventListener('click', function () {
      var item = images[idx];
      if (item && fullres) fullres.open(item.full || item.thumb);
    });

    document.addEventListener('keydown', function (e) {
      if (lightbox.hidden) return;
      if (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT') return;
      if (e.key === 'Escape') {
        e.preventDefault();
        close();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        prev();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        next();
      }
    });

    bindSwipe(lightbox.querySelector('.photo-lightbox-center'), next, prev);
  }

  function initDetailPage(fullres) {
    var pageImg = document.querySelector('.image-page-image');
    if (!pageImg || !fullres) return;

    var fullUrl = pageImg.getAttribute('data-full-url') || pageImg.src;
    pageImg.style.cursor = 'zoom-in';
    pageImg.addEventListener('click', function () {
      fullres.open(fullUrl);
    });

    var prev = document.querySelector('.image-nav-prev');
    var next = document.querySelector('.image-nav-next');

    document.addEventListener('keydown', function (e) {
      if (fullres.isOpen()) {
        if (e.key === 'Escape') {
          e.preventDefault();
          fullres.close();
        }
        return;
      }
      if (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT') return;
      if (e.key === 'ArrowLeft' && prev) { window.location = prev.href; }
      if (e.key === 'ArrowRight' && next) { window.location = next.href; }
    });

    var navCenter = document.querySelector('.image-nav-center');
    bindSwipe(navCenter, function () {
      if (next) window.location = next.href;
    }, function () {
      if (prev) window.location = prev.href;
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var fullres = initFullres();
    initAlbumLightbox(fullres);
    initDetailPage(fullres);
  });
})();
