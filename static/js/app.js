document.addEventListener("click", (evt) => {
  const bouton = evt.target.closest("[data-nav-toggle]");
  if (bouton) {
    document.querySelector(".nav").classList.toggle("ouvert");
    return;
  }
  if (!evt.target.closest(".nav") && !evt.target.closest("[data-nav-toggle]")) {
    document.querySelector(".nav")?.classList.remove("ouvert");
  }
});

document.addEventListener("change", (evt) => {
  if (evt.target.name === "segment") {
    evt.target.closest("form").dataset.segment = evt.target.value;
  }
  if (evt.target.id === "mesure_reactif") {
    const champ = document.getElementById("reactif");
    if (champ) champ.disabled = !evt.target.checked;
  }
});
