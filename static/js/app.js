document.addEventListener("change", (evt) => {
  if (evt.target.name === "segment") {
    evt.target.closest("form").dataset.segment = evt.target.value;
  }
  if (evt.target.id === "mesure_reactif") {
    const champ = document.getElementById("reactif");
    if (champ) champ.disabled = !evt.target.checked;
  }
});

// Les fragments de graphiques Plotly (fig.to_html) mesurent la largeur de
// leur conteneur au moment du tracé ; si la mise en page n'est pas encore
// stabilisée à cet instant (chargement initial, échange HTMX), le
// graphique peut être dessiné trop large et déborder de sa carte. On
// force un redimensionnement explicite une fois la page (ou le fragment)
// posée.
function redimensionnerGraphiques() {
  document.querySelectorAll(".js-plotly-plot").forEach((el) => {
    if (window.Plotly) window.Plotly.Plots.resize(el);
  });
}
// Appel immédiat : ce script s'exécute en fin de page, le DOM (et Plotly,
// chargé dans <head>) sont déjà disponibles — pas besoin d'attendre "load",
// qui peut s'être déjà déclenché avant que ce fichier ne l'écoute.
redimensionnerGraphiques();
window.addEventListener("load", redimensionnerGraphiques);
window.addEventListener("resize", redimensionnerGraphiques);
document.body.addEventListener("htmx:afterSwap", redimensionnerGraphiques);
