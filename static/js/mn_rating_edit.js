document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('[data-mn-rating-edit]').forEach(function (row) {
    var display = row.querySelector('.mn-score-display');
    var form = row.querySelector('.mn-score-edit-form');
    var input = form && form.querySelector('input[name="rating"]');
    var editBtn = row.querySelector('.mn-rating-edit-toggle');
    if (!display || !form || !input || !editBtn) {
      return;
    }

    function openEdit() {
      display.hidden = true;
      form.hidden = false;
      editBtn.hidden = true;
      input.focus();
      input.select();
    }

    function closeEdit() {
      form.hidden = true;
      display.hidden = false;
      editBtn.hidden = false;
    }

    editBtn.addEventListener('click', function (e) {
      e.preventDefault();
      openEdit();
    });

    input.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        e.preventDefault();
        closeEdit();
      }
    });
  });
});
