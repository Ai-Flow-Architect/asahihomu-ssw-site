/* あさひほうむ 特定技能サポート — フロント挙動
   依存ライブラリなしのバニラJS。SEO上、本文はHTML側に静的出力済み。 */
(function () {
  "use strict";

  /* ---------- モバイルメニュー ---------- */
  var toggle = document.querySelector(".nav-toggle");
  var menu = document.getElementById("mobile-menu");
  if (toggle && menu) {
    toggle.addEventListener("click", function () {
      var open = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!open));
      menu.classList.toggle("is-open", !open);
    });
    // メニュー内リンク押下で閉じる
    menu.addEventListener("click", function (e) {
      if (e.target.closest("a")) {
        toggle.setAttribute("aria-expanded", "false");
        menu.classList.remove("is-open");
      }
    });
  }

  /* ---------- FAQ アコーディオン ---------- */
  document.querySelectorAll(".faq__q").forEach(function (q) {
    q.addEventListener("click", function () {
      var open = q.getAttribute("aria-expanded") === "true";
      q.setAttribute("aria-expanded", String(!open));
      var a = q.nextElementSibling;
      if (a) a.classList.toggle("is-open", !open);
    });
  });

  /* ---------- 現在ページをナビでハイライト ---------- */
  var path = location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll('[data-nav]').forEach(function (a) {
    var href = a.getAttribute("href");
    if (href === path) a.setAttribute("aria-current", "page");
  });

  /* ---------- お問い合わせフォーム バリデーション ---------- */
  var form = document.getElementById("contact-form");
  if (form) {
    var status = form.querySelector(".form-status");
    var endpoint = form.getAttribute("data-endpoint") || "";

    function setError(field, on) {
      var wrap = field.closest(".field");
      if (wrap) wrap.classList.toggle("is-invalid", on);
    }

    function validEmail(v) {
      return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
    }

    function checkField(el) {
      var v = (el.value || "").trim();
      var bad = !v;
      if (!bad && el.type === "email" && !validEmail(v)) bad = true;
      if (el.type === "checkbox" && !el.checked) bad = true;
      setError(el, bad);
      return !bad;
    }

    function validate() {
      var ok = true;
      form.querySelectorAll("[required]").forEach(function (el) {
        if (!checkField(el)) ok = false;
      });
      return ok;
    }

    // リアルタイム検証: 一度フォーカスを外したら、その後は入力中も即時に判定
    form.querySelectorAll("[required]").forEach(function (el) {
      var ev = (el.type === "checkbox" || el.tagName === "SELECT") ? "change" : "blur";
      el.addEventListener(ev, function () {
        el.dataset.touched = "1";
        checkField(el);
      });
      el.addEventListener("input", function () {
        if (el.dataset.touched) checkField(el);
      });
    });

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (status) { status.className = "form-status"; status.textContent = ""; }

      // ハニーポット: bot が隠しフィールドを埋めたら、成功を装って静かに破棄
      var hp = form.querySelector('input[name="website"]');
      if (hp && hp.value.trim() !== "") {
        if (status) { status.classList.add("is-ok"); status.textContent = "お問い合わせを受け付けました。"; }
        form.reset();
        return;
      }

      if (!validate()) {
        if (status) {
          status.classList.add("is-err");
          status.textContent = "未入力または形式が正しくない項目があります。赤枠の項目をご確認ください。";
        }
        var firstBad = form.querySelector(".is-invalid input, .is-invalid select, .is-invalid textarea");
        if (firstBad) firstBad.focus();
        return;
      }

      var btn = form.querySelector('button[type="submit"]');

      // 送信先が設定されていない場合はモック完了（受注前ビルド）— loading→success の状態遷移も再現
      if (!endpoint) {
        if (btn) { btn.disabled = true; btn.textContent = "確認中…"; }
        if (status) { status.className = "form-status"; status.textContent = ""; }
        setTimeout(function () {
          if (status) {
            status.classList.add("is-ok");
            status.textContent = "【デモ表示】入力内容に問題はありません。本番では送信先を設定後、実際にお問い合わせが送信され、この位置に受付完了メッセージが表示されます。";
          }
          form.reset();
          if (btn) { btn.disabled = false; btn.textContent = "この内容で送信する"; }
        }, 600);
        return;
      }

      if (btn) { btn.disabled = true; btn.textContent = "送信中…"; }

      fetch(endpoint, {
        method: "POST",
        headers: { "Accept": "application/json" },
        body: new FormData(form)
      }).then(function (res) {
        if (res.ok) {
          if (status) { status.classList.add("is-ok"); status.textContent = "お問い合わせを受け付けました。担当者より折り返しご連絡いたします。"; }
          form.reset();
        } else {
          throw new Error("send failed");
        }
      }).catch(function () {
        if (status) { status.classList.add("is-err"); status.textContent = "送信に失敗しました。お手数ですがお電話でもお問い合わせいただけます。"; }
      }).finally(function () {
        if (btn) { btn.disabled = false; btn.textContent = "この内容で送信する"; }
      });
    });
  }

  /* ---------- 会員ページ（モック・受注前デモ） ---------- */
  var login = document.getElementById("member-login");
  if (login) {
    login.addEventListener("submit", function (e) {
      e.preventDefault();
      var note = document.getElementById("member-note");
      if (note) {
        note.classList.add("is-ok");
        note.style.display = "block";
        note.textContent = "【デモ表示】本番では会員認証後、限定資料のダウンロードページに進みます。";
      }
    });
  }

  /* ---------- フッターの年号 ---------- */
  var y = document.getElementById("copyright-year");
  if (y) y.textContent = new Date().getFullYear();
})();
