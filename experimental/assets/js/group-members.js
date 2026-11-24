(function () {
  "use strict";

  let activeDialog = null;
  let returnFocus = null;

  function focusableElements(dialog) {
    return Array.from(
      dialog.querySelectorAll(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    ).filter((element) => !element.hidden);
  }

  function openDialog(trigger) {
    const dialogId = trigger.getAttribute("aria-controls");
    const dialog = document.getElementById(dialogId);

    if (!dialog) return;

    activeDialog = dialog;
    returnFocus = trigger;
    dialog.hidden = false;
    document.body.classList.add("member-dialog-open");

    const closeButton = dialog.querySelector(".modal-close");
    if (closeButton) closeButton.focus();
  }

  function closeDialog() {
    if (!activeDialog) return;

    activeDialog.hidden = true;
    activeDialog = null;
    document.body.classList.remove("member-dialog-open");

    if (returnFocus) returnFocus.focus();
    returnFocus = null;
  }

  document.addEventListener("click", function (event) {
    const trigger = event.target.closest(".person-trigger");
    if (trigger) {
      openDialog(trigger);
      return;
    }

    if (!activeDialog) return;

    if (event.target.closest(".modal-close") || event.target === activeDialog) {
      closeDialog();
    }
  });

  document.addEventListener("keydown", function (event) {
    if (!activeDialog) return;

    if (event.key === "Escape") {
      event.preventDefault();
      closeDialog();
      return;
    }

    if (event.key !== "Tab") return;

    const focusable = focusableElements(activeDialog);
    if (focusable.length === 0) {
      event.preventDefault();
      return;
    }

    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
}());
