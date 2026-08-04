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
    // .form-status は form の内側に置く前提だが、外に出ても無反応にならないよう保険を掛ける
    // （null のまま進むと送信結果が一切表示されず、ユーザーには「押しても何も起きない」に見える）
    var status = form.querySelector(".form-status")
      || document.querySelector(".form-status");
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
            // 「送信された」と誤解させないこと。入力チェックが通っただけで、実際には何も送信していない。
            status.className = "form-status is-err";
            status.textContent = "【デモ表示】入力内容に問題はありませんでしたが、この画面は準備中のため お問い合わせは送信されていません。お急ぎの場合はお電話でご連絡ください。";
          }
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

  /* ---------- 資料ダウンロード登録（メール登録で即DL・承認制にしない） ----------
     site.json の download.form_endpoint（登録の送信先）と download.guidebook_url（PDF）が
     両方設定されると本番動作＝登録成功→その場でダウンロード導線を表示する。
     どちらかが未設定（PDF現物・フォームサービスの鍵が未着）のうちはモック動作。 */
  var login = document.getElementById("member-login");
  if (login) {
    var dlEndpoint = login.getAttribute("data-endpoint") || "";
    var dlFile = login.getAttribute("data-file") || "";
    var dlLive = Boolean(dlEndpoint && dlFile);
    var dlBtn = login.querySelector('button[type="submit"]');
    if (dlLive && dlBtn) {
      // 本番動作では「登録→即ダウンロード」なので、ボタン文言も実際の動きに合わせる
      dlBtn.textContent = "ガイドブックをダウンロードする";
    }
    login.addEventListener("submit", function (e) {
      e.preventDefault();
      var note = document.getElementById("member-note");

      // 必須項目（メールアドレス・プライバシーポリシー同意）を検証してから進む。
      // 検証せずにモック表示だけ出すと、同意を取らないままPIIを扱う導線になる。
      var bad = false;
      login.querySelectorAll("[required]").forEach(function (el) {
        var v = (el.value || "").trim();
        var ng = el.type === "checkbox" ? !el.checked : !v;
        if (!ng && el.type === "email") {
          ng = !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
        }
        var wrap = el.closest(".field");
        if (wrap) wrap.classList.toggle("is-invalid", ng);
        if (ng) bad = true;
      });
      if (bad) {
        if (note) {
          note.className = "notice is-err";
          note.style.display = "block";
          note.textContent = "未入力または形式が正しくない項目があります。赤枠の項目をご確認ください。";
        }
        var firstBad = login.querySelector(".is-invalid input");
        if (firstBad) firstBad.focus();
        return;
      }
      // 配信基盤が未確定のうちはモック動作。
      // PIIを預かるフォームで「登録できた」と誤解させない。実際には送信も保存もしていない。
      if (!dlLive) {
        if (note) {
          note.className = "notice is-err";
          note.style.display = "block";
          note.textContent = "【デモ表示】この画面は準備中のため、ご登録は受け付けられていません（入力内容は送信も保存もされていません）。公開後にあらためてご登録ください。";
        }
        return;
      }

      // 本番動作: 登録を送信し、成功したらその場でダウンロード導線を表示する（即DL・承認なし）
      if (dlBtn) { dlBtn.disabled = true; dlBtn.textContent = "送信中…"; }
      fetch(dlEndpoint, {
        method: "POST",
        headers: { "Accept": "application/json" },
        body: new FormData(login)
      }).then(function (res) {
        if (!res.ok) throw new Error("register failed");
        var ready = document.getElementById("dl-ready");
        var link = document.getElementById("dl-link");
        if (link) link.setAttribute("href", dlFile);
        if (ready) ready.style.display = "block";
        if (note) {
          note.className = "notice is-ok";
          note.style.display = "block";
          note.textContent = "ご登録ありがとうございます。下のご案内からガイドブックをダウンロードいただけます。";
        }
        if (ready && ready.scrollIntoView) ready.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }).catch(function () {
        if (note) {
          note.className = "notice is-err";
          note.style.display = "block";
          note.textContent = "送信に失敗しました。お手数ですが、時間をおいてもう一度お試しいただくか、お問い合わせフォームからご連絡ください。";
        }
      }).finally(function () {
        if (dlBtn) { dlBtn.disabled = false; dlBtn.textContent = "ガイドブックをダウンロードする"; }
      });
    });
  }

  /* ---------- フッターの年号 ---------- */
  var y = document.getElementById("copyright-year");
  if (y) y.textContent = new Date().getFullYear();
})();
