let nodes = [];
let fuse = null;

let filter = "all";
let categoryFilter = "all";
let kindFilter = "all";
let statusFilter = "all";

let visibleCount = 100;

const STEP = 100;

const FEATURED_LIMIT = 8;
const POPULAR_LIMIT = 8;


const FUSE_OPTIONS = {
  includeScore: true,
  shouldSort: true,
  threshold: 0.34,
  distance: 120,
  ignoreLocation: true,
  minMatchCharLength: 2,

  keys: [
    {
      name: "displayName",
      weight: 0.42,
    },
    {
      name: "name",
      weight: 0.15,
    },
    {
      name: "package",
      weight: 0.15,
    },
    {
      name: "categories",
      weight: 0.10,
    },
    {
      name: "description",
      weight: 0.10,
    },
    {
      name: "nodeKind",
      weight: 0.05,
    },
    {
      name: "publisher",
      weight: 0.03,
    },
  ],
};


const container =
  document.getElementById("nodes");

const featuredContainer =
  document.getElementById(
    "featured-nodes"
  );

const popularContainer =
  document.getElementById(
    "popular-nodes"
  );

const discovery =
  document.getElementById(
    "discovery"
  );

const search =
  document.getElementById(
    "search"
  );

const count =
  document.getElementById(
    "count"
  );

const loadMore =
  document.getElementById(
    "load-more"
  );

const categorySelect =
  document.getElementById(
    "category-filter"
  );

const kindSelect =
  document.getElementById(
    "kind-filter"
  );

const statusSelect =
  document.getElementById(
    "status-filter"
  );

const clearFilters =
  document.getElementById(
    "clear-filters"
  );


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
    const parsed =
      new URL(url);

    if (
      parsed.protocol === "https:" ||
      parsed.protocol === "http:"
    ) {
      return parsed.href;
    }

  } catch {}

  return null;
}


