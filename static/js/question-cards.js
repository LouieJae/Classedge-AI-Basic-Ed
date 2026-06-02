(function () {
  "use strict";

  /* ------------------------------------------------------------------
     Quiz-type metadata for icons and picker groups. Backend enum values
     are used verbatim as keys; serialization round-trips them unchanged.
     ------------------------------------------------------------------ */
  var QUIZ_TYPE_META = {
    "Multiple Choice":    { icon: "fas fa-list-ul",     group: "Auto-graded" },
    "True/False":         { icon: "fas fa-toggle-on",   group: "Auto-graded" },
    "Fill in the Blank":  { icon: "fas fa-keyboard",    group: "Auto-graded" },
    "Matching Type":      { icon: "fas fa-link",        group: "Auto-graded" },
    "Calculated Numeric": { icon: "fas fa-calculator",  group: "Auto-graded" },
    "Essay":              { icon: "fas fa-align-left",  group: "Manual" },
    "Document":           { icon: "fas fa-file-upload", group: "Manual" },
  };

  var QUIZ_TYPE_GROUPS = [
    { label: "Auto-graded", types: ["Multiple Choice", "True/False", "Fill in the Blank", "Matching Type", "Calculated Numeric"] },
    { label: "Manual",      types: ["Essay", "Document"] },
  ];

  var DEFAULT_QUESTION = {
    question_text: "",
    quiz_type: "Multiple Choice",
    score: "",
    correct_answer: "",
    choices: ["", "", "", ""],
    choice_images: [],
    matching_left: [""],
    matching_right: [""],
    extra_right: [],
    rubric_items: [],
  };

  function mergeQuestion(template, data) {
    var out = {};
    Object.keys(template).forEach(function (k) { out[k] = template[k]; });
    if (data) Object.keys(data).forEach(function (k) { out[k] = data[k]; });
    return out;
  }

  /* ================================================================== */
  function QuestionCards(config) {
    this.container       = document.getElementById(config.containerId);
    this.batchUrl        = config.batchUrl;
    this.uploadFileUrl   = config.uploadFileUrl || "";
    this.saveFormId      = config.saveFormId;
    this.csrfToken       = config.csrfToken;
    this.defaultPoints   = config.defaultPoints || "";
    this.subjectId       = config.subjectId;
    this.rubrics         = config.rubrics || [];
    this.cards           = [];
    this.lastType        = config.lastType || "Multiple Choice";
    this.skipRestoreBanner = !!config.skipRestoreBanner;
    this._dragSrc        = null;
    this._autoSaveTimer  = null;

    this._init(config.initialQuestions || []);
  }

  QuestionCards.TYPE_META = QUIZ_TYPE_META;

  QuestionCards.prototype._baselineKey = function () {
    var m = (this.batchUrl || '').match(/\/([^/?#]+)\/?$/);
    var id = (m && m[1]) || 'unknown';
    var userId = (document.body && document.body.dataset && document.body.dataset.currentUserId) || 'anon';
    return 'qc:baseline:' + id + ':' + userId;
  };

  QuestionCards.prototype._loadBaseline = function () {
    try { return JSON.parse(localStorage.getItem(this._baselineKey()) || 'null'); }
    catch (_) { return null; }
  };

  QuestionCards.prototype._saveBaseline = function (items) {
    try { localStorage.setItem(this._baselineKey(), JSON.stringify(items || [])); }
    catch (_) {}
  };

  QuestionCards.prototype._init = function (initial) {
    var self = this;
    this._bindPicker();
    this._bindAddButton();
    this._bindSaveButton();
    this._updateNumbers();
    this._renderEmptyState();
    this._initialized = true;
    window.addEventListener("beforeunload", function () { self._autoSaveNow(); });

    initial = initial || [];
    var baseline = this._loadBaseline();

    // Fresh bulk-import: server told us these items were just imported
    // intentionally — render them all and adopt them as the new baseline,
    // so the autosave "Restore" prompt doesn't appear.
    if (this.skipRestoreBanner) {
      initial.forEach(function (q) { self.addCard(q); });
      this._saveBaseline(initial);
      return;
    }

    if (!baseline) {
      initial.forEach(function (q) { self.addCard(q); });
      this._saveBaseline(initial);
      return;
    }

    var baselineCount = baseline.length;
    initial.slice(0, baselineCount).forEach(function (q) { self.addCard(q); });
    var newItems = initial.slice(baselineCount);
    if (newItems.length > 0) {
      this._showRestoreBanner(newItems, baseline);
    }
  };

  QuestionCards.prototype._showRestoreBanner = function (newQuestions, baseline) {
    var self = this;
    var anchor = this.container;
    if (!anchor || !anchor.parentNode) return;
    if (anchor.parentNode.querySelector('.cl-autosave-banner.qc-restore-banner')) return;

    var count = newQuestions.length;
    var banner = document.createElement('div');
    banner.className = 'cl-autosave-banner qc-restore-banner';
    banner.setAttribute('role', 'status');
    banner.innerHTML =
      '<div class="cl-autosave-banner-text">' +
        '<i class="fas fa-clock-rotate-left" aria-hidden="true"></i>' +
        '<span><strong>We saved your progress!</strong> Pick up where you left off?' +
          ' <span class="cl-autosave-banner-time">' + count + ' unsaved ' +
          (count === 1 ? 'question' : 'questions') + '</span></span>' +
      '</div>' +
      '<div class="cl-autosave-banner-actions">' +
        '<button type="button" class="cl-autosave-btn cl-autosave-btn-ghost" data-qc-discard>Discard</button>' +
        '<button type="button" class="cl-autosave-btn cl-autosave-btn-primary" data-qc-restore>Restore</button>' +
      '</div>';

    anchor.parentNode.insertBefore(banner, anchor);

    function dismiss() {
      banner.classList.add('is-dismissing');
      setTimeout(function () { if (banner.parentNode) banner.parentNode.removeChild(banner); }, 220);
    }

    banner.querySelector('[data-qc-restore]').addEventListener('click', function () {
      newQuestions.forEach(function (q) { self.addCard(q); });
      self._saveBaseline(self.serialize());
      dismiss();
    });

    banner.querySelector('[data-qc-discard]').addEventListener('click', function () {
      fetch(self.batchUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": self.csrfToken },
        body: JSON.stringify(baseline || []),
        keepalive: true,
      }).catch(function () {});
      document.body.setAttribute('data-fetch-dirty', 'false');
      dismiss();
    });
  };

  /* ------------------------- Auto-save ------------------------- */
  QuestionCards.prototype._scheduleAutoSave = function () {
    var self = this;
    if (this._initialized) document.body.setAttribute('data-fetch-dirty', 'true');
    if (this._autoSaveTimer) clearTimeout(this._autoSaveTimer);
    this._autoSaveTimer = setTimeout(function () { self._autoSaveNow(); }, 1500);
  };

  QuestionCards.prototype._autoSaveNow = function () {
    var questions = this.serialize();
    fetch(this.batchUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": this.csrfToken },
      body: JSON.stringify(questions),
      keepalive: true,
    }).catch(function () {});
  };

  /* ------------------------- Bindings ------------------------- */
  QuestionCards.prototype._bindPicker = function () {
    var self = this;
    document.querySelectorAll("[data-add-type]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var type = btn.getAttribute("data-add-type");
        if (!type) return;
        self.lastType = type;
        self.addCard({ quiz_type: type });
        self._scrollToLast();
      });
    });
  };

  QuestionCards.prototype._bindAddButton = function () {
    var self = this;
    var btn = document.getElementById("add-question-btn");
    if (btn) {
      btn.addEventListener("click", function () {
        self.addCard(null);
        self._scrollToLast();
      });
    }
    document.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        self.addCard(null);
        self._scrollToLast();
      }
    });
  };

  QuestionCards.prototype._clearValidationErrors = function () {
    var root = this.container;
    if (!root) return;
    Array.from(root.querySelectorAll('.is-invalid')).forEach(function (el) {
      el.classList.remove('is-invalid');
    });
    Array.from(root.querySelectorAll('.qc-card-error')).forEach(function (el) {
      el.parentNode && el.parentNode.removeChild(el);
    });
    Array.from(root.querySelectorAll('.qc-card-invalid')).forEach(function (el) {
      el.classList.remove('qc-card-invalid');
      el.style.border = '';
      el.style.boxShadow = '';
    });
    var emptyState = root.querySelector('.qc-empty');
    if (emptyState) emptyState.classList.remove('qc-empty-invalid');
  };

  QuestionCards.prototype._setCardError = function (card, messages) {
    if (!card) return;
    var msgs = Array.isArray(messages) ? messages : [messages];
    if (!msgs.length) return;
    var existing = card.querySelector('.qc-card-error');
    if (existing) existing.parentNode.removeChild(existing);

    var box = document.createElement('div');
    box.className = 'qc-card-error';
    box.setAttribute('role', 'alert');
    box.style.cssText = 'display:flex;align-items:flex-start;gap:10px;margin:14px 14px 0;padding:12px 16px;border-radius:10px;background:rgba(231,76,60,0.14);border:1.5px solid #e74c3c;color:#b3261e;font-size:14px;font-weight:700;line-height:1.45;';
    var icon = document.createElement('i');
    icon.className = 'fas fa-circle-exclamation';
    icon.setAttribute('aria-hidden', 'true');
    icon.style.cssText = 'font-size:17px;color:#e74c3c;flex:0 0 auto;margin-top:2px;';
    box.appendChild(icon);

    if (msgs.length === 1) {
      var span = document.createElement('span');
      span.textContent = msgs[0];
      box.appendChild(span);
    } else {
      var ul = document.createElement('ul');
      ul.style.cssText = 'list-style:disc;padding-left:18px;margin:0;';
      msgs.forEach(function (m) {
        var li = document.createElement('li');
        li.style.cssText = 'margin:2px 0;';
        li.textContent = m;
        ul.appendChild(li);
      });
      box.appendChild(ul);
    }

    card.insertBefore(box, card.firstChild);
    card.classList.add('qc-card-invalid');
    card.style.border = '2px solid #e74c3c';
    card.style.boxShadow = '0 0 0 4px rgba(231, 76, 60, 0.18)';
  };

  QuestionCards.prototype._clearCardError = function (card) {
    if (!card || !card.classList.contains('qc-card-invalid')) return;
    var err = card.querySelector('.qc-card-error');
    if (err && err.parentNode) err.parentNode.removeChild(err);
    card.classList.remove('qc-card-invalid');
    card.style.border = '';
    card.style.boxShadow = '';
    Array.from(card.querySelectorAll('.is-invalid')).forEach(function (el) {
      el.classList.remove('is-invalid');
    });
  };

  QuestionCards.prototype._bindSaveButton = function () {
    var self = this;
    var form = document.getElementById(this.saveFormId);
    if (!form) return;
    form.addEventListener("submit", function (e) {
      self._clearValidationErrors();
      var questions = self.serialize();

      if (questions.length === 0) {
        e.preventDefault();
        e.stopImmediatePropagation();
        var emptyState = self.container.querySelector('.qc-empty');
        if (emptyState) {
          emptyState.classList.add('qc-empty-invalid');
          emptyState.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        return;
      }

      var issuesByCard = {};
      function addIssue(idx, msg) {
        if (!issuesByCard[idx]) issuesByCard[idx] = [];
        issuesByCard[idx].push(msg);
      }

      self.cards.forEach(function (card, idx) {
        var inp = card.querySelector('.points-input');
        if (!inp) return;
        var val = parseFloat(inp.value);
        var bad = !inp.value || isNaN(val) || val <= 0;
        if (bad) {
          inp.classList.add('is-invalid');
          addIssue(idx, 'Needs a point value greater than 0.');
        } else {
          inp.classList.remove('is-invalid');
        }
      });

      var typesNeedingQuestion = ['Multiple Choice', 'True/False', 'Fill in the Blank', 'Calculated Numeric', 'Essay'];
      for (var qi = 0; qi < questions.length; qi++) {
        var q = questions[qi];
        var card = self.cards[qi];

        if (typesNeedingQuestion.indexOf(q.quiz_type) !== -1) {
          if (!q.question_text || !String(q.question_text).trim()) {
            addIssue(qi, 'Enter the question text.');
            if (card) {
              var qInput = card.querySelector('.question-text');
              if (qInput) qInput.classList.add('is-invalid');
            }
          }
        }

        switch (q.quiz_type) {
          case "Multiple Choice":
            var nonEmptyChoices = (q.choices || []).filter(function (c, i) {
              return (c && String(c).trim()) || (q.choice_images && q.choice_images[i]);
            });
            if (nonEmptyChoices.length < 2) {
              addIssue(qi, 'Fill in at least two answer choices.');
              if (card) {
                card.querySelectorAll('.choice-text').forEach(function (inp) {
                  if (!inp.value || !inp.value.trim()) inp.classList.add('is-invalid');
                });
              }
            } else if (q.correct_answer === "" || q.correct_answer === null || q.correct_answer === undefined) {
              addIssue(qi, 'Pick the correct option.');
            }
            break;
          case "True/False":
            if (!q.correct_answer || (q.correct_answer !== "True" && q.correct_answer !== "False")) {
              addIssue(qi, 'Select True or False as the correct answer.');
            }
            break;
          case "Fill in the Blank":
            if (!q.correct_answer || !String(q.correct_answer).trim()) {
              addIssue(qi, 'Enter the correct answer.');
              if (card) {
                var fitb = card.querySelector('.fitb-answer');
                if (fitb) fitb.classList.add('is-invalid');
              }
            }
            break;
          case "Calculated Numeric":
            if (!q.correct_answer || !String(q.correct_answer).trim()) {
              addIssue(qi, 'Enter the correct answer.');
              if (card) {
                var calc = card.querySelector('.calc-answer');
                if (calc) calc.classList.add('is-invalid');
              }
            }
            break;
          case "Matching Type":
            var pairs = (q.matching_left || []).filter(function (l, i) {
              return l && String(l).trim() &&
                     q.matching_right && q.matching_right[i] && String(q.matching_right[i]).trim();
            });
            if (pairs.length < 1) {
              addIssue(qi, 'Add at least one complete left/right pair.');
              if (card) {
                card.querySelectorAll('.matching-left, .matching-right').forEach(function (inp) {
                  if (!inp.value || !inp.value.trim()) inp.classList.add('is-invalid');
                });
              }
            }
            break;
        }
      }

      var firstBadCard = null;
      Object.keys(issuesByCard).forEach(function (idxStr) {
        var card = self.cards[parseInt(idxStr, 10)];
        if (card) {
          self._setCardError(card, issuesByCard[idxStr]);
          if (!firstBadCard) firstBadCard = card;
        }
      });

      if (firstBadCard) {
        e.preventDefault();
        e.stopImmediatePropagation();
        firstBadCard.scrollIntoView({ behavior: "smooth", block: "center" });
        var focusTarget = firstBadCard.querySelector('.is-invalid') ||
                          firstBadCard.querySelector('input, select, textarea');
        if (focusTarget) focusTarget.focus();
        return;
      }
      e.preventDefault();
      var saveBtn = form.querySelector("button[type=submit]");
      if (!self._saveBtnHTML && saveBtn) self._saveBtnHTML = saveBtn.innerHTML;

      function doSave() {
        if (saveBtn) {
          saveBtn.disabled = true;
          saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving…';
        }
        fetch(self.batchUrl + "?save_final=1", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": self.csrfToken },
          body: JSON.stringify(questions),
        })
          .then(function (r) { return r.json().then(function (d) { return { status: r.status, data: d }; }); })
          .then(function (res) {
            if (res.status === 200 && res.data.ok) {
              document.body.setAttribute('data-fetch-dirty', 'false');
              self._saveBaseline(questions);
              if (window.ClFormGuard && window.ClFormGuard.suppressNext) window.ClFormGuard.suppressNext();
              form.dataset._qcConfirmed = "1";
              form.submit();
            } else {
              if (window.clToast) clToast(res.data.error || "Cannot save questions.", "error");
              if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.innerHTML = self._saveBtnHTML || 'Save';
              }
            }
          })
          .catch(function () {
            if (window.clToast) clToast("Network error while saving.", "error");
            if (saveBtn) {
              saveBtn.disabled = false;
              saveBtn.innerHTML = self._saveBtnHTML || 'Save';
            }
          });
      }

      if (typeof Swal !== "undefined") {
        Swal.fire({
          title: "Save all questions?",
          text: "This will assign the assessment to enrolled students.",
          icon: "question",
          showCancelButton: true,
          confirmButtonColor: (getComputedStyle(document.documentElement)
            .getPropertyValue('--brand-primary') || '').trim() || "#1B4332",
          cancelButtonColor: "#C08479",
          reverseButtons: true,
          confirmButtonText: "Yes, save",
        }).then(function (result) { if (result.isConfirmed) doSave(); });
      } else {
        doSave();
      }
    });
  };

  /* ------------------------- Empty state ------------------------- */
  QuestionCards.prototype._renderEmptyState = function () {
    var existing = this.container.querySelector(".qc-empty");
    if (this.cards.length === 0) {
      if (!existing) {
        var empty = document.createElement("div");
        empty.className = "qc-empty";
        empty.innerHTML =
          '<div><i class="far fa-question-circle"></i></div>' +
          '<div class="qc-empty-title">No questions yet</div>' +
          '<div>Pick a type above or click <strong>Add Question</strong> to start.</div>';
        this.container.appendChild(empty);
      }
    } else if (existing) {
      existing.remove();
    }
  };

  /* ================================================================ */
  /*                          Card creation                           */
  /* ================================================================ */
  QuestionCards.prototype.addCard = function (data) {
    var self = this;
    var q = mergeQuestion(
      Object.assign({}, DEFAULT_QUESTION, { quiz_type: this.lastType, score: this.defaultPoints }),
      data
    );

    // Use Bootstrap's .card as the primary container; keep .question-card and
    // .qc-card as legacy hooks for existing CSS and serialization.
    var card = document.createElement("article");
    card.className = "card shadow-sm mb-3 qc-card question-card";
    card.dataset.index = this.cards.length;
    card.setAttribute("role", "group");

    card.appendChild(this._buildHeader(card, q));
    card.appendChild(this._buildBody(card, q));
    card.appendChild(this._buildFooter(card, q));

    var empty = this.container.querySelector(".qc-empty");
    if (empty) empty.remove();

    this.container.appendChild(card);
    this.cards.push(card);

    this._setupDragDrop(card);

    function clearFieldError(e) {
      var t = e && e.target;
      if (t && t.classList && t.classList.contains('is-invalid')) {
        t.classList.remove('is-invalid');
      }
      self._scheduleAutoSave();
    }
    card.addEventListener("input",  clearFieldError);
    card.addEventListener("change", clearFieldError);

    this._rebuildTypeFields(card, q.quiz_type, q);
    this._updateNumbers();
    this._scheduleAutoSave();
  };

  /* --------------------------- Header --------------------------- */
  QuestionCards.prototype._buildHeader = function (card, q) {
    var self = this;
    var header = document.createElement("header");
    header.className = "card-header bg-body-tertiary d-flex align-items-center gap-2 py-2";

    // Drag handle
    var grip = document.createElement("span");
    grip.className = "qc-grip";
    grip.setAttribute("aria-label", "Drag to reorder");
    grip.setAttribute("title", "Drag to reorder");
    grip.innerHTML = '<i class="fas fa-grip-vertical"></i>';
    grip.addEventListener("mousedown",  function () { card.draggable = true; });
    grip.addEventListener("touchstart", function () { card.draggable = true; }, { passive: true });
    document.addEventListener("mouseup",  function () { card.draggable = false; });
    document.addEventListener("touchend", function () { card.draggable = false; });

    // Q number badge
    var num = document.createElement("span");
    num.className = "qc-num q-number";
    num.textContent = "Q" + (this.cards.length + 1);

    // Type select — plain BS5 form-select with optgroups
    var typeWrap = document.createElement("span");
    typeWrap.className = "qc-type-wrap";

    var typeSelect = document.createElement("select");
    typeSelect.className = "form-select form-select-sm qc-type-select";
    typeSelect.setAttribute("aria-label", "Question type");
    typeSelect.style.width = "220px";
    QUIZ_TYPE_GROUPS.forEach(function (group) {
      var optgroup = document.createElement("optgroup");
      optgroup.label = group.label;
      group.types.forEach(function (t) {
        var opt = document.createElement("option");
        opt.value = t;
        opt.textContent = t;
        if (t === q.quiz_type) opt.selected = true;
        optgroup.appendChild(opt);
      });
      typeSelect.appendChild(optgroup);
    });
    typeSelect.addEventListener("change", function () {
      var newType = typeSelect.value;
      self.lastType = newType;
      self._rebuildTypeFields(card, newType, {});
    });
    typeWrap.appendChild(typeSelect);

    var actions = document.createElement("span");
    actions.className = "ms-auto d-inline-flex gap-1";

    var dupBtn = document.createElement("button");
    dupBtn.type = "button";
    dupBtn.className = "btn btn-sm btn-outline-secondary px-2";
    dupBtn.title = "Duplicate question";
    dupBtn.setAttribute("aria-label", "Duplicate question");
    dupBtn.innerHTML = '<i class="fas fa-copy"></i>';
    dupBtn.addEventListener("click", function () {
      var clone = self._serializeCard(card);
      self.addCard(clone);
      self._scrollToLast();
    });

    var delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "btn btn-sm btn-outline-danger px-2";
    delBtn.title = "Delete question";
    delBtn.setAttribute("aria-label", "Delete question");
    delBtn.innerHTML = '<i class="fas fa-trash"></i>';
    delBtn.addEventListener("click", function () {
      if (!confirm("Delete this question?")) return;
      var i = self.cards.indexOf(card);
      if (i > -1) self.cards.splice(i, 1);
      card.remove();
      self._updateNumbers();
      self._renderEmptyState();
      self._scheduleAutoSave();
      if (window.clToast) clToast("Question removed.", "info", 2500);
    });

    actions.appendChild(dupBtn);
    actions.appendChild(delBtn);

    // Points input lives next to the type select for tighter UI.
    var pointsWrap = document.createElement("div");
    pointsWrap.className = "d-inline-flex align-items-center gap-2 qc-points-wrap";
    var pointsInput = document.createElement("input");
    pointsInput.type = "number";
    pointsInput.className = "form-control form-control-sm points-input";
    pointsInput.style.width = "78px";
    pointsInput.placeholder = "Pts";
    pointsInput.min = "0.5";
    pointsInput.step = "0.5";
    pointsInput.required = true;
    pointsInput.title = "Required — must be greater than 0";
    pointsInput.value = (q.score != null && q.score !== "") ? q.score : "";
    pointsInput.setAttribute("aria-label", "Points");
    pointsInput.addEventListener("input", function () {
      var val = parseFloat(pointsInput.value);
      pointsInput.classList.toggle("is-invalid", !pointsInput.value || isNaN(val) || val <= 0);
      self._updateNumbers();
      self._scheduleAutoSave();
    });
    var ptsSuffix = document.createElement("span");
    ptsSuffix.className = "small text-600";
    ptsSuffix.textContent = "pts";
    pointsWrap.appendChild(pointsInput);
    pointsWrap.appendChild(ptsSuffix);

    header.appendChild(grip);
    header.appendChild(num);
    header.appendChild(typeWrap);
    header.appendChild(pointsWrap);
    header.appendChild(actions);
    return header;
  };

  /* ---------------------------- Body ---------------------------- */
  QuestionCards.prototype._buildBody = function (card, q) {
    var self = this;
    var body = document.createElement("div");
    body.className = "card-body";

    var isEssayDoc = q.quiz_type === "Essay" || q.quiz_type === "Document";
    var textLabel  = isEssayDoc ? "Instruction" : "Question";

    // Question / Instruction textarea
    var qaRow = document.createElement("div");
    qaRow.className = "mb-3";

    var qaLabel = document.createElement("label");
    qaLabel.className = "form-label small fw-semibold text-uppercase text-600 qa-label";
    qaLabel.textContent = textLabel;

    var textarea = document.createElement("textarea");
    textarea.className = "form-control question-text";
    textarea.placeholder = textLabel + " text...";
    textarea.rows = 2;
    textarea.value = q.question_text || "";

    qaRow.appendChild(qaLabel);
    qaRow.appendChild(textarea);
    body.appendChild(qaRow);

    // Instruction file (Essay / Document only)
    var instrRow = document.createElement("div");
    instrRow.className = "mb-3 instr-file-row";

    var instrLabel = document.createElement("label");
    instrLabel.className = "form-label small fw-semibold text-uppercase text-600 instr-file-label";
    instrLabel.textContent = "Instruction File (optional)";

    var existingInstrPath = q.question_instruction || "";

    var instrFileInput = document.createElement("input");
    instrFileInput.type = "file";
    instrFileInput.className = "form-control form-control-sm instr-file-input";
    instrFileInput.accept = ".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.png,.jpg,.jpeg";

    var instrFileStatus = document.createElement("div");
    instrFileStatus.className = "small text-600 mt-1 instr-file-status";
    if (existingInstrPath) {
      instrFileStatus.textContent = existingInstrPath.split("/").pop();
      instrRow.dataset.instrPath = existingInstrPath;
    }

    instrFileInput.addEventListener("change", function () {
      if (!instrFileInput.files.length) return;
      var fd = new FormData();
      fd.append("file", instrFileInput.files[0]);
      instrFileStatus.textContent = "Uploading...";
      instrFileStatus.className = "small text-600 mt-1 instr-file-status";
      fetch(self.uploadFileUrl, {
        method: "POST",
        headers: { "X-CSRFToken": self.csrfToken },
        body: fd,
      })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d.ok) {
            instrRow.dataset.instrPath = d.path;
            instrFileStatus.innerHTML = '<i class="fas fa-check-circle text-success me-1"></i>' + instrFileInput.files[0].name;
            instrFileStatus.className = "small text-success mt-1 instr-file-status";
            self._scheduleAutoSave();
          } else {
            instrFileStatus.innerHTML = '<i class="fas fa-times-circle me-1"></i>Upload failed: ' + (d.error || "unknown error");
            instrFileStatus.className = "small text-danger mt-1 instr-file-status";
          }
        })
        .catch(function () {
          instrFileStatus.innerHTML = '<i class="fas fa-times-circle me-1"></i>Upload failed (network error)';
          instrFileStatus.className = "small text-danger mt-1 instr-file-status";
        });
    });

    instrRow.appendChild(instrLabel);
    instrRow.appendChild(instrFileInput);
    instrRow.appendChild(instrFileStatus);
    if (!isEssayDoc) instrRow.style.display = "none";
    body.appendChild(instrRow);

    // Type-specific fields container
    var typeFields = document.createElement("div");
    typeFields.className = "type-fields";
    body.appendChild(typeFields);

    return body;
  };

  /* --------------------------- Footer --------------------------- */
  QuestionCards.prototype._buildFooter = function (card, q) {
    var footer = document.createElement("footer");
    footer.className = "card-footer bg-body-tertiary d-flex align-items-center gap-3 py-2";

    var note = document.createElement("span");
    note.className = "ms-auto small text-600 qc-type-note";
    note.innerHTML = '<i class="fas fa-info-circle me-1"></i><span class="qc-type-note-text"></span>';

    footer.appendChild(note);
    return footer;
  };

  /* ------------------------ Drag & Drop ------------------------ */
  QuestionCards.prototype._setupDragDrop = function (card) {
    var self = this;

    card.addEventListener("dragstart", function (e) {
      self._dragSrc = card;
      card.classList.add("qc-dragging");
      try { e.dataTransfer.setData("text/plain", card.dataset.index); } catch (err) {}
      e.dataTransfer.effectAllowed = "move";
    });

    card.addEventListener("dragend", function () {
      card.classList.remove("qc-dragging");
      card.draggable = false;
      self._clearDropMarkers();
      self._dragSrc = null;
    });

    card.addEventListener("dragover", function (e) {
      if (!self._dragSrc || self._dragSrc === card) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      var rect = card.getBoundingClientRect();
      var before = e.clientY < rect.top + rect.height / 2;
      self._clearDropMarkers();
      card.classList.add(before ? "qc-drop-before" : "qc-drop-after");
    });

    card.addEventListener("dragleave", function () {
      card.classList.remove("qc-drop-before", "qc-drop-after");
    });

    card.addEventListener("drop", function (e) {
      if (!self._dragSrc || self._dragSrc === card) return;
      e.preventDefault();
      var rect = card.getBoundingClientRect();
      var before = e.clientY < rect.top + rect.height / 2;
      self.container.insertBefore(self._dragSrc, before ? card : card.nextSibling);
      self._clearDropMarkers();
      self._reorderFromDom();
    });
  };

  QuestionCards.prototype._clearDropMarkers = function () {
    this.container.querySelectorAll(".qc-drop-before, .qc-drop-after").forEach(function (el) {
      el.classList.remove("qc-drop-before", "qc-drop-after");
    });
  };

  QuestionCards.prototype._reorderFromDom = function () {
    var list = [];
    this.container.querySelectorAll(".qc-card").forEach(function (c) { list.push(c); });
    this.cards = list;
    this._updateNumbers();
    this._scheduleAutoSave();
  };

  /* =================================================================
     Type-specific field builders
     ================================================================= */
  QuestionCards.prototype._rebuildTypeFields = function (card, type, data) {
    var container = card.querySelector(".type-fields");
    container.innerHTML = "";
    var textarea = card.querySelector(".question-text");
    var qaLabel  = card.querySelector(".qa-label");
    var isEssayDoc = type === "Essay" || type === "Document";
    var labelText = isEssayDoc ? "Instruction" : "Question";
    if (textarea) textarea.placeholder = labelText + " text...";
    if (qaLabel)  qaLabel.textContent  = labelText;

    var instrRow = card.querySelector(".instr-file-row");
    if (instrRow) instrRow.style.display = isEssayDoc ? "" : "none";

    var noteText = card.querySelector(".qc-type-note-text");
    if (noteText) {
      noteText.textContent = (QUIZ_TYPE_META[type] && QUIZ_TYPE_META[type].group)
        ? QUIZ_TYPE_META[type].group + " · " + type
        : type;
    }

    switch (type) {
      case "Multiple Choice":    this._buildMC(container, data); break;
      case "True/False":         this._buildTF(container, data); break;
      case "Fill in the Blank":  this._buildFITB(container, data); break;
      case "Matching Type":      this._buildMatching(container, data); break;
      case "Calculated Numeric": this._buildCalcNumeric(container, data); break;
      case "Essay":              this._buildEssay(container, data); break;
      case "Document":           this._buildDocument(container, data); break;
    }
  };

  function makeLabel(text) {
    var label = document.createElement("label");
    label.className = "form-label small fw-semibold text-uppercase text-600 d-block mb-2";
    label.textContent = text;
    return label;
  }

  function iconBtn(klass, title, icon) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = klass;
    b.title = title;
    b.setAttribute("aria-label", title);
    b.innerHTML = '<i class="' + icon + '"></i>';
    return b;
  }

  function addLink(text) {
    var a = document.createElement("a");
    a.href = "#";
    a.className = "link-primary small text-decoration-none d-inline-flex align-items-center gap-1 mt-1";
    a.innerHTML = '<i class="fas fa-plus-circle"></i> ' + text;
    return a;
  }

  /* --------------------------- MC --------------------------- */
  QuestionCards.prototype._buildMC = function (container, data) {
    var self = this;
    var choices      = data.choices && data.choices.length ? data.choices : ["", "", "", ""];
    var choiceImages = data.choice_images || [];
    var correctIdx   = parseInt(data.correct_answer, 10);
    if (isNaN(correctIdx)) correctIdx = -1;

    container.appendChild(makeLabel("Options — select the correct answer"));

    var wrapper = document.createElement("div");
    wrapper.className = "mc-choices";

    function refreshCorrectStates() {
      wrapper.querySelectorAll(".qc-choice").forEach(function (r) {
        var radio = r.querySelector('input[type="radio"]');
        r.classList.toggle("is-correct", !!(radio && radio.checked));
      });
    }

    function addChoiceRow(text, idx, isCorrect, existingImgPath) {
      var row = document.createElement("div");
      row.className = "qc-choice choice-row";
      if (existingImgPath) row.dataset.imgPath = existingImgPath;

      var radio = document.createElement("input");
      radio.type = "radio";
      radio.name = "mc_correct_" + container.closest(".question-card").dataset.index;
      radio.className = "qc-choice-radio";
      radio.checked = isCorrect;
      radio.setAttribute("aria-label", "Mark option " + (idx + 1) + " as correct");
      radio.addEventListener("change", refreshCorrectStates);

      var input = document.createElement("input");
      input.type = "text";
      input.className = "qc-choice-text choice-text";
      input.placeholder = "Option " + (idx + 1) + " (text or image)";
      input.value = text || "";

      var fileInput = document.createElement("input");
      fileInput.type = "file";
      fileInput.accept = "image/*";
      fileInput.className = "form-control form-control-sm qc-choice-file choice-img-input";
      fileInput.title = "Choice image (optional)";

      var imgThumb = document.createElement("img");
      imgThumb.className = "qc-choice-thumb";
      imgThumb.alt = "";
      imgThumb.style.display = existingImgPath ? "" : "none";
      if (existingImgPath) imgThumb.src = "/media/" + existingImgPath;

      fileInput.addEventListener("change", function () {
        if (!fileInput.files.length) return;
        var fd = new FormData();
        fd.append("file", fileInput.files[0]);
        fetch(self.uploadFileUrl, {
          method: "POST",
          headers: { "X-CSRFToken": self.csrfToken },
          body: fd,
        })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (d.ok) {
              row.dataset.imgPath = d.path;
              imgThumb.src = "/media/" + d.path;
              imgThumb.style.display = "";
              self._scheduleAutoSave();
            }
          });
      });

      var flag = document.createElement("span");
      flag.className = "qc-correct-flag";
      flag.innerHTML = '<i class="fas fa-check"></i> Correct';

      var removeBtn = iconBtn("btn btn-sm btn-outline-danger px-2", "Remove option", "fas fa-times");
      removeBtn.addEventListener("click", function () {
        row.remove();
        refreshCorrectStates();
      });

      row.appendChild(radio);
      row.appendChild(input);
      row.appendChild(fileInput);
      row.appendChild(imgThumb);
      row.appendChild(flag);
      row.appendChild(removeBtn);
      wrapper.appendChild(row);
    }

    choices.forEach(function (c, i) {
      addChoiceRow(c, i, i === correctIdx, choiceImages[i] || null);
    });
    refreshCorrectStates();

    var link = addLink("Add option");
    link.addEventListener("click", function (e) {
      e.preventDefault();
      addChoiceRow("", wrapper.querySelectorAll(".qc-choice").length, false, null);
    });

    container.appendChild(wrapper);
    container.appendChild(link);
  };

  /* --------------------------- TF --------------------------- */
  QuestionCards.prototype._buildTF = function (container, data) {
    var correct = data.correct_answer || "True";

    container.appendChild(makeLabel("Correct answer"));

    var group = document.createElement("div");
    group.className = "qc-tf tf-toggle";

    function refreshStates() {
      group.querySelectorAll(".qc-tf-opt").forEach(function (l) {
        var r = l.querySelector('input[type="radio"]');
        l.classList.toggle("is-correct", !!(r && r.checked));
      });
    }

    [
      { val: "True",  icon: "fas fa-check-circle" },
      { val: "False", icon: "fas fa-times-circle" },
    ].forEach(function (opt) {
      var lbl = document.createElement("label");
      lbl.className = "qc-tf-opt";

      var radio = document.createElement("input");
      radio.type = "radio";
      radio.name = "tf_correct_" + container.closest(".question-card").dataset.index;
      radio.value = opt.val;
      radio.checked = correct === opt.val;
      radio.addEventListener("change", refreshStates);

      var icon = document.createElement("i");
      icon.className = opt.icon + " qc-tf-icon";

      var span = document.createElement("span");
      span.textContent = opt.val;

      lbl.appendChild(radio);
      lbl.appendChild(icon);
      lbl.appendChild(span);
      group.appendChild(lbl);
    });

    container.appendChild(group);
    refreshStates();
  };

  /* --------------------------- FITB --------------------------- */
  QuestionCards.prototype._buildFITB = function (container, data) {
    container.appendChild(makeLabel("Correct answer"));
    var input = document.createElement("input");
    input.type = "text";
    input.className = "form-control fitb-answer";
    input.placeholder = "Expected answer (case-insensitive match)";
    input.value = data.correct_answer || "";
    container.appendChild(input);
  };

  /* ------------------------ Matching ------------------------ */
  QuestionCards.prototype._buildMatching = function (container, data) {
    var lefts  = data.matching_left  && data.matching_left.length  ? data.matching_left  : [""];
    var rights = data.matching_right && data.matching_right.length ? data.matching_right : [""];
    var extras = data.extra_right || [];

    container.appendChild(makeLabel("Matching pairs"));

    var pairsDiv = document.createElement("div");
    pairsDiv.className = "matching-pairs";

    function addPair(left, right) {
      var row = document.createElement("div");
      row.className = "qc-pair-row matching-pair-row";

      var li = document.createElement("input");
      li.type = "text";
      li.className = "form-control form-control-sm matching-left";
      li.placeholder = "Left side";
      li.value = left || "";
      li.style.flex = "1 1 160px";

      var arrow = document.createElement("span");
      arrow.className = "qc-arrow";
      arrow.innerHTML = '<i class="fas fa-arrow-right"></i>';

      var ri = document.createElement("input");
      ri.type = "text";
      ri.className = "form-control form-control-sm matching-right";
      ri.placeholder = "Right side";
      ri.value = right || "";
      ri.style.flex = "1 1 160px";

      var del = iconBtn("btn btn-sm btn-outline-danger px-2", "Remove pair", "fas fa-times");
      del.addEventListener("click", function () {
        if (pairsDiv.querySelectorAll(".matching-pair-row").length > 1) row.remove();
      });

      row.appendChild(li);
      row.appendChild(arrow);
      row.appendChild(ri);
      row.appendChild(del);
      pairsDiv.appendChild(row);
    }

    var maxLen = Math.max(lefts.length, rights.length);
    for (var i = 0; i < maxLen; i++) addPair(lefts[i] || "", rights[i] || "");

    var pairLink = addLink("Add pair");
    pairLink.addEventListener("click", function (e) { e.preventDefault(); addPair("", ""); });

    container.appendChild(pairsDiv);
    container.appendChild(pairLink);

    // Distractors
    var distLabel = makeLabel("Distractors (extra right-side options)");
    distLabel.classList.add("mt-3");
    container.appendChild(distLabel);

    var distDiv = document.createElement("div");
    distDiv.className = "matching-distractors";

    function addDistractor(val) {
      var row = document.createElement("div");
      row.className = "qc-distractor-row distractor-row";

      var inp = document.createElement("input");
      inp.type = "text";
      inp.className = "form-control form-control-sm extra-right";
      inp.placeholder = "Distractor";
      inp.value = val || "";
      inp.style.flex = "1 1 200px";

      var del = iconBtn("btn btn-sm btn-outline-danger px-2", "Remove distractor", "fas fa-times");
      del.addEventListener("click", function () { row.remove(); });

      row.appendChild(inp);
      row.appendChild(del);
      distDiv.appendChild(row);
    }
    extras.forEach(function (v) { addDistractor(v); });

    var distLink = addLink("Add distractor");
    distLink.addEventListener("click", function (e) { e.preventDefault(); addDistractor(""); });

    container.appendChild(distDiv);
    container.appendChild(distLink);
  };

  /* -------------------- Calculated Numeric -------------------- */
  QuestionCards.prototype._buildCalcNumeric = function (container, data) {
    container.appendChild(makeLabel("Correct numeric answer (supports LaTeX)"));

    var input = document.createElement("input");
    input.type = "text";
    input.className = "form-control calc-answer";
    input.placeholder = "e.g. \\frac{1}{2} or 3.14";
    input.value = data.correct_answer || "";

    var preview = document.createElement("div");
    preview.className = "small text-600 mt-2 calc-preview";
    preview.innerHTML = '<i class="fas fa-eye me-1"></i>Preview: <span class="mathjax-out"></span>';

    input.addEventListener("input", function () {
      var out = preview.querySelector(".mathjax-out");
      out.textContent = "\\(" + input.value + "\\)";
      if (window.MathJax && MathJax.typesetPromise) {
        MathJax.typesetPromise([out]).catch(function () {});
      }
    });

    container.appendChild(input);
    container.appendChild(preview);
  };

  /* --------------------------- Essay --------------------------- */
  QuestionCards.prototype._buildEssay = function (container, data) {
    var note = document.createElement("div");
    note.className = "alert alert-info small py-2 mb-3";
    note.innerHTML = '<i class="fas fa-info-circle me-1"></i>Essay questions are graded manually using the rubric criteria below.';
    container.appendChild(note);
    this._buildRubricSelector(container, data);
  };

  /* -------------------------- Document -------------------------- */
  QuestionCards.prototype._buildDocument = function (container, data) {
    var note = document.createElement("div");
    note.className = "alert alert-info small py-2 mb-3";
    note.innerHTML = '<i class="fas fa-info-circle me-1"></i>Students upload a file. Graded manually using the rubric criteria below.';
    container.appendChild(note);
    this._buildRubricSelector(container, data);
  };

  /* --------------------- Rubric selector --------------------- */
  QuestionCards.prototype._buildRubricSelector = function (container, data) {
    var self = this;
    var card = container.closest(".question-card");
    var rubrics = this.rubrics;
    var existingItems = (data && data.rubric_items) ? data.rubric_items : [];

    if (rubrics.length === 0) {
      var warn = document.createElement("div");
      warn.className = "alert alert-warning small py-2 mb-0";
      warn.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>No rubric criteria found for this subject. Please create rubrics first.';
      container.appendChild(warn);
      return;
    }

    container.appendChild(makeLabel("Rubric criteria (must total 100%)"));

    var rowsDiv = document.createElement("div");
    rowsDiv.className = "rubric-rows";

    var totalDisplay = document.createElement("div");
    totalDisplay.className = "small mt-2 rubric-total-display";

    function updateTotal() {
      var total = 0;
      rowsDiv.querySelectorAll(".rubric-points-input").forEach(function (inp) {
        total += parseFloat(inp.value) || 0;
      });
      var ok = Math.abs(total - 100) < 0.01;
      totalDisplay.innerHTML =
        '<i class="fas fa-' + (ok ? "check-circle" : "exclamation-circle") + ' me-1"></i>Total: ' + total + "%";
      totalDisplay.classList.toggle("text-success", ok);
      totalDisplay.classList.toggle("text-danger", !ok);
    }

    function addRubricRow(rubricId, point) {
      var row = document.createElement("div");
      row.className = "qc-pair-row rubric-row";

      var sel = document.createElement("select");
      sel.className = "form-select form-select-sm rubric-select";
      var selWrap = document.createElement("div");
      selWrap.style.flex = "1 1 200px";
      selWrap.appendChild(sel);
      rubrics.forEach(function (r) {
        var opt = document.createElement("option");
        opt.value = r.id;
        opt.textContent = r.rubric_name;
        if (String(r.id) === String(rubricId)) opt.selected = true;
        sel.appendChild(opt);
      });

      var pctInput = document.createElement("input");
      pctInput.type = "number";
      pctInput.className = "form-control form-control-sm rubric-points-input";
      pctInput.style.width = "90px";
      pctInput.placeholder = "%";
      pctInput.min = "0";
      pctInput.max = "100";
      pctInput.step = "1";
      pctInput.value = point !== undefined ? point : "";
      pctInput.addEventListener("input", updateTotal);

      var pctLabel = document.createElement("span");
      pctLabel.className = "small text-600";
      pctLabel.textContent = "%";

      var del = iconBtn("btn btn-sm btn-outline-danger px-2", "Remove criterion", "fas fa-times");
      del.addEventListener("click", function () { row.remove(); updateTotal(); });

      row.appendChild(selWrap);
      row.appendChild(pctInput);
      row.appendChild(pctLabel);
      row.appendChild(del);
      rowsDiv.appendChild(row);
      updateTotal();
    }

    container.appendChild(rowsDiv);

    if (existingItems.length > 0) {
      existingItems.forEach(function (item) { addRubricRow(item.rubric_id, item.point); });
    } else {
      addRubricRow("", "");
    }

    var link = addLink("Add rubric criterion");
    link.addEventListener("click", function (e) { e.preventDefault(); addRubricRow("", ""); });

    container.appendChild(link);
    container.appendChild(totalDisplay);
  };

  /* ======================= Serialization ======================= */
  QuestionCards.prototype.serialize = function () {
    var self = this;
    var result = [];
    this.cards.forEach(function (card) { result.push(self._serializeCard(card)); });
    return result;
  };

  QuestionCards.prototype._serializeCard = function (card) {
    var typeSelect          = card.querySelector(".qc-type-select") || card.querySelector(".qc-type-wrap select") || card.querySelector("select");
    var type                = typeSelect.value;
    var questionText        = card.querySelector(".question-text").value;
    var score               = parseFloat(card.querySelector(".points-input").value) || 0;
    var instrRow            = card.querySelector(".instr-file-row");
    var questionInstruction = (instrRow && instrRow.dataset.instrPath) ? instrRow.dataset.instrPath : null;

    var q = {
      question_text:        questionText,
      quiz_type:            type,
      score:                score,
      correct_answer:       "",
      question_instruction: questionInstruction,
      choices:              [],
      choice_images:        [],
      matching_left:        [],
      matching_right:       [],
      extra_right:          [],
      rubric_items:         [],
    };

    switch (type) {
      case "Multiple Choice":
        var rows   = card.querySelectorAll(".choice-row");
        var radios = card.querySelectorAll('.choice-row input[type="radio"]');
        rows.forEach(function (row, i) {
          q.choices.push(row.querySelector(".choice-text").value);
          q.choice_images.push(row.dataset.imgPath || null);
          if (radios[i] && radios[i].checked) q.correct_answer = i;
        });
        break;

      case "True/False":
        var checked = card.querySelector('.tf-toggle input[type="radio"]:checked');
        q.correct_answer = checked ? checked.value : "True";
        break;

      case "Fill in the Blank":
        var ans = card.querySelector(".fitb-answer");
        q.correct_answer = ans ? ans.value : "";
        break;

      case "Matching Type":
        card.querySelectorAll(".matching-pair-row").forEach(function (row) {
          q.matching_left.push(row.querySelector(".matching-left").value);
          q.matching_right.push(row.querySelector(".matching-right").value);
        });
        card.querySelectorAll(".extra-right").forEach(function (inp) {
          q.extra_right.push(inp.value);
        });
        q.correct_answer = q.matching_left.map(function (l, i) {
          return l + " -> " + (q.matching_right[i] || "");
        }).join(", ");
        break;

      case "Calculated Numeric":
        var ca = card.querySelector(".calc-answer");
        q.correct_answer = ca ? ca.value : "";
        break;

      case "Essay":
        card.querySelectorAll(".rubric-row").forEach(function (row) {
          var rubricId = row.querySelector(".rubric-select") ? row.querySelector(".rubric-select").value : "";
          var point    = parseFloat(row.querySelector(".rubric-points-input").value) || 0;
          if (rubricId) q.rubric_items.push({ rubric_id: rubricId, point: point });
        });
        q.correct_answer = "";
        break;

      case "Document":
        var typeFields = card.querySelector(".type-fields");
        q.correct_answer = (typeFields && typeFields.dataset.documentPath) ? typeFields.dataset.documentPath : "";
        card.querySelectorAll(".rubric-row").forEach(function (row) {
          var rubricId = row.querySelector(".rubric-select") ? row.querySelector(".rubric-select").value : "";
          var point    = parseFloat(row.querySelector(".rubric-points-input").value) || 0;
          if (rubricId) q.rubric_items.push({ rubric_id: rubricId, point: point });
        });
        break;
    }
    return q;
  };

  /* =========================== Helpers =========================== */
  QuestionCards.prototype._updateNumbers = function () {
    this.cards.forEach(function (card, i) {
      card.dataset.index = i;
      var badge = card.querySelector(".q-number");
      if (badge) badge.textContent = "Q" + (i + 1);
      card.querySelectorAll('input[type="radio"]').forEach(function (r) {
        r.name = r.name.replace(/_\d+$/, "_" + i);
      });
    });

    var total = 0;
    this.cards.forEach(function (card) {
      total += parseFloat(card.querySelector(".points-input").value) || 0;
    });
    var totalEl = document.getElementById("total-points-display");
    if (totalEl) totalEl.textContent = total;
    var countEl = document.getElementById("question-count-display");
    if (countEl) countEl.textContent = this.cards.length;
  };

  QuestionCards.prototype._scrollToLast = function () {
    var last = this.cards[this.cards.length - 1];
    if (last) last.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  // Expose globally
  window.QuestionCards = QuestionCards;
})();
