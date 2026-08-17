let nodes = [];
let filter = "all";

const container = document.getElementById("nodes");
const search = document.getElementById("search");
const count = document.getElementById("count");

fetch("./data/catalog.json")
  .then(res => res.json())
  .then(data => {
    nodes = data;
    render();
  });

function render() {
  const query = search.value.toLowerCase();

  const results = nodes.filter(node => {
    const matchesSearch =
      node.name?.toLowerCase().includes(query) ||
      node.description?.toLowerCase().includes(query);

    const matchesFilter =
      filter === "all" ||
      node.source === filter;

    return matchesSearch && matchesFilter;
  });

  count.textContent = `${results.length.toLocaleString()} nodes`;

  container.innerHTML = results
    .slice(0, 200)
    .map(node => `
      <div class="card">
        <span class="badge">${node.source}</span>

        <h2>${node.name}</h2>

        <p>
          ${node.description || "No description available"}
        </p>

        ${node.version
          ? `<small>Version: ${node.version}</small>`
          : ""}
      </div>
    `)
    .join("");
}

search.addEventListener("input", render);

document.querySelectorAll("[data-filter]").forEach(button => {
  button.addEventListener("click", () => {

    document
      .querySelectorAll("[data-filter]")
      .forEach(b => b.classList.remove("active"));

    button.classList.add("active");

    filter = button.dataset.filter;

    render();
  });
});