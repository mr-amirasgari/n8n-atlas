let nodes = [];
let filter = "all";

let visibleCount = 100;

const STEP = 100;

const container =
  document.getElementById("nodes");

const search =
  document.getElementById("search");

const count =
  document.getElementById("count");

const loadMore =
  document.getElementById("load-more");


function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}


function safeUrl(url) {

  if (!url) {
    return null;
  }

  try {

    const parsed = new URL(url);

    if (
      parsed.protocol === "https:" ||
      parsed.protocol === "http:"
    ) {
      return parsed.href;
    }

  } catch {}

  return null;
}


function updateStats() {

  const official =
    nodes.filter(
      node => node.source === "official"
    ).length;

  const community =
    nodes.filter(
      node => node.source === "community"
    ).length;

  document.getElementById(
    "total-stat"
  ).textContent =
    nodes.length.toLocaleString();

  document.getElementById(
    "official-stat"
  ).textContent =
    official.toLocaleString();

  document.getElementById(
    "community-stat"
  ).textContent =
    community.toLocaleString();
}


function getLinks(node) {

  const links = node.links || {};

  const npm =
    safeUrl(links.npm) ||
    (
      node.source === "community"
        ? `https://www.npmjs.com/package/${encodeURIComponent(node.package)}`
        : null
    );

  return {
    npm,
    repository: safeUrl(
      links.repository
    ),
    homepage: safeUrl(
      links.homepage
    )
  };
}


fetch("./data/catalog.json")

  .then(response => {

    if (!response.ok) {
      throw new Error(
        "Unable to load catalog"
      );
    }

    return response.json();
  })

  .then(data => {

    nodes = data;

    updateStats();

    render();
  })

  .catch(error => {

    console.error(error);

    count.textContent =
      "Unable to load catalog.";
  });


function getResults() {

  const query =
    search.value
      .trim()
      .toLowerCase();

  return nodes.filter(node => {

    const searchable = [
      node.displayName,
      node.name,
      node.package,
      node.description
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    const matchesSearch =
      !query ||
      searchable.includes(query);

    const matchesFilter =
      filter === "all" ||
      node.source === filter;

    return (
      matchesSearch &&
      matchesFilter
    );
  });
}


function render() {

  const results =
    getResults();

  count.textContent =
    `${results.length.toLocaleString()} integrations found`;

  const visible =
    results.slice(
      0,
      visibleCount
    );


  if (!visible.length) {

    container.innerHTML = `
      <div class="empty">

        <h2>
          No integrations found
        </h2>

        <p>
          Try another search.
        </p>

      </div>
    `;

    loadMore.style.display =
      "none";

    return;
  }


  container.innerHTML =
    visible
      .map(createCard)
      .join("");


  loadMore.style.display =
    results.length > visibleCount
      ? "inline-flex"
      : "none";
}


function createCard(node) {

  const links =
    getLinks(node);


  const buttons = [];


  if (links.repository) {

    buttons.push(`
      <a
        href="${escapeHtml(links.repository)}"
        target="_blank"
        rel="noopener noreferrer">
        GitHub
      </a>
    `);
  }


  if (links.npm) {

    buttons.push(`
      <a
        href="${escapeHtml(links.npm)}"
        target="_blank"
        rel="noopener noreferrer">
        npm
      </a>
    `);
  }


  if (links.homepage) {

    buttons.push(`
      <a
        href="${escapeHtml(links.homepage)}"
        target="_blank"
        rel="noopener noreferrer">
        Website
      </a>
    `);
  }


  return `
    <article class="card">

      <div class="card-top">

        <span
          class="badge ${escapeHtml(node.source)}">

          ${escapeHtml(node.source)}

        </span>


        ${
          node.version
            ? `
              <span class="version">
                v${escapeHtml(node.version)}
              </span>
            `
            : ""
        }

      </div>


      <h2>
        ${escapeHtml(
          node.displayName ||
          node.name
        )}
      </h2>


      <div class="package">

        ${escapeHtml(node.package)}

      </div>


      <p class="description">

        ${escapeHtml(
          node.description ||
          (
            node.source === "official"
              ? "Official n8n integration."
              : "Community integration for n8n."
          )
        )}

      </p>


      <div class="card-footer">

        <div class="links">

          ${buttons.join("")}

        </div>

      </div>

    </article>
  `;
}


search.addEventListener(
  "input",
  () => {

    visibleCount = STEP;

    render();
  }
);


document
  .querySelectorAll(
    "[data-filter]"
  )
  .forEach(button => {

    button.addEventListener(
      "click",
      () => {

        document
          .querySelectorAll(
            "[data-filter]"
          )
          .forEach(item =>
            item.classList.remove(
              "active"
            )
          );

        button.classList.add(
          "active"
        );

        filter =
          button.dataset.filter;

        visibleCount =
          STEP;

        render();
      }
    );
  });


loadMore.addEventListener(
  "click",
  () => {

    visibleCount += STEP;

    render();
  }
);