function safeIconPath(path) {
  if (!path) {
    return null;
  }

  const value =
    String(path)
      .replaceAll("\\", "/")
      .replace(/^\.?\//, "");

  if (
    value.includes("..")
  ) {
    return null;
  }

  if (
    !value.startsWith(
      "assets/icons/"
    )
  ) {
    return null;
  }

  return value;
}


function normalizeText(value) {
  return String(
    value || ""
  )
    .trim()
    .toLowerCase();
}


function buildSearchEngine() {
  if (
    typeof Fuse === "undefined"
  ) {
    console.warn(
      "Fuse.js not loaded. Falling back to basic search."
    );

    fuse = null;

    return;
  }

  fuse = new Fuse(
    nodes,
    FUSE_OPTIONS
  );
}


function updateStats() {
  const official =
    nodes.filter(
      node =>
        node.source ===
        "official"
    ).length;

  const community =
    nodes.filter(
      node =>
        node.source ===
        "community"
    ).length;

  document
    .getElementById(
      "total-stat"
    )
    .textContent =
      nodes.length
        .toLocaleString();

  document
    .getElementById(
      "official-stat"
    )
    .textContent =
      official
        .toLocaleString();

  document
    .getElementById(
      "community-stat"
    )
    .textContent =
      community
        .toLocaleString();
}


function buildCategoryFilter() {
  const categories =
    new Set();

  nodes.forEach(node => {

    (
      node.categories || []
    ).forEach(category => {

      if (
        category &&
        category !== "Official"
      ) {
        categories.add(
          category
        );
      }

    });

  });

  [...categories]
    .sort(
      (a, b) =>
        a.localeCompare(b)
    )
    .forEach(category => {

      const option =
        document.createElement(
          "option"
        );

      option.value =
        category;

      option.textContent =
        category;

      categorySelect
        .appendChild(option);
    });
}


function getLinks(node) {
  const links =
    node.links || {};

  const npm =
    safeUrl(
      links.npm
    ) ||
    (
      node.source ===
      "community"

        ? (
          "https://www.npmjs.com/package/" +
          encodeURIComponent(
            node.package
          )
        )

        : null
    );

  return {
    npm,

    repository:
      safeUrl(
        links.repository
      ),

    homepage:
      safeUrl(
        links.homepage
      ),
  };
}


function createFallback(name) {
  const letter =
    (
      name
        ?.trim()
        ?.charAt(0)
      ||
      "N"
    ).toUpperCase();

  return `
    <div
      class="node-icon fallback-icon"
    >
      ${escapeHtml(letter)}
    </div>
  `;
}


function createIcon(node) {
  const icon =
    safeIconPath(
      node.iconDark ||
      node.icon ||
      node.iconLight
    );

  if (!icon) {
    return createFallback(
      node.displayName ||
      node.name
    );
  }

  const fallbackLetter =
    (
      node.displayName ||
      node.name ||
      "N"
    )
      .charAt(0)
      .toUpperCase();

  return `
    <div class="node-icon">

      <img
        src="${escapeHtml(icon)}"
        alt=""
        loading="lazy"
        decoding="async"

        onerror="
          this.style.display='none';
          this.parentElement.classList.add('fallback-icon');
          this.parentElement.textContent='${escapeHtml(
            fallbackLetter
          )}';
        "
      >

    </div>
  `;
}


function createCategories(node) {
  const categories =
    (
      node.categories || []
    )
      .filter(
        category =>
          category !== "Official"
      )
      .slice(0, 2);

  if (
    !categories.length
  ) {
    return "";
  }

  return `
    <div class="categories">

      ${
        categories
          .map(
            category => `
              <span class="category">
                ${escapeHtml(
                  category
                )}
              </span>
            `
          )
          .join("")
      }

    </div>
  `;
}


function createTypeBadge(node) {
  if (
    node.nodeKind === "trigger"
  ) {
    return `
      <span class="type-badge trigger">
        Trigger
      </span>
    `;
  }

  return `
    <span class="type-badge action">
      Action
    </span>
  `;
}


function createStatusBadge(node) {
  if (
    !node.deprecated
  ) {
    return "";
  }

  return `
    <span class="deprecated-badge">
      Deprecated
    </span>
  `;
}


function createCard(
  node,
  compact = false
) {
  const links =
    getLinks(node);

  const buttons = [];

  if (
    links.repository
  ) {
    buttons.push(`
      <a
        href="${escapeHtml(
          links.repository
        )}"
        target="_blank"
        rel="noopener noreferrer"
      >
        GitHub
      </a>
    `);
  }

  if (
    links.npm
  ) {
    buttons.push(`
      <a
        href="${escapeHtml(
          links.npm
        )}"
        target="_blank"
        rel="noopener noreferrer"
      >
        npm
      </a>
    `);
  }

  if (
    links.homepage
  ) {
    buttons.push(`
      <a
        href="${escapeHtml(
          links.homepage
        )}"
        target="_blank"
        rel="noopener noreferrer"
      >
        Website
      </a>
    `);
  }


  const displayName =
    node.displayName ||
    node.name ||
    "Unknown Node";


  const detailsUrl =
    "node.html?id=" +
    encodeURIComponent(
      node.id
    );


  return `
    <article
      class="card ${
        compact
          ? "showcase-card"
          : ""
      }"
    >

      <div class="card-header">

        ${createIcon(node)}

        <div class="card-heading">

          <div class="card-meta">

            <span
              class="badge ${escapeHtml(
                node.source
              )}"
            >
              ${escapeHtml(
                node.source
              )}
            </span>

            ${createTypeBadge(node)}

            ${createStatusBadge(node)}

            ${
              node.version
                ? `
                  <span class="version">
                    v${escapeHtml(
                      node.version
                    )}
                  </span>
                `
                : ""
            }

          </div>

          <h2
            title="${escapeHtml(
              displayName
            )}"
          >
            ${escapeHtml(
              displayName
            )}
          </h2>

        </div>

      </div>


      ${createCategories(node)}


      <div
        class="package"
        title="${escapeHtml(
          node.package || ""
        )}"
      >
        ${escapeHtml(
          node.package || ""
        )}
      </div>


      ${
        compact
          ? ""
          : `
            <p class="description">

              ${escapeHtml(
                node.description ||
                (
                  node.source ===
                  "official"

                    ? "Official n8n integration."

                    : "Community integration for n8n."
                )
              )}

            </p>
          `
      }


      <div class="card-footer">

        <div class="links">

          <a
            class="details-button"
            href="${escapeHtml(
              detailsUrl
            )}"
          >
            Details
          </a>

          ${buttons.join("")}

        </div>

      </div>

    </article>
  `;
}


function normalizePopularName(
  value
) {
  return String(
    value || ""
  )
    .toLowerCase()

    .replace(
      /\btrigger\b/g,
      ""
    )

    .replace(
      /[^a-z0-9]+/g,
      ""
    );
}


function pickUniquePackages(
  list,
  limit
) {
  const seenPackages =
    new Set();

  const seenNames =
    new Set();

  const result = [];

  for (
    const node of list
  ) {

    const packageKey =
      String(
        node.package ||
        node.id ||
        ""
      ).toLowerCase();

    const nameKey =
      normalizePopularName(
        node.displayName ||
        node.name
      );


    if (
      seenPackages.has(
        packageKey
      )
    ) {
      continue;
    }


    if (
      nameKey &&
      seenNames.has(
        nameKey
      )
    ) {
      continue;
    }


    seenPackages.add(
      packageKey
    );


    if (
      nameKey
    ) {
      seenNames.add(
        nameKey
      );
    }


    result.push(
      node
    );


    if (
      result.length >=
      limit
    ) {
      break;
    }
  }

  return result;
}


function renderDiscovery() {
  const featured =
    nodes

      .filter(
        node =>
          node.featured ===
          true
      )

      .sort(
        (a, b) =>
          (
            a.featuredRank ??
            999
          )
          -
          (
            b.featuredRank ??
            999
          )
      )

      .slice(
        0,
        FEATURED_LIMIT
      );


  const popular =
    pickUniquePackages(

      nodes

        .filter(
          node =>

            node.source ===
              "community"

            &&

            node.verified ===
              true

            &&

            !node.deprecated

            &&

            node.nodeKind !==
              "trigger"

            &&

            Number.isFinite(
              Number(
                node.npmPopularity
              )
            )
        )

        .sort(
          (a, b) =>
            Number(
              b.npmPopularity ||
              0
            )
            -
            Number(
              a.npmPopularity ||
              0
            )
        ),

      POPULAR_LIMIT
    );


  featuredContainer.innerHTML =
    featured
      .map(
        node =>
          createCard(
            node,
            true
          )
      )
      .join("");


  popularContainer.innerHTML =
    popular
      .map(
        node =>
          createCard(
            node,
            true
          )
      )
      .join("");
}


function discoveryShouldShow() {
  return (
    search.value
      .trim() === ""

    &&

    filter === "all"

    &&

    categoryFilter ===
      "all"

    &&

    kindFilter ===
      "all"

    &&

    statusFilter ===
      "all"
  );
}


function basicSearch(query) {
  const normalizedQuery =
    normalizeText(query);

  if (
    !normalizedQuery
  ) {
    return nodes;
  }

  return nodes.filter(
    node => {

      const searchable = [
        node.displayName,
        node.name,
        node.package,
        node.description,
        node.publisher,
        node.nodeKind,

        ...(
          node.categories || []
        ),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();


      return searchable.includes(
        normalizedQuery
      );
    }
  );
}


function fuzzySearch(query) {
  const normalizedQuery =
    normalizeText(query);

  if (
    !normalizedQuery
  ) {
    return nodes;
  }


  if (
    !fuse
  ) {
    return basicSearch(
      normalizedQuery
    );
  }


  return fuse
    .search(
      normalizedQuery
    )
    .map(
      result =>
        result.item
    );
}


function getResults() {
  const query =
    search.value
      .trim();


  const searchResults =
    query
      ? fuzzySearch(query)
      : nodes;


  return searchResults.filter(
    node => {

      const matchesSource =
        filter === "all" ||
        node.source ===
        filter;


      const matchesCategory =
        categoryFilter ===
          "all"

        ||

        (
          node.categories || []
        ).includes(
          categoryFilter
        );


      const matchesKind =
        kindFilter === "all" ||
        node.nodeKind ===
        kindFilter;


      const isDeprecated =
        Boolean(
          node.deprecated
        );


      const matchesStatus =
        statusFilter ===
          "all"

        ||

        (
          statusFilter ===
            "active"

          &&

          !isDeprecated
        )

        ||

        (
          statusFilter ===
            "deprecated"

          &&

          isDeprecated
        );


      return (
        matchesSource &&
        matchesCategory &&
        matchesKind &&
        matchesStatus
      );
    }
  );
}


function render() {
  const results =
    getResults();


  const query =
    search.value
      .trim();


  if (
    query
  ) {
    count.textContent =
      `${results.length.toLocaleString()} fuzzy matches`;

  } else {

    count.textContent =
      `${results.length.toLocaleString()} integrations found`;
  }


  discovery.style.display =
    discoveryShouldShow()
      ? "block"
      : "none";


  const visible =
    results.slice(
      0,
      visibleCount
    );


  if (
    !visible.length
  ) {
    container.innerHTML = `
      <div class="empty">

        <h2>
          No integrations found
        </h2>

        <p>
          Try another search or filter.
        </p>

      </div>
    `;


    loadMore.style.display =
      "none";


    return;
  }


  container.innerHTML =
    visible

      .map(
        node =>
          createCard(node)
      )

      .join("");


  loadMore.style.display =
    results.length >
      visibleCount

      ? "inline-flex"
      : "none";
}


fetch(
  "./data/catalog.json"
)

  .then(
    response => {

      if (
        !response.ok
      ) {
        throw new Error(
          "Unable to load catalog"
        );
      }

      return response.json();
    }
  )

  .then(
    data => {

      nodes = data;

      updateStats();

      buildCategoryFilter();

      buildSearchEngine();

      renderDiscovery();

      render();
    }
  )

  .catch(
    error => {

      console.error(
        error
      );

      count.textContent =
        "Unable to load catalog.";
    }
  );


let searchTimer =
  null;


search.addEventListener(
  "input",
  () => {

    clearTimeout(
      searchTimer
    );


    searchTimer =
      setTimeout(
        () => {

          visibleCount =
            STEP;

          render();

        },
        90
      );
  }
);


document
  .querySelectorAll(
    "[data-filter]"
  )
  .forEach(
    button => {

      button.addEventListener(
        "click",
        () => {

          document
            .querySelectorAll(
              "[data-filter]"
            )
            .forEach(
              item => {

                item
                  .classList
                  .remove(
                    "active"
                  );
              }
            );


          button
            .classList
            .add(
              "active"
            );


          filter =
            button.dataset.filter;


          visibleCount =
            STEP;


          render();
        }
      );
    }
  );


categorySelect
  .addEventListener(
    "change",
    () => {

      categoryFilter =
        categorySelect.value;


      visibleCount =
        STEP;


      render();
    }
  );


kindSelect
  .addEventListener(
    "change",
    () => {

      kindFilter =
        kindSelect.value;


      visibleCount =
        STEP;


      render();
    }
  );


statusSelect
  .addEventListener(
    "change",
    () => {

      statusFilter =
        statusSelect.value;


      visibleCount =
        STEP;


      render();
    }
  );


clearFilters
  .addEventListener(
    "click",
    () => {

      search.value =
        "";

      filter =
        "all";

      categoryFilter =
        "all";

      kindFilter =
        "all";

      statusFilter =
        "all";


      categorySelect.value =
        "all";

      kindSelect.value =
        "all";

      statusSelect.value =
        "all";


      document
        .querySelectorAll(
          "[data-filter]"
        )
        .forEach(
          button => {

            button.classList.toggle(
              "active",
              button.dataset.filter ===
                "all"
            );
          }
        );


      visibleCount =
        STEP;


      render();
    }
  );


loadMore
  .addEventListener(
    "click",
    () => {

      visibleCount +=
        STEP;


      render();
    }
  